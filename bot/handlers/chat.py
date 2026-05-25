import base64
import re
from html import escape as html_escape

import structlog
from aiogram import Router, F
from aiogram.types import Message

from bot.config import settings
from bot.services.claude_proxy import ClaudeProxyClient
from bot.utils.media import extract_document_text, transcribe_voice
from bot.utils.storage import storage

logger = structlog.get_logger()

router = Router()

TELEGRAM_MESSAGE_LIMIT = 4096


def text_to_content_blocks(text: str) -> list:
    return [{"type": "text", "text": text}]


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


def _split_for_telegram(text: str, limit: int = TELEGRAM_MESSAGE_LIMIT) -> list[str]:
    if not text:
        return [""]
    parts: list[str] = []
    remaining = text
    while len(remaining) > limit:
        cut = remaining.rfind("\n", 0, limit)
        if cut <= 0:
            cut = limit
        parts.append(remaining[:cut])
        remaining = remaining[cut:].lstrip("\n")
    parts.append(remaining)
    return parts


async def send_reply_safely(message: Message, text: str, parse_mode: str | None = "HTML"):
    if not text:
        return
    for chunk in _split_for_telegram(text):
        try:
            await message.answer(chunk, parse_mode=parse_mode)
        except Exception as exc:
            logger.warning("send_failed_falling_back_to_plain", error=str(exc))
            await message.answer(chunk)


async def handle_streaming(message: Message, client: ClaudeProxyClient, messages: list) -> str:
    sent_msg = await message.answer("…")
    full_text = ""
    try:
        stream = await client.send_message(
            messages=messages,
            model=settings.free_claude_default_model,
            stream=True,
        )
        async for chunk in stream:
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

    rendered = md_to_html(full_text)
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

    return full_text


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
        file = await message.bot.get_file(photo.file_id)
        data = await message.bot.download_file(file.file_path)
        b64 = base64.b64encode(data.read() if hasattr(data, "read") else data).decode("utf-8")
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
        file = await message.bot.get_file(message.voice.file_id)
        data = await message.bot.download_file(file.file_path)
        audio_bytes = data.read() if hasattr(data, "read") else data
        transcribed = await transcribe_voice(audio_bytes)
        if not transcribed:
            await message.answer("❌ Could not transcribe voice message.")
            return
        content_blocks = text_to_content_blocks(transcribed)

    elif message.document:
        doc = message.document
        file = await message.bot.get_file(doc.file_id)
        data = await message.bot.download_file(file.file_path)
        doc_bytes = data.read() if hasattr(data, "read") else data
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

    client = ClaudeProxyClient(
        settings.free_claude_base_url,
        settings.free_claude_auth_token,
        settings.free_claude_timeout_seconds,
    )
    try:
        if settings.free_claude_streaming_enabled:
            reply_text = await handle_streaming(message, client, messages)
        else:
            response = await client.send_message(
                messages=messages,
                model=settings.free_claude_default_model,
            )
            reply_text = ""
            for block in response.get("content", []):
                if block.get("type") == "text":
                    reply_text += block.get("text", "")
            if not reply_text:
                reply_text = "Claude returned no text response."
            await send_reply_safely(message, md_to_html(reply_text))

        if use_history and reply_text:
            storage.add_message(chat.id, user_id, "user", content_blocks)
            storage.add_message(
                chat.id, user_id, "assistant", [{"type": "text", "text": reply_text}]
            )

    except Exception as exc:
        logger.exception("chat_handler_failed", error=str(exc))
        await message.answer(f"❌ Error: {exc}")
    finally:
        await client.close()
