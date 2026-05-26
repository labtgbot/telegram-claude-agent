from typing import Any, Optional

import httpx
import structlog

logger = structlog.get_logger()

DEFAULT_REQUEST_TIMEOUT = 60.0

# Telegram limits the draft text to 0-4096 characters after entities parsing;
# an empty string is explicitly allowed and shows a "Thinking…" placeholder.
MESSAGE_DRAFT_TEXT_LIMIT = 4096


class SendMessageDraftError(Exception):
    """Raised when ``sendMessageDraft`` fails validation or the raw call fails.

    The pinned ``aiogram==3.3.0`` (Bot API 7.0) predates the Bot API 10.0
    ``sendMessageDraft`` method and ships no typed wrapper for it, so this helper
    calls the raw HTTP endpoint directly. Validation failures (a zero
    ``draft_id`` or an over-long ``text``) and request failures (transport errors
    or a Telegram ``ok: false`` response) are surfaced through this dedicated
    exception instead of aiogram's ``TelegramAPIError`` so callers have a single,
    version-independent error type to catch. ``error_code`` holds the Telegram
    ``error_code`` when the failure comes from a Telegram response and stays
    ``None`` for client-side validation errors.
    """

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


def _build_api_url(bot: Any, method: str) -> str:
    """Resolve the Bot API URL for ``method`` from the bot's session.

    Prefers aiogram's ``bot.session.api.api_url(token, method)`` so a custom
    local Bot API server is honoured, and falls back to the production cloud
    endpoint when the session does not expose that helper (e.g. in tests with a
    minimal bot stub).
    """
    session = getattr(bot, "session", None)
    api = getattr(session, "api", None)
    api_url = getattr(api, "api_url", None)
    if callable(api_url):
        return api_url(token=bot.token, method=method)
    return f"https://api.telegram.org/bot{bot.token}/{method}"


async def perform_send_message_draft(
    bot: Any,
    *,
    chat_id: int,
    draft_id: int,
    text: str = "",
    message_thread_id: Optional[int] = None,
    parse_mode: Optional[str] = None,
    entities: Optional[list] = None,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> bool:
    """Stream a partial message to a user via a raw Telegram Bot API call.

    The Telegram ``sendMessageDraft`` method (Bot API 10.0) streams a partial
    message to a user while the reply is still being generated. The streamed
    draft is **ephemeral**: it acts as a temporary 30-second preview, so once the
    output is finalized the caller must still send the complete message with
    ``sendMessage`` to persist it in the chat. The method only targets **private
    chats**, requires ``chat_id`` and a non-zero ``draft_id`` and returns ``True``
    on success. Drafts sharing the same ``draft_id`` are animated into one
    another, so a single id should be reused across one streaming response.
    ``text`` is limited to 0-4096 characters after entities parsing; passing an
    empty string shows a "Thinking…" placeholder. ``message_thread_id`` targets a
    forum topic, and ``parse_mode``/``entities`` control text formatting (Telegram
    accepts at most one of the two).

    Because the pinned ``aiogram==3.3.0`` (Bot API 7.0) has no typed wrapper for
    this Bot API 10.0 method, this is an isolated raw helper: it POSTs the JSON
    payload to the ``sendMessageDraft`` HTTP endpoint via ``httpx`` and returns
    the Telegram ``result`` (``True``). A zero ``draft_id`` or an over-long
    ``text`` is rejected with :class:`SendMessageDraftError` before any request is
    made; transport failures and Telegram ``ok: false`` responses are raised as
    the same exception. The draft carries operator/Claude-provided text, so only
    structural metadata (chat, draft id, text length, placeholder flag) is logged,
    never the text itself.
    """
    if draft_id == 0:
        raise SendMessageDraftError("draft_id must be non-zero.")

    if len(text) > MESSAGE_DRAFT_TEXT_LIMIT:
        raise SendMessageDraftError(
            f"Draft text is too long: {len(text)} characters "
            f"(max {MESSAGE_DRAFT_TEXT_LIMIT})."
        )

    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "draft_id": draft_id,
        "text": text,
    }
    optional = {
        "message_thread_id": message_thread_id,
        "parse_mode": parse_mode,
        "entities": entities,
    }
    payload.update({key: value for key, value in optional.items() if value is not None})

    url = _build_api_url(bot, "sendMessageDraft")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "send_message_draft_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            chat_id=chat_id,
            draft_id=draft_id,
        )
        raise SendMessageDraftError(
            f"sendMessageDraft request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "send_message_draft_failed",
            error_code=error_code,
            error=description,
            chat_id=chat_id,
            draft_id=draft_id,
        )
        raise SendMessageDraftError(description, error_code=error_code)

    result = data.get("result", True)
    logger.info(
        "message_draft_sent",
        chat_id=chat_id,
        draft_id=draft_id,
        text_length=len(text),
        is_placeholder=not text,
        has_thread=message_thread_id is not None,
    )
    return result
