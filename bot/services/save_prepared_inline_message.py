import json
from typing import Any, Optional

import httpx
import structlog

from bot.services.send_paid_media import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()


class SavePreparedInlineMessageError(Exception):
    """Raised when ``savePreparedInlineMessage`` validation or raw call fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


async def perform_save_prepared_inline_message(
    bot: Any,
    *,
    user_id: int,
    result: dict[str, Any],
    allow_user_chats: Optional[bool] = None,
    allow_bot_chats: Optional[bool] = None,
    allow_group_chats: Optional[bool] = None,
    allow_channel_chats: Optional[bool] = None,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> dict:
    """Save an inline message for a Telegram user via raw Bot API.

    ``savePreparedInlineMessage`` stores one ``InlineQueryResult`` that the user
    can later send through an inline-mode prepared message flow. The pinned
    ``aiogram==3.3.0`` has no typed wrapper for this Bot API method, so this
    helper posts directly to Telegram and returns the ``PreparedInlineMessage``
    result dict.
    """
    if user_id <= 0:
        raise SavePreparedInlineMessageError("user_id must be a positive integer")
    if not result:
        raise SavePreparedInlineMessageError("result is required")

    request_payload: dict[str, Any] = {
        "user_id": user_id,
        "result": json.dumps(result),
    }
    optional_flags = {
        "allow_user_chats": allow_user_chats,
        "allow_bot_chats": allow_bot_chats,
        "allow_group_chats": allow_group_chats,
        "allow_channel_chats": allow_channel_chats,
    }
    request_payload.update(
        {name: value for name, value in optional_flags.items() if value is not None}
    )
    url = _build_api_url(bot, "savePreparedInlineMessage")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=request_payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "save_prepared_inline_message_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            user_id=user_id,
        )
        raise SavePreparedInlineMessageError(
            f"savePreparedInlineMessage request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "save_prepared_inline_message_failed",
            error_code=error_code,
            error=description,
            user_id=user_id,
        )
        raise SavePreparedInlineMessageError(description, error_code=error_code)

    prepared_message = data.get("result") or {}
    logger.info(
        "prepared_inline_message_saved",
        user_id=user_id,
        result_type=result.get("type"),
        prepared_message_id=prepared_message.get("id"),
    )
    return prepared_message
