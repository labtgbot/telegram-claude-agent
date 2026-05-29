from html import escape
from typing import Any, Optional

import httpx
import structlog

from bot.services.create_new_sticker_set import _validate_required_text
from bot.services.get_sticker_set import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()


class SetCustomEmojiStickerSetThumbnailError(Exception):
    """Raised when raw ``setCustomEmojiStickerSetThumbnail`` fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


def validate_custom_emoji_id(custom_emoji_id: Optional[str]) -> Optional[str]:
    """Normalize the optional custom emoji id used as set thumbnail."""
    if custom_emoji_id is None:
        return None

    normalized = custom_emoji_id.strip()
    if normalized == "-":
        return None
    if not normalized:
        raise SetCustomEmojiStickerSetThumbnailError(
            "custom_emoji_id must not be empty."
        )
    return normalized


async def perform_set_custom_emoji_sticker_set_thumbnail(
    bot: Any,
    *,
    name: str,
    custom_emoji_id: Optional[str] = None,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> bool:
    """Set or clear the thumbnail of a bot-created custom emoji sticker set."""
    try:
        normalized_name = _validate_required_text(name, "name")
        normalized_custom_emoji_id = validate_custom_emoji_id(custom_emoji_id)
    except Exception as exc:
        raise SetCustomEmojiStickerSetThumbnailError(str(exc)) from exc

    payload: dict[str, Any] = {"name": normalized_name}
    if normalized_custom_emoji_id is not None:
        payload["custom_emoji_id"] = normalized_custom_emoji_id

    url = _build_api_url(bot, "setCustomEmojiStickerSetThumbnail")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "set_custom_emoji_sticker_set_thumbnail_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            sticker_set_name=normalized_name,
            has_custom_emoji_id=normalized_custom_emoji_id is not None,
        )
        raise SetCustomEmojiStickerSetThumbnailError(
            f"setCustomEmojiStickerSetThumbnail request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "set_custom_emoji_sticker_set_thumbnail_failed",
            error_code=error_code,
            error=description,
            sticker_set_name=normalized_name,
            has_custom_emoji_id=normalized_custom_emoji_id is not None,
        )
        raise SetCustomEmojiStickerSetThumbnailError(
            description,
            error_code=error_code,
        )

    logger.info(
        "custom_emoji_sticker_set_thumbnail_set",
        sticker_set_name=normalized_name,
        has_custom_emoji_id=normalized_custom_emoji_id is not None,
    )
    return bool(data.get("result"))


def format_set_custom_emoji_sticker_set_thumbnail_result(
    *,
    name: str,
    custom_emoji_id: Optional[str],
) -> str:
    """Format a successful ``setCustomEmojiStickerSetThumbnail`` result."""
    lines = [
        "<b>setCustomEmojiStickerSetThumbnail</b>",
        "Custom emoji sticker set thumbnail updated.",
        f"Name: <code>{escape(name)}</code>",
    ]
    normalized_custom_emoji_id = validate_custom_emoji_id(custom_emoji_id)
    if normalized_custom_emoji_id is None:
        lines.append("Custom emoji thumbnail: cleared")
    else:
        lines.append(
            "Custom emoji id: "
            f"<code>{escape(normalized_custom_emoji_id)}</code>"
        )
    return "\n".join(lines)
