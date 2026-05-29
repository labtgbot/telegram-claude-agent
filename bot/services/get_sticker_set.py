from html import escape
from typing import Any, Optional

import httpx
import structlog
from aiogram.types import StickerSet

logger = structlog.get_logger()

DEFAULT_REQUEST_TIMEOUT = 60.0


class GetStickerSetError(Exception):
    """Raised when raw ``getStickerSet`` fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


def _build_api_url(bot: Any, method: str) -> str:
    session = getattr(bot, "session", None)
    api = getattr(session, "api", None)
    api_url = getattr(api, "api_url", None)
    if callable(api_url):
        return api_url(token=bot.token, method=method)
    return f"https://api.telegram.org/bot{bot.token}/{method}"


async def perform_get_sticker_set(
    bot: Any,
    *,
    name: str,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> StickerSet:
    """Fetch a Telegram sticker set by name through raw Bot API.

    Telegram ``getStickerSet`` accepts the sticker set ``name`` and returns a
    ``StickerSet`` object with metadata and sticker items. The project pins
    ``aiogram==3.3.0``, so this method is isolated in a raw HTTP helper while
    the successful result is still parsed into aiogram's typed model.
    """
    url = _build_api_url(bot, "getStickerSet")
    payload = {"name": name}

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "get_sticker_set_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            sticker_set_name=name,
        )
        raise GetStickerSetError(f"getStickerSet request failed: {exc}") from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "get_sticker_set_failed",
            error_code=error_code,
            error=description,
            sticker_set_name=name,
        )
        raise GetStickerSetError(description, error_code=error_code)

    sticker_set = StickerSet.model_validate(data["result"])
    logger.info(
        "sticker_set_fetched",
        sticker_set_name=sticker_set.name,
        sticker_count=len(sticker_set.stickers),
        sticker_type=sticker_set.sticker_type,
    )
    return sticker_set


def format_sticker_set(sticker_set: StickerSet) -> str:
    """Format a ``getStickerSet`` result for HTML responses."""
    lines = [
        "<b>getStickerSet</b>",
        f"Name: <code>{escape(sticker_set.name)}</code>",
        f"Title: {escape(sticker_set.title)}",
        f"Type: {escape(sticker_set.sticker_type)}",
        f"Stickers: {len(sticker_set.stickers)}",
    ]

    thumbnail = getattr(sticker_set, "thumbnail", None)
    if thumbnail is not None:
        lines.append(
            "Thumbnail file_id: "
            f"<code>{escape(str(getattr(thumbnail, 'file_id', 'unknown')))}</code>"
        )

    for index, sticker in enumerate(sticker_set.stickers[:10], start=1):
        emoji = getattr(sticker, "emoji", None) or "no emoji"
        file_id = getattr(sticker, "file_id", "unknown")
        lines.append(
            f"{index}. {escape(str(emoji))} "
            f"<code>{escape(str(file_id))}</code>"
        )

    if len(sticker_set.stickers) > 10:
        lines.append(f"... and {len(sticker_set.stickers) - 10} more stickers.")

    return "\n".join(lines)
