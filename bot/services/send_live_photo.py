from typing import Any, Optional

import httpx
import structlog

logger = structlog.get_logger()

DEFAULT_REQUEST_TIMEOUT = 60.0


class SendLivePhotoError(Exception):
    """Raised when the raw ``sendLivePhoto`` Bot API call fails.

    The pinned ``aiogram==3.3.0`` (Bot API 7.0) predates the Bot API 10.0
    ``sendLivePhoto`` method and ships no typed wrapper for it, so this helper
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


async def perform_send_live_photo(
    bot: Any,
    *,
    chat_id: int,
    live_photo: str,
    photo: str,
    caption: Optional[str] = None,
    parse_mode: Optional[str] = None,
    message_thread_id: Optional[int] = None,
    has_spoiler: Optional[bool] = None,
    show_caption_above_media: Optional[bool] = None,
    disable_notification: Optional[bool] = None,
    protect_content: Optional[bool] = None,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> dict:
    """Send a live photo into a chat via a raw Telegram Bot API call.

    The Telegram ``sendLivePhoto`` method (Bot API 10.0) sends a live photo: a
    short looping video paired with its static cover photo. It requires
    ``chat_id``, ``live_photo`` (the video) and ``photo`` (the static cover) and
    returns the sent ``Message`` on success. The ``live_photo`` video must be no
    longer than 10 seconds and must not exceed 10 MB. Per Telegram, **sending
    live photos by a URL is currently unsupported**, so ``live_photo`` and
    ``photo`` must be ``file_id`` strings of media that already exist on Telegram
    servers (or uploads, which this string-form helper does not cover). The
    ``caption`` is limited to 1024 characters after entities parsing.

    Because the pinned ``aiogram==3.3.0`` (Bot API 7.0) has no typed wrapper for
    this Bot API 10.0 method, this is an isolated raw helper: it POSTs the JSON
    payload to the ``sendLivePhoto`` HTTP endpoint via ``httpx`` and returns the
    parsed ``result`` dict. Transport failures and Telegram ``ok: false``
    responses are raised as :class:`SendLivePhotoError`.
    """
    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "live_photo": live_photo,
        "photo": photo,
    }
    optional = {
        "caption": caption,
        "parse_mode": parse_mode,
        "message_thread_id": message_thread_id,
        "has_spoiler": has_spoiler,
        "show_caption_above_media": show_caption_above_media,
        "disable_notification": disable_notification,
        "protect_content": protect_content,
    }
    payload.update({key: value for key, value in optional.items() if value is not None})

    url = _build_api_url(bot, "sendLivePhoto")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "send_live_photo_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            chat_id=chat_id,
        )
        raise SendLivePhotoError(f"sendLivePhoto request failed: {exc}") from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "send_live_photo_failed",
            error_code=error_code,
            error=description,
            chat_id=chat_id,
        )
        raise SendLivePhotoError(description, error_code=error_code)

    result = data.get("result") or {}
    logger.info(
        "live_photo_sent",
        chat_id=chat_id,
        has_caption=bool(caption),
        has_spoiler=bool(has_spoiler),
        protect_content=bool(protect_content),
        sent_message_id=result.get("message_id"),
    )
    return result
