import json
from typing import Any, Optional

import httpx
import structlog

from bot.services.send_checklist import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()


class EditMessageLiveLocationError(Exception):
    """Raised when ``editMessageLiveLocation`` validation or raw API call fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


async def perform_edit_message_live_location(
    bot: Any,
    *,
    latitude: float,
    longitude: float,
    chat_id: Optional[int] = None,
    message_id: Optional[int] = None,
    inline_message_id: Optional[str] = None,
    horizontal_accuracy: Optional[float] = None,
    heading: Optional[int] = None,
    proximity_alert_radius: Optional[int] = None,
    reply_markup: Optional[dict[str, Any]] = None,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> dict[str, Any] | bool:
    """Edit an active live location via Telegram Bot API.

    The pinned ``aiogram==3.3.0`` may not expose all Bot API 10.0 parameters, so
    this helper uses the raw endpoint and keeps the compatibility surface
    isolated from command handlers.
    """
    inline_message_id = inline_message_id.strip() if inline_message_id else None

    has_chat_message = chat_id is not None or message_id is not None
    if inline_message_id and has_chat_message:
        raise EditMessageLiveLocationError(
            "Use either inline_message_id or chat_id with message_id."
        )
    if inline_message_id is None:
        if chat_id is None or message_id is None:
            raise EditMessageLiveLocationError(
                "chat_id and message_id are required unless inline_message_id is set."
            )
        if message_id <= 0:
            raise EditMessageLiveLocationError("message_id must be positive.")

    if not -90 <= latitude <= 90:
        raise EditMessageLiveLocationError("latitude must be between -90 and 90.")
    if not -180 <= longitude <= 180:
        raise EditMessageLiveLocationError("longitude must be between -180 and 180.")
    if horizontal_accuracy is not None and not 0 <= horizontal_accuracy <= 1500:
        raise EditMessageLiveLocationError(
            "horizontal_accuracy must be between 0 and 1500 meters."
        )
    if heading is not None and not 1 <= heading <= 360:
        raise EditMessageLiveLocationError("heading must be between 1 and 360.")
    if proximity_alert_radius is not None and not 1 <= proximity_alert_radius <= 100000:
        raise EditMessageLiveLocationError(
            "proximity_alert_radius must be between 1 and 100000 meters."
        )

    payload: dict[str, Any] = {
        "latitude": latitude,
        "longitude": longitude,
    }
    if inline_message_id is not None:
        payload["inline_message_id"] = inline_message_id
    else:
        payload["chat_id"] = chat_id
        payload["message_id"] = message_id

    optional = {
        "horizontal_accuracy": horizontal_accuracy,
        "heading": heading,
        "proximity_alert_radius": proximity_alert_radius,
        "reply_markup": json.dumps(reply_markup) if reply_markup is not None else None,
    }
    payload.update({key: value for key, value in optional.items() if value is not None})

    url = _build_api_url(bot, "editMessageLiveLocation")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "edit_message_live_location_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            chat_id=chat_id,
            message_id=message_id,
            has_inline_message=inline_message_id is not None,
        )
        raise EditMessageLiveLocationError(
            f"editMessageLiveLocation request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "edit_message_live_location_failed",
            error_code=error_code,
            error=description,
            chat_id=chat_id,
            message_id=message_id,
            has_inline_message=inline_message_id is not None,
        )
        raise EditMessageLiveLocationError(description, error_code=error_code)

    result = data.get("result", True)
    logger.info(
        "message_live_location_edited",
        chat_id=chat_id,
        message_id=message_id,
        has_inline_message=inline_message_id is not None,
        has_horizontal_accuracy=horizontal_accuracy is not None,
        has_heading=heading is not None,
        has_proximity_alert_radius=proximity_alert_radius is not None,
    )
    return result
