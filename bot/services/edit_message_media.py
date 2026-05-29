import json
from typing import Any, Optional

import httpx
import structlog

from bot.services.send_checklist import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()

EDIT_MESSAGE_MEDIA_CAPTION_LIMIT = 1024
EDIT_MESSAGE_MEDIA_TYPES = {"animation", "audio", "document", "photo", "video"}


class EditMessageMediaError(Exception):
    """Raised when ``editMessageMedia`` validation or raw Bot API call fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


async def perform_edit_message_media(
    bot: Any,
    *,
    media_type: str,
    media: str,
    chat_id: Optional[int] = None,
    message_id: Optional[int] = None,
    inline_message_id: Optional[str] = None,
    caption: Optional[str] = None,
    parse_mode: Optional[str] = None,
    caption_entities: Optional[list[dict[str, Any]]] = None,
    show_caption_above_media: Optional[bool] = None,
    has_spoiler: Optional[bool] = None,
    reply_markup: Optional[dict[str, Any]] = None,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> dict[str, Any] | bool:
    """Edit a media message via Telegram Bot API ``editMessageMedia``."""
    media_type = (media_type or "").strip().lower()
    media = (media or "").strip()
    caption = caption.strip() if caption is not None else None
    inline_message_id = inline_message_id.strip() if inline_message_id else None

    if media_type not in EDIT_MESSAGE_MEDIA_TYPES:
        allowed = ", ".join(sorted(EDIT_MESSAGE_MEDIA_TYPES))
        raise EditMessageMediaError(f"media_type must be one of: {allowed}.")
    if not media:
        raise EditMessageMediaError("media is required.")

    has_chat_message = chat_id is not None or message_id is not None
    if inline_message_id and has_chat_message:
        raise EditMessageMediaError("Use either inline_message_id or chat_id with message_id.")
    if inline_message_id is None:
        if chat_id is None or message_id is None:
            raise EditMessageMediaError(
                "chat_id and message_id are required unless inline_message_id is set."
            )
        if message_id <= 0:
            raise EditMessageMediaError("message_id must be positive.")

    if caption is not None and len(caption) > EDIT_MESSAGE_MEDIA_CAPTION_LIMIT:
        raise EditMessageMediaError(
            f"caption must be at most {EDIT_MESSAGE_MEDIA_CAPTION_LIMIT} characters."
        )

    media_payload: dict[str, Any] = {"type": media_type, "media": media}
    optional_media = {
        "caption": caption,
        "parse_mode": parse_mode,
        "caption_entities": caption_entities,
        "show_caption_above_media": show_caption_above_media,
        "has_spoiler": has_spoiler,
    }
    media_payload.update(
        {key: value for key, value in optional_media.items() if value is not None}
    )

    payload: dict[str, Any] = {"media": json.dumps(media_payload)}
    if inline_message_id is not None:
        payload["inline_message_id"] = inline_message_id
    else:
        payload["chat_id"] = chat_id
        payload["message_id"] = message_id
    if reply_markup is not None:
        payload["reply_markup"] = json.dumps(reply_markup)

    url = _build_api_url(bot, "editMessageMedia")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "edit_message_media_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            chat_id=chat_id,
            message_id=message_id,
            has_inline_message=inline_message_id is not None,
            media_type=media_type,
        )
        raise EditMessageMediaError(f"editMessageMedia request failed: {exc}") from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "edit_message_media_failed",
            error_code=error_code,
            error=description,
            chat_id=chat_id,
            message_id=message_id,
            has_inline_message=inline_message_id is not None,
            media_type=media_type,
        )
        raise EditMessageMediaError(description, error_code=error_code)

    result = data.get("result", True)
    logger.info(
        "message_media_edited",
        chat_id=chat_id,
        message_id=message_id,
        has_inline_message=inline_message_id is not None,
        media_type=media_type,
        has_caption=bool(caption),
    )
    return result
