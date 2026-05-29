from html import escape
from typing import Any, Optional

import httpx
import structlog

from bot.services.create_new_sticker_set import _validate_required_text
from bot.services.get_sticker_set import DEFAULT_REQUEST_TIMEOUT, _build_api_url
from bot.services.upload_sticker_file import validate_sticker_format

logger = structlog.get_logger()


class SetStickerSetThumbnailError(Exception):
    """Raised when raw ``setStickerSetThumbnail`` validation or request fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


def validate_sticker_set_thumbnail(thumbnail: Optional[str]) -> Optional[str]:
    """Normalize the optional thumbnail file id."""
    if thumbnail is None:
        return None

    normalized = thumbnail.strip()
    if normalized == "-":
        return None
    if not normalized:
        raise SetStickerSetThumbnailError("thumbnail must not be empty.")
    return normalized


async def perform_set_sticker_set_thumbnail(
    bot: Any,
    *,
    name: str,
    user_id: int,
    sticker_format: str,
    thumbnail: Optional[str] = None,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> bool:
    """Set or clear the thumbnail of a bot-created Telegram sticker set."""
    if user_id <= 0:
        raise SetStickerSetThumbnailError("user_id must be a positive integer.")

    try:
        normalized_name = _validate_required_text(name, "name")
        normalized_format = validate_sticker_format(sticker_format)
        normalized_thumbnail = validate_sticker_set_thumbnail(thumbnail)
    except Exception as exc:
        raise SetStickerSetThumbnailError(str(exc)) from exc

    payload: dict[str, Any] = {
        "name": normalized_name,
        "user_id": user_id,
        "format": normalized_format,
    }
    if normalized_thumbnail is not None:
        payload["thumbnail"] = normalized_thumbnail

    url = _build_api_url(bot, "setStickerSetThumbnail")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "set_sticker_set_thumbnail_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            sticker_set_name=normalized_name,
            user_id=user_id,
            sticker_format=normalized_format,
            has_thumbnail=normalized_thumbnail is not None,
        )
        raise SetStickerSetThumbnailError(
            f"setStickerSetThumbnail request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "set_sticker_set_thumbnail_failed",
            error_code=error_code,
            error=description,
            sticker_set_name=normalized_name,
            user_id=user_id,
            sticker_format=normalized_format,
            has_thumbnail=normalized_thumbnail is not None,
        )
        raise SetStickerSetThumbnailError(description, error_code=error_code)

    logger.info(
        "sticker_set_thumbnail_set",
        sticker_set_name=normalized_name,
        user_id=user_id,
        sticker_format=normalized_format,
        has_thumbnail=normalized_thumbnail is not None,
    )
    return bool(data.get("result"))


def format_set_sticker_set_thumbnail_result(
    *,
    name: str,
    user_id: int,
    sticker_format: str,
    thumbnail: Optional[str],
) -> str:
    """Format a successful ``setStickerSetThumbnail`` result for HTML."""
    lines = [
        "<b>setStickerSetThumbnail</b>",
        "Sticker set thumbnail updated.",
        f"Name: <code>{escape(name)}</code>",
        f"User: <code>{user_id}</code>",
        f"Format: {escape(sticker_format)}",
    ]
    normalized_thumbnail = validate_sticker_set_thumbnail(thumbnail)
    if normalized_thumbnail is None:
        lines.append("Thumbnail: cleared")
    else:
        lines.append(f"Thumbnail file id: <code>{escape(normalized_thumbnail)}</code>")
    return "\n".join(lines)
