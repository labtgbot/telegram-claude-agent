from html import escape
from typing import Any, Optional

import httpx
import structlog

from bot.services.create_new_sticker_set import _validate_required_text
from bot.services.get_sticker_set import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()


class SetStickerEmojiListError(Exception):
    """Raised when raw ``setStickerEmojiList`` validation or request fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


def validate_sticker_emoji_list(emoji_list: list[str]) -> list[str]:
    normalized = [emoji.strip() for emoji in emoji_list if emoji.strip()]
    if not normalized:
        raise SetStickerEmojiListError("emoji_list must contain at least one emoji.")
    return normalized


async def perform_set_sticker_emoji_list(
    bot: Any,
    *,
    sticker: str,
    emoji_list: list[str],
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> bool:
    """Replace the emoji list for one sticker in a bot-created sticker set."""
    try:
        normalized_sticker = _validate_required_text(sticker, "sticker")
        normalized_emoji_list = validate_sticker_emoji_list(emoji_list)
    except Exception as exc:
        raise SetStickerEmojiListError(str(exc)) from exc

    payload = {
        "sticker": normalized_sticker,
        "emoji_list": normalized_emoji_list,
    }
    url = _build_api_url(bot, "setStickerEmojiList")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "set_sticker_emoji_list_failed",
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise SetStickerEmojiListError(
            f"setStickerEmojiList request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "set_sticker_emoji_list_failed",
            error_code=error_code,
            error=description,
        )
        raise SetStickerEmojiListError(description, error_code=error_code)

    logger.info(
        "sticker_emoji_list_set",
        emoji_count=len(normalized_emoji_list),
    )
    return bool(data.get("result"))


def format_set_sticker_emoji_list_result(
    *,
    sticker: str,
    emoji_list: list[str],
) -> str:
    """Format a successful ``setStickerEmojiList`` result for HTML."""
    return "\n".join(
        [
            "<b>setStickerEmojiList</b>",
            "Sticker emoji list updated.",
            f"Sticker file id: <code>{escape(sticker)}</code>",
            f"Emoji: {escape(', '.join(emoji_list))}",
        ]
    )
