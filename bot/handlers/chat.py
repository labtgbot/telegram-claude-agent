import base64
from copy import deepcopy
import re
import time
from contextlib import aclosing, asynccontextmanager
from html import escape as html_escape

import structlog
from aiogram import Router, F
from aiogram.types import Message

from bot.config import settings
from bot.services.answer_guest_query import (
    AnswerGuestQueryError,
    perform_answer_guest_query,
)
from bot.services.claude_proxy import ClaudeProxyClient
from bot.services.send_chat_action import keep_chat_action
from bot.services.send_message_draft import (
    SendMessageDraftError,
    perform_send_message_draft,
)
from bot.utils.media import extract_document_text, transcribe_voice
from bot.utils.storage import storage

logger = structlog.get_logger()

router = Router()

TELEGRAM_MESSAGE_LIMIT = 4096

# Telegram clears a message draft after about 30 seconds and animates updates
# that reuse the same draft_id, so refresh the preview at most this often to show
# steady progress without flooding the ephemeral endpoint with tiny deltas.
DRAFT_UPDATE_INTERVAL_SECONDS = 0.5
IMAGE_HISTORY_PLACEHOLDER = "[image omitted from history]"


def _format_byte_size(size: int) -> str:
    if size == 1:
        return "1 byte"
    if size < 1024:
        return f"{size} bytes"

    value = float(size)
    for unit in ("KiB", "MiB", "GiB", "TiB"):
        value /= 1024
        if value < 1024:
            if value.is_integer():
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
    return f"{value:.1f} PiB"


def _known_file_size(media) -> int | None:
    file_size = getattr(media, "file_size", None)
    if isinstance(file_size, int) and not isinstance(file_size, bool) and file_size >= 0:
        return file_size
    return None


async def _reject_oversized_media(message: Message, file_size: int | None) -> bool:
    if file_size is None or file_size <= settings.telegram_media_download_max_bytes:
        return False

    max_size = _format_byte_size(settings.telegram_media_download_max_bytes)
    await message.answer(f"❌ Media file is too large. Maximum allowed size is {max_size}.")
    logger.info(
        "media_download_rejected_oversize",
        file_size=file_size,
        max_bytes=settings.telegram_media_download_max_bytes,
        chat_id=getattr(message.chat, "id", None),
        user_id=getattr(message.from_user, "id", None),
    )
    return True


async def _download_media_bytes(
    message: Message, file_id: str, file_size: int | None
) -> bytes | None:
    if await _reject_oversized_media(message, file_size):
        return None

    file = await message.bot.get_file(file_id)
    if await _reject_oversized_media(message, _known_file_size(file)):
        return None

    data = await message.bot.download_file(file.file_path)
    media_bytes = data.read() if hasattr(data, "read") else data
    if await _reject_oversized_media(message, len(media_bytes)):
        return None
    return media_bytes


@asynccontextmanager
async def _typing_indicator(message: Message):
    """Show a "typing…" chat action while Claude/proxy handles the request.

    Wraps :func:`keep_chat_action` so the bot refreshes the indicator until the
    block exits, signalling that a noticeably long request is in progress. The
    indicator is skipped entirely when ``telegram_chat_action_enabled`` is off,
    keeping behaviour unchanged for deployments that opt out.
    """
    if not settings.telegram_chat_action_enabled:
        yield
        return
    async with keep_chat_action(message.bot, chat_id=message.chat.id, action="typing"):
        yield


def text_to_content_blocks(text: str) -> list:
    return [{"type": "text", "text": text}]


def _content_blocks_for_history(content_blocks: list) -> list:
    history_blocks = []
    for block in content_blocks:
        if isinstance(block, dict) and block.get("type") == "image":
            history_blocks.append({"type": "text", "text": IMAGE_HISTORY_PLACEHOLDER})
        else:
            history_blocks.append(deepcopy(block))
    return history_blocks


def _strip_bot_mention(text: str, bot_username: str) -> str:
    if not bot_username:
        return text
    pattern = "@" + re.escape(bot_username) + r"\s*"
    return re.sub(pattern, "", text, count=1).strip()


_MD_INLINE_CODE = re.compile(r"`([^`\n]+?)`")
_MD_BOLD = re.compile(r"\*\*(.+?)\*\*", re.DOTALL)
_MD_ITALIC = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", re.DOTALL)
_MD_FENCED_CODE = re.compile(r"```([a-zA-Z0-9_+-]*)\n?([\s\S]*?)```", re.MULTILINE)


def md_to_html(text: str) -> str:
    """Convert a minimal subset of Markdown emitted by LLMs into Telegram HTML."""
    if not text:
        return ""

    placeholders: list[str] = []

    def _save(html: str) -> str:
        placeholders.append(html)
        return f"\x00{len(placeholders) - 1}\x00"

    def _fenced(match: re.Match) -> str:
        body = match.group(2)
        return _save(f"<pre><code>{html_escape(body)}</code></pre>")

    def _inline(match: re.Match) -> str:
        body = match.group(1)
        return _save(f"<code>{html_escape(body)}</code>")

    rendered = _MD_FENCED_CODE.sub(_fenced, text)
    rendered = _MD_INLINE_CODE.sub(_inline, rendered)
    rendered = html_escape(rendered)
    rendered = _MD_BOLD.sub(r"<b>\1</b>", rendered)
    rendered = _MD_ITALIC.sub(r"<i>\1</i>", rendered)

    def _restore(match: re.Match) -> str:
        return placeholders[int(match.group(1))]

    rendered = re.sub(r"\x00(\d+)\x00", _restore, rendered)
    return rendered


# Matches a single HTML tag or character/named entity. Everything else is plain
# text. ``md_to_html`` only ever emits ``<b>``, ``<i>``, ``<code>`` and
# ``<pre><code>`` plus entities from :func:`html.escape`, but the pattern is
# generic enough to keep any well-formed Telegram HTML intact.
_HTML_TOKEN_RE = re.compile(
    r"</?[a-zA-Z][a-zA-Z0-9]*[^>]*>"  # opening, closing or void tag
    r"|&(?:#x?[0-9a-fA-F]+|[a-zA-Z][a-zA-Z0-9]*);"  # numeric or named entity
)


def _tokenize_html(text: str) -> list[dict]:
    """Break ``text`` into atomic tokens that must never be split internally.

    Tags and HTML entities become single tokens; every other character becomes
    its own text token so a chunk boundary can fall between any two characters
    without ever landing inside a tag (``<b>``) or an entity (``&amp;``).
    """
    tokens: list[dict] = []
    pos = 0
    for match in _HTML_TOKEN_RE.finditer(text):
        for ch in text[pos : match.start()]:
            tokens.append({"type": "text", "s": ch})
        token = match.group(0)
        if token.startswith("&"):
            tokens.append({"type": "text", "s": token})
        elif token.startswith("</"):
            name = token[2:].rstrip(">").strip().lower()
            tokens.append({"type": "close", "s": token, "name": name})
        elif token.endswith("/>"):
            # Void tag (e.g. ``<br/>``): does not open a scope.
            tokens.append({"type": "text", "s": token})
        else:
            name = re.match(r"<([a-zA-Z][a-zA-Z0-9]*)", token).group(1).lower()
            tokens.append(
                {"type": "open", "s": token, "name": name, "close": f"</{name}>"}
            )
        pos = match.end()
    for ch in text[pos:]:
        tokens.append({"type": "text", "s": ch})
    return tokens


def _split_for_telegram(text: str, limit: int = TELEGRAM_MESSAGE_LIMIT) -> list[str]:
    """Split ``text`` into chunks no longer than ``limit``, keeping HTML valid.

    The input is already-rendered Telegram HTML, so a naive length-based cut can
    land inside a tag or entity, or leave a ``<pre><code>`` block (or ``<b>``
    span) unbalanced across chunks. This splitter is HTML-aware: it never breaks
    inside a tag or entity, closes every still-open tag at the end of a chunk and
    reopens it at the start of the next one, and prefers to cut on a newline for
    readability.
    """
    if not text:
        return [""]
    if len(text) <= limit:
        return [text]

    tokens = _tokenize_html(text)
    chunks: list[str] = []
    open_stack: list[dict] = []  # tags carried open across the current boundary
    i = 0
    n = len(tokens)

    while i < n:
        parts = [tag["s"] for tag in open_stack]  # reopen carried-over tags
        cur_len = sum(len(p) for p in parts)
        local_stack = list(open_stack)
        # Best newline break seen so far: (token_index, parts_len, stack_copy).
        last_break: tuple[int, int, list[dict]] | None = None
        progressed = False

        while i < n:
            tok = tokens[i]
            s = tok["s"]
            if tok["type"] == "open":
                stack_after = local_stack + [tok]
            elif tok["type"] == "close" and local_stack:
                stack_after = local_stack[:-1]
            else:
                stack_after = local_stack
            close_len = sum(len(t["close"]) for t in stack_after)

            if progressed and cur_len + len(s) + close_len > limit:
                break

            parts.append(s)
            cur_len += len(s)
            local_stack = stack_after
            i += 1
            progressed = True
            if tok["type"] == "text" and s.endswith("\n"):
                last_break = (i, len(parts), list(local_stack))

        if i < n and last_break is not None and last_break[1] > len(open_stack):
            # Prefer the newline break: rewind to it and replay the tail later.
            i, keep, local_stack = last_break
            parts = parts[:keep]

        for tag in reversed(local_stack):
            parts.append(tag["close"])
        chunks.append("".join(parts))
        open_stack = local_stack

    return chunks


async def send_reply_safely(message: Message, text: str, parse_mode: str | None = "HTML"):
    if not text:
        return
    for chunk in _split_for_telegram(text):
        try:
            await message.answer(chunk, parse_mode=parse_mode)
        except Exception as exc:
            logger.warning("send_failed_falling_back_to_plain", error=str(exc))
            await message.answer(chunk)


def _guest_query_id(message: Message) -> str | None:
    value = getattr(message, "guest_query_id", None)
    return value or None


async def send_final_reply(
    message: Message, text: str, parse_mode: str | None = "HTML"
) -> None:
    guest_query_id = _guest_query_id(message)
    if guest_query_id:
        try:
            await perform_answer_guest_query(
                message.bot,
                guest_query_id=guest_query_id,
                text=text[:TELEGRAM_MESSAGE_LIMIT],
            )
            return
        except AnswerGuestQueryError as exc:
            logger.warning(
                "answer_guest_query_failed_falling_back_to_message",
                error=str(exc),
                guest_query_id=guest_query_id,
            )

    await send_reply_safely(message, text, parse_mode=parse_mode)


async def handle_streaming(
    message: Message, client: ClaudeProxyClient, messages: list, model: str
) -> str:
    sent_msg = await message.answer("…")
    full_text = ""
    try:
        stream = await client.send_message(
            messages=messages,
            model=model,
            stream=True,
        )
        # ``aclosing`` guarantees the generator's ``finally`` runs (closing the
        # underlying HTTP response) even if we break early or raise here. See #351.
        async with aclosing(stream) as events:
            async for chunk in events:
                if chunk.get("type") != "content_block_delta":
                    continue
                delta = chunk.get("delta", {})
                if delta.get("type") != "text_delta":
                    continue
                text = delta.get("text", "")
                if not text:
                    continue
                full_text += text
                try:
                    await sent_msg.edit_text(full_text[:TELEGRAM_MESSAGE_LIMIT])
                except Exception:
                    pass
    except Exception as exc:
        await sent_msg.edit_text(f"❌ Error: {exc}")
        raise

    reply_text = full_text or "Claude returned no text response."
    rendered = md_to_html(reply_text)
    chunks = _split_for_telegram(rendered)
    try:
        await sent_msg.edit_text(chunks[0], parse_mode="HTML")
    except Exception:
        await sent_msg.edit_text(chunks[0][:TELEGRAM_MESSAGE_LIMIT])
    for extra in chunks[1:]:
        try:
            await message.answer(extra, parse_mode="HTML")
        except Exception:
            await message.answer(extra)

    return reply_text


def _should_use_message_draft(message: Message) -> bool:
    """Decide whether to stream the reply via ephemeral ``sendMessageDraft``.

    ``sendMessageDraft`` only targets private chats, so the ephemeral preview
    alternative to ``editMessageText`` is used only there and only when opted in
    via ``telegram_message_draft_enabled``; every other chat keeps the existing
    edit-based streaming.
    """
    return settings.telegram_message_draft_enabled and message.chat.type == "private"


async def _send_draft_preview(message: Message, draft_id: int, text: str) -> None:
    """Show a partial reply as an ephemeral ``sendMessageDraft`` preview.

    Best-effort wrapper around :func:`perform_send_message_draft`: a failure to
    display the ephemeral preview is logged and swallowed so it never breaks the
    streaming response being generated. ``text`` is clamped to the Telegram
    message limit; an empty string shows the "Thinking…" placeholder.
    """
    try:
        await perform_send_message_draft(
            message.bot,
            chat_id=message.chat.id,
            draft_id=draft_id,
            text=text[:TELEGRAM_MESSAGE_LIMIT],
        )
    except SendMessageDraftError as exc:
        logger.warning("message_draft_preview_failed", error=str(exc))


async def handle_streaming_with_draft(
    message: Message, client: ClaudeProxyClient, messages: list, model: str
) -> str:
    """Stream the reply as ephemeral draft previews, then persist the final text.

    Used in private chats as an alternative to repeatedly calling
    ``editMessageText`` while Claude generates an answer: partial text is shown
    through the ephemeral Telegram ``sendMessageDraft`` preview (a single,
    non-zero ``draft_id`` per response keeps the updates animated) instead of
    creating and editing a real message. Because the draft is only a temporary
    30-second preview, the finished answer is still persisted with real
    ``sendMessage`` calls once generation completes. Draft previews are
    throttled to :data:`DRAFT_UPDATE_INTERVAL_SECONDS` to avoid flooding the
    endpoint with tiny deltas.
    """
    # draft_id must be non-zero; reuse one id per response so updates animate.
    draft_id = message.message_id or 1

    # Show the "Thinking…" placeholder immediately.
    await _send_draft_preview(message, draft_id, "")

    # Any streaming failure propagates to the outer handler, which reports it to
    # the user; the ephemeral draft simply expires on its own.
    full_text = ""
    last_update = time.monotonic()
    stream = await client.send_message(
        messages=messages,
        model=model,
        stream=True,
    )
    # ``aclosing`` guarantees the generator's ``finally`` runs (closing the
    # underlying HTTP response) even if we break early or raise here. See #351.
    async with aclosing(stream) as events:
        async for chunk in events:
            if chunk.get("type") != "content_block_delta":
                continue
            delta = chunk.get("delta", {})
            if delta.get("type") != "text_delta":
                continue
            text = delta.get("text", "")
            if not text:
                continue
            full_text += text
            now = time.monotonic()
            if now - last_update >= DRAFT_UPDATE_INTERVAL_SECONDS:
                last_update = now
                await _send_draft_preview(message, draft_id, full_text)

    reply_text = full_text or "Claude returned no text response."
    await send_final_reply(message, md_to_html(reply_text))
    return reply_text


@router.message(F.text | F.photo | F.voice | F.document)
async def handle_chat_message(message: Message):
    user_id = message.from_user.id
    chat = message.chat
    bot_username = message.bot.username or (await message.bot.get_me()).username

    allowed_ids = settings.allowed_chat_ids
    if allowed_ids and chat.id not in allowed_ids:
        return

    is_group = chat.type in ("group", "supergroup")
    addressed_to_bot = True

    if is_group:
        mention_pattern = re.compile(r"@" + re.escape(bot_username or ""), re.IGNORECASE)
        text_mentions_bot = bool(message.text and bot_username and mention_pattern.search(message.text))
        caption_mentions_bot = bool(
            message.caption and bot_username and mention_pattern.search(message.caption)
        )
        replies_to_bot = bool(
            message.reply_to_message
            and message.reply_to_message.from_user
            and message.reply_to_message.from_user.is_bot
            and message.reply_to_message.from_user.username == bot_username
        )
        addressed_to_bot = text_mentions_bot or caption_mentions_bot or replies_to_bot

        if not addressed_to_bot:
            return

    use_history = not (is_group and settings.telegram_guest_mode_enabled)

    messages = []
    if use_history:
        messages.extend(storage.get_history(chat.id, user_id))

    content_blocks = None

    if message.text:
        cleaned = _strip_bot_mention(message.text, bot_username) if is_group else message.text
        content_blocks = text_to_content_blocks(cleaned)

    elif message.photo:
        photo = message.photo[-1]
        image_bytes = await _download_media_bytes(
            message, photo.file_id, _known_file_size(photo)
        )
        if image_bytes is None:
            return
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        content_blocks = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": b64,
                },
            }
        ]
        if message.caption:
            caption = (
                _strip_bot_mention(message.caption, bot_username) if is_group else message.caption
            )
            content_blocks.append({"type": "text", "text": caption})

    elif message.voice:
        audio_bytes = await _download_media_bytes(
            message, message.voice.file_id, _known_file_size(message.voice)
        )
        if audio_bytes is None:
            return
        transcribed = await transcribe_voice(audio_bytes)
        if not transcribed:
            await message.answer("❌ Could not transcribe voice message.")
            return
        content_blocks = text_to_content_blocks(transcribed)

    elif message.document:
        doc = message.document
        doc_bytes = await _download_media_bytes(
            message, doc.file_id, _known_file_size(doc)
        )
        if doc_bytes is None:
            return
        extracted = await extract_document_text(doc.mime_type, doc_bytes)
        if not extracted:
            await message.answer(
                f"❌ Could not extract text from document: {doc.file_name or 'unknown'}"
            )
            return
        content_blocks = text_to_content_blocks(extracted)

    else:
        return

    if not content_blocks:
        return

    messages.append({"role": "user", "content": content_blocks})

    model = storage.get_setting(user_id, "model", settings.free_claude_default_model)

    client = ClaudeProxyClient(
        settings.free_claude_base_url,
        settings.free_claude_auth_token,
        settings.free_claude_timeout_seconds,
    )
    try:
        use_draft_stream = _should_use_message_draft(message)
        async with _typing_indicator(message):
            if settings.free_claude_streaming_enabled and use_draft_stream:
                reply_text = await handle_streaming_with_draft(message, client, messages, model)
            elif settings.free_claude_streaming_enabled:
                reply_text = await handle_streaming(message, client, messages, model)
            else:
                response = await client.send_message(
                    messages=messages,
                    model=model,
                )
                reply_text = ""
                for block in response.get("content", []):
                    if block.get("type") == "text":
                        reply_text += block.get("text", "")
                if not reply_text:
                    reply_text = "Claude returned no text response."
                await send_final_reply(message, md_to_html(reply_text))

        if use_history and reply_text:
            storage.add_message(
                chat.id, user_id, "user", _content_blocks_for_history(content_blocks)
            )
            storage.add_message(
                chat.id, user_id, "assistant", [{"type": "text", "text": reply_text}]
            )

    except Exception as exc:
        logger.exception("chat_handler_failed", error=str(exc))
        await message.answer(f"❌ Error: {exc}")
    finally:
        await client.close()
