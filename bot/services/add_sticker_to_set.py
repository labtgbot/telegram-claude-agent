from html import escape
from typing import Any, Optional

import httpx
import structlog

from bot.services.create_new_sticker_set import _validate_required_text
from bot.services.get_sticker_set import DEFAULT_REQUEST_TIMEOUT, _build_api_url
from bot.services.upload_sticker_file import validate_sticker_format

logger = structlog.get_logger()


class AddStickerToSetError(Exception):
    """Raised when raw ``addStickerToSet`` validation or request fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


async def perform_add_sticker_to_set(
    bot: Any,
    *,
    user_id: int,
    name: str,
    sticker_format: str,
    sticker: str,
    emoji_list: list[str],
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> bool:
    """Add one pre-uploaded sticker to an existing Telegram sticker set."""
    if user_id <= 0:
        raise AddStickerToSetError("user_id must be a positive integer.")

    try:
        normalized_name = _validate_required_text(name, "name")
        normalized_format = validate_sticker_format(sticker_format)
        normalized_sticker = _validate_required_text(sticker, "sticker")
    except Exception as exc:
        raise AddStickerToSetError(str(exc)) from exc

    normalized_emoji_list = [emoji.strip() for emoji in emoji_list if emoji.strip()]
    if not normalized_emoji_list:
        raise AddStickerToSetError("emoji_list must contain at least one emoji.")

    payload = {
        "user_id": user_id,
        "name": normalized_name,
        "sticker": {
            "sticker": normalized_sticker,
            "format": normalized_format,
            "emoji_list": normalized_emoji_list,
        },
    }
    url = _build_api_url(bot, "addStickerToSet")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "add_sticker_to_set_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            sticker_set_name=normalized_name,
            user_id=user_id,
        )
        raise AddStickerToSetError(f"addStickerToSet request failed: {exc}") from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "add_sticker_to_set_failed",
            error_code=error_code,
            error=description,
            sticker_set_name=normalized_name,
            user_id=user_id,
        )
        raise AddStickerToSetError(description, error_code=error_code)

    logger.info(
        "sticker_added_to_set",
        sticker_set_name=normalized_name,
        user_id=user_id,
        sticker_format=normalized_format,
        emoji_count=len(normalized_emoji_list),
    )
    return bool(data.get("result"))


def format_add_sticker_to_set_result(
    *,
    user_id: int,
    name: str,
    sticker_format: str,
    sticker: str,
    emoji_list: list[str],
) -> str:
    """Format a successful ``addStickerToSet`` result for HTML responses."""
    return "\n".join(
        [
            "<b>addStickerToSet</b>",
            "Sticker added to set.",
            f"User: <code>{user_id}</code>",
            f"Name: <code>{escape(name)}</code>",
            f"Format: {escape(sticker_format)}",
            f"Sticker file id: <code>{escape(sticker)}</code>",
            f"Emoji: {escape(', '.join(emoji_list))}",
        ]
    )
