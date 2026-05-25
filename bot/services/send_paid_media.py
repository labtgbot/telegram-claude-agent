import json
from typing import Any, Optional

import httpx
import structlog

logger = structlog.get_logger()

DEFAULT_REQUEST_TIMEOUT = 60.0


class SendPaidMediaError(Exception):
    """Raised when the raw ``sendPaidMedia`` Bot API call fails.

    The pinned ``aiogram==3.3.0`` (Bot API 7.0) predates the Bot API 7.6
    ``sendPaidMedia`` method and ships no typed wrapper for it, so this helper
    calls the raw HTTP endpoint directly. Failures (transport errors or a
    Telegram ``ok: false`` response) are surfaced through this dedicated
    exception instead of aiogram's ``TelegramAPIError`` so the command handler
    has a single, version-independent error type to catch. ``error_code`` holds
    the Telegram ``error_code`` when the failure comes from a Telegram response.
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


async def perform_send_paid_media(
    bot: Any,
    *,
    chat_id: int,
    star_count: int,
    media: list[dict[str, Any]],
    payload: Optional[str] = None,
    caption: Optional[str] = None,
    parse_mode: Optional[str] = None,
    show_caption_above_media: Optional[bool] = None,
    message_thread_id: Optional[int] = None,
    disable_notification: Optional[bool] = None,
    protect_content: Optional[bool] = None,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> dict:
    """Send paid media into a chat via a raw Telegram Bot API call.

    The Telegram ``sendPaidMedia`` method (introduced in Bot API 7.6) sends
    media that users must pay for with Telegram Stars to access. It requires
    ``chat_id``, ``star_count`` (the number of Telegram Stars to buy access;
    1-25000 as of Bot API 10.0) and ``media`` (a JSON-serialized array of up to
    10 ``InputPaidMedia`` items, each a ``photo`` or ``video``), and returns the
    sent ``Message`` on success. When ``chat_id`` points at a channel, all
    Telegram Star proceeds are credited to that channel's balance; otherwise
    they are credited to the bot's balance. The optional ``payload`` is a
    bot-defined string (0-128 bytes) that is not shown to the user and comes
    back in ``purchased_paid_media`` updates, and the ``caption`` is limited to
    1024 characters after entities parsing.

    Because the pinned ``aiogram==3.3.0`` (Bot API 7.0) has no typed wrapper for
    this Bot API 7.6 method, this is an isolated raw helper: it POSTs the JSON
    payload to the ``sendPaidMedia`` HTTP endpoint via ``httpx`` and returns the
    parsed ``result`` dict. The ``media`` array is JSON-serialized into the
    request body as Telegram expects. Transport failures and Telegram
    ``ok: false`` responses are raised as :class:`SendPaidMediaError`.
    """
    request_payload: dict[str, Any] = {
        "chat_id": chat_id,
        "star_count": star_count,
        "media": json.dumps(media),
    }
    optional = {
        "payload": payload,
        "caption": caption,
        "parse_mode": parse_mode,
        "show_caption_above_media": show_caption_above_media,
        "message_thread_id": message_thread_id,
        "disable_notification": disable_notification,
        "protect_content": protect_content,
    }
    request_payload.update(
        {key: value for key, value in optional.items() if value is not None}
    )

    url = _build_api_url(bot, "sendPaidMedia")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=request_payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "send_paid_media_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            chat_id=chat_id,
        )
        raise SendPaidMediaError(f"sendPaidMedia request failed: {exc}") from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "send_paid_media_failed",
            error_code=error_code,
            error=description,
            chat_id=chat_id,
        )
        raise SendPaidMediaError(description, error_code=error_code)

    result = data.get("result") or {}
    logger.info(
        "paid_media_sent",
        chat_id=chat_id,
        star_count=star_count,
        media_count=len(media),
        has_caption=bool(caption),
        has_payload=payload is not None,
        protect_content=bool(protect_content),
        sent_message_id=result.get("message_id"),
    )
    return result
