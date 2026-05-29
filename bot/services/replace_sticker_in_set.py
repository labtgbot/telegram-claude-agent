from html import escape
from typing import Any, Optional

import httpx
import structlog

from bot.services.create_new_sticker_set import _validate_required_text
from bot.services.get_sticker_set import DEFAULT_REQUEST_TIMEOUT, _build_api_url
from bot.services.upload_sticker_file import validate_sticker_format

logger = structlog.get_logger()


class ReplaceStickerInSetError(Exception):
    """Raised when raw ``replaceStickerInSet`` validation or request fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


async def perform_replace_sticker_in_set(
    bot: Any,
    *,
    user_id: int,
    name: str,
    old_sticker: str,
    sticker_format: str,
    sticker: str,
    emoji_list: list[str],
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> bool:
    """Replace one sticker in a Telegram sticker set with a new uploaded file id."""
    if user_id <= 0:
        raise ReplaceStickerInSetError("user_id must be a positive integer.")

    try:
        normalized_name = _validate_required_text(name, "name")
        normalized_old_sticker = _validate_required_text(old_sticker, "old_sticker")
        normalized_format = validate_sticker_format(sticker_format)
        normalized_sticker = _validate_required_text(sticker, "sticker")
    except Exception as exc:
        raise ReplaceStickerInSetError(str(exc)) from exc

    normalized_emoji_list = [emoji.strip() for emoji in emoji_list if emoji.strip()]
    if not normalized_emoji_list:
        raise ReplaceStickerInSetError("emoji_list must contain at least one emoji.")

    payload = {
        "user_id": user_id,
        "name": normalized_name,
        "old_sticker": normalized_old_sticker,
        "sticker": {
            "sticker": normalized_sticker,
            "format": normalized_format,
            "emoji_list": normalized_emoji_list,
        },
    }
    url = _build_api_url(bot, "replaceStickerInSet")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "replace_sticker_in_set_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            sticker_set_name=normalized_name,
            user_id=user_id,
        )
        raise ReplaceStickerInSetError(
            f"replaceStickerInSet request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "replace_sticker_in_set_failed",
            error_code=error_code,
            error=description,
            sticker_set_name=normalized_name,
            user_id=user_id,
        )
        raise ReplaceStickerInSetError(description, error_code=error_code)

    logger.info(
        "sticker_replaced_in_set",
        sticker_set_name=normalized_name,
        user_id=user_id,
        sticker_format=normalized_format,
        emoji_count=len(normalized_emoji_list),
    )
    return bool(data.get("result"))


def format_replace_sticker_in_set_result(
    *,
    user_id: int,
    name: str,
    old_sticker: str,
    sticker_format: str,
    sticker: str,
    emoji_list: list[str],
) -> str:
    """Format a successful ``replaceStickerInSet`` result for HTML responses."""
    return "\n".join(
        [
            "<b>replaceStickerInSet</b>",
            "Sticker replaced in set.",
            f"User: <code>{user_id}</code>",
            f"Name: <code>{escape(name)}</code>",
            f"Old sticker file id: <code>{escape(old_sticker)}</code>",
            f"Format: {escape(sticker_format)}",
            f"New sticker file id: <code>{escape(sticker)}</code>",
            f"Emoji: {escape(', '.join(emoji_list))}",
        ]
    )
