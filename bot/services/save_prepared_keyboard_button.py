from typing import Any, Optional

import httpx
import structlog

from bot.services.send_paid_media import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()


class SavePreparedKeyboardButtonError(Exception):
    """Raised when ``savePreparedKeyboardButton`` validation or raw call fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


async def perform_save_prepared_keyboard_button(
    bot: Any,
    *,
    user_id: int,
    prepared_message_id: str,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> Any:
    """Save a prepared keyboard button for a Telegram Mini App user.

    ``savePreparedKeyboardButton`` persists a button that lets a Mini App user
    send a previously prepared inline message from a keyboard button. The
    pinned ``aiogram==3.3.0`` has no typed wrapper for this Bot API 10.0 method,
    so this helper posts directly to Telegram and returns the raw result dict.
    """
    if user_id <= 0:
        raise SavePreparedKeyboardButtonError("user_id must be a positive integer")
    prepared_message_id = prepared_message_id.strip()
    if not prepared_message_id:
        raise SavePreparedKeyboardButtonError("prepared_message_id is required")

    request_payload = {
        "user_id": user_id,
        "prepared_message_id": prepared_message_id,
    }
    url = _build_api_url(bot, "savePreparedKeyboardButton")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=request_payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "save_prepared_keyboard_button_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            user_id=user_id,
        )
        raise SavePreparedKeyboardButtonError(
            f"savePreparedKeyboardButton request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "save_prepared_keyboard_button_failed",
            error_code=error_code,
            error=description,
            user_id=user_id,
        )
        raise SavePreparedKeyboardButtonError(description, error_code=error_code)

    result = data.get("result")
    logger.info(
        "prepared_keyboard_button_saved",
        user_id=user_id,
        prepared_message_id=prepared_message_id,
        result_type=type(result).__name__,
    )
    return result
