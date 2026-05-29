import json
from typing import Any, Optional

import httpx
import structlog

from bot.services.send_checklist import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()


class StopMessageLiveLocationError(Exception):
    """Raised when ``stopMessageLiveLocation`` validation or raw API call fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


async def perform_stop_message_live_location(
    bot: Any,
    *,
    chat_id: Optional[int] = None,
    message_id: Optional[int] = None,
    inline_message_id: Optional[str] = None,
    reply_markup: Optional[dict[str, Any]] = None,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> dict[str, Any] | bool:
    """Stop an active live location via Telegram Bot API."""
    inline_message_id = inline_message_id.strip() if inline_message_id else None

    has_chat_message = chat_id is not None or message_id is not None
    if inline_message_id and has_chat_message:
        raise StopMessageLiveLocationError(
            "Use either inline_message_id or chat_id with message_id."
        )
    if inline_message_id is None:
        if chat_id is None or message_id is None:
            raise StopMessageLiveLocationError(
                "chat_id and message_id are required unless inline_message_id is set."
            )
        if message_id <= 0:
            raise StopMessageLiveLocationError("message_id must be positive.")

    payload: dict[str, Any] = {}
    if inline_message_id is not None:
        payload["inline_message_id"] = inline_message_id
    else:
        payload["chat_id"] = chat_id
        payload["message_id"] = message_id
    if reply_markup is not None:
        payload["reply_markup"] = json.dumps(reply_markup)

    url = _build_api_url(bot, "stopMessageLiveLocation")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "stop_message_live_location_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            chat_id=chat_id,
            message_id=message_id,
            has_inline_message=inline_message_id is not None,
        )
        raise StopMessageLiveLocationError(
            f"stopMessageLiveLocation request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "stop_message_live_location_failed",
            error_code=error_code,
            error=description,
            chat_id=chat_id,
            message_id=message_id,
            has_inline_message=inline_message_id is not None,
        )
        raise StopMessageLiveLocationError(description, error_code=error_code)

    result = data.get("result", True)
    logger.info(
        "message_live_location_stopped",
        chat_id=chat_id,
        message_id=message_id,
        has_inline_message=inline_message_id is not None,
        has_reply_markup=reply_markup is not None,
    )
    return result
