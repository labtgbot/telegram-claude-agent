import json
from typing import Any, Optional

import httpx
import structlog

from bot.services.send_checklist import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()

EDIT_MESSAGE_CAPTION_LIMIT = 1024


class EditMessageCaptionError(Exception):
    """Raised when ``editMessageCaption`` validation or raw Bot API call fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


async def perform_edit_message_caption(
    bot: Any,
    *,
    caption: Optional[str] = None,
    chat_id: Optional[int] = None,
    message_id: Optional[int] = None,
    inline_message_id: Optional[str] = None,
    parse_mode: Optional[str] = None,
    caption_entities: Optional[list[dict[str, Any]]] = None,
    show_caption_above_media: Optional[bool] = None,
    reply_markup: Optional[dict[str, Any]] = None,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> dict[str, Any] | bool:
    """Edit a media message caption via Telegram Bot API ``editMessageCaption``."""
    caption = caption.strip() if caption is not None else None
    inline_message_id = inline_message_id.strip() if inline_message_id else None

    has_chat_message = chat_id is not None or message_id is not None
    if inline_message_id and has_chat_message:
        raise EditMessageCaptionError(
            "Use either inline_message_id or chat_id with message_id."
        )
    if inline_message_id is None:
        if chat_id is None or message_id is None:
            raise EditMessageCaptionError(
                "chat_id and message_id are required unless inline_message_id is set."
            )
        if message_id <= 0:
            raise EditMessageCaptionError("message_id must be positive.")

    if caption is not None and len(caption) > EDIT_MESSAGE_CAPTION_LIMIT:
        raise EditMessageCaptionError(
            f"caption must be at most {EDIT_MESSAGE_CAPTION_LIMIT} characters."
        )

    payload: dict[str, Any] = {"caption": caption or ""}
    if inline_message_id is not None:
        payload["inline_message_id"] = inline_message_id
    else:
        payload["chat_id"] = chat_id
        payload["message_id"] = message_id

    optional = {
        "parse_mode": parse_mode,
        "caption_entities": (
            json.dumps(caption_entities) if caption_entities is not None else None
        ),
        "show_caption_above_media": show_caption_above_media,
        "reply_markup": json.dumps(reply_markup) if reply_markup is not None else None,
    }
    payload.update({key: value for key, value in optional.items() if value is not None})

    url = _build_api_url(bot, "editMessageCaption")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "edit_message_caption_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            chat_id=chat_id,
            message_id=message_id,
            has_inline_message=inline_message_id is not None,
        )
        raise EditMessageCaptionError(
            f"editMessageCaption request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "edit_message_caption_failed",
            error_code=error_code,
            error=description,
            chat_id=chat_id,
            message_id=message_id,
            has_inline_message=inline_message_id is not None,
        )
        raise EditMessageCaptionError(description, error_code=error_code)

    result = data.get("result", True)
    logger.info(
        "message_caption_edited",
        chat_id=chat_id,
        message_id=message_id,
        has_inline_message=inline_message_id is not None,
        has_caption=bool(caption),
        show_caption_above_media=show_caption_above_media,
    )
    return result
