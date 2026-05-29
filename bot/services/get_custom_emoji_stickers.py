from html import escape
from typing import Any, Optional

import httpx
import structlog
from aiogram.types import Sticker

from bot.services.get_sticker_set import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()

MAX_CUSTOM_EMOJI_IDS = 200


class GetCustomEmojiStickersError(Exception):
    """Raised when raw ``getCustomEmojiStickers`` fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


class GetCustomEmojiStickersValidationError(ValueError):
    """Raised when ``getCustomEmojiStickers`` input is invalid locally."""


def validate_custom_emoji_ids(custom_emoji_ids: list[str]) -> list[str]:
    """Validate custom emoji ids before calling Telegram."""
    if not custom_emoji_ids:
        raise GetCustomEmojiStickersValidationError(
            "At least one custom emoji id is required."
        )
    if len(custom_emoji_ids) > MAX_CUSTOM_EMOJI_IDS:
        raise GetCustomEmojiStickersValidationError(
            f"At most {MAX_CUSTOM_EMOJI_IDS} custom emoji ids can be requested."
        )
    if any(not isinstance(item, str) or not item.strip() for item in custom_emoji_ids):
        raise GetCustomEmojiStickersValidationError(
            "Custom emoji ids must be non-empty strings."
        )
    return [item.strip() for item in custom_emoji_ids]


async def perform_get_custom_emoji_stickers(
    bot: Any,
    *,
    custom_emoji_ids: list[str],
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> list[Sticker]:
    """Fetch custom emoji stickers by id through raw Bot API.

    Telegram ``getCustomEmojiStickers`` accepts 1-200 custom emoji identifiers
    and returns the corresponding ``Sticker`` objects. It is read-only, needs no
    chat permissions or special allowed update types, and is isolated here
    because the project pins ``aiogram==3.3.0``.
    """
    normalized_ids = validate_custom_emoji_ids(custom_emoji_ids)
    url = _build_api_url(bot, "getCustomEmojiStickers")
    payload = {"custom_emoji_ids": normalized_ids}

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "get_custom_emoji_stickers_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            custom_emoji_ids_count=len(normalized_ids),
        )
        raise GetCustomEmojiStickersError(
            f"getCustomEmojiStickers request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "get_custom_emoji_stickers_failed",
            error_code=error_code,
            error=description,
            custom_emoji_ids_count=len(normalized_ids),
        )
        raise GetCustomEmojiStickersError(description, error_code=error_code)

    result = data.get("result")
    if not isinstance(result, list):
        logger.warning(
            "get_custom_emoji_stickers_failed",
            error="unexpected result",
            custom_emoji_ids_count=len(normalized_ids),
        )
        raise GetCustomEmojiStickersError(
            "Telegram returned an unexpected custom emoji stickers result."
        )

    stickers = [Sticker.model_validate(item) for item in result]
    logger.info(
        "custom_emoji_stickers_fetched",
        requested_count=len(normalized_ids),
        stickers_count=len(stickers),
        custom_emoji_ids=[
            sticker.custom_emoji_id
            for sticker in stickers
            if getattr(sticker, "custom_emoji_id", None)
        ],
    )
    return stickers


def format_custom_emoji_stickers(stickers: list[Sticker]) -> str:
    """Format a ``getCustomEmojiStickers`` result for HTML admin responses."""
    lines = [
        "<b>getCustomEmojiStickers</b>",
        f"Stickers: {len(stickers)}",
    ]
    if not stickers:
        lines.append("Telegram returned no stickers for the requested ids.")
        return "\n".join(lines)

    for index, sticker in enumerate(stickers[:10], start=1):
        emoji = getattr(sticker, "emoji", None) or "no emoji"
        custom_emoji_id = getattr(sticker, "custom_emoji_id", None) or "unknown"
        set_name = getattr(sticker, "set_name", None)
        file_id = getattr(sticker, "file_id", "unknown")
        line = (
            f"{index}. {escape(str(emoji))} "
            f"custom_emoji_id=<code>{escape(str(custom_emoji_id))}</code> "
            f"file_id=<code>{escape(str(file_id))}</code>"
        )
        if set_name:
            line += f" set=<code>{escape(str(set_name))}</code>"
        lines.append(line)

    if len(stickers) > 10:
        lines.append(f"... and {len(stickers) - 10} more stickers.")
    return "\n".join(lines)
