from html import escape
from typing import Any, Optional, Sequence

import httpx
import structlog
from aiogram.types import Sticker

logger = structlog.get_logger()

DEFAULT_REQUEST_TIMEOUT = 60.0


class GetForumTopicIconStickersError(Exception):
    """Raised when raw ``getForumTopicIconStickers`` fails."""

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


async def perform_get_forum_topic_icon_stickers(
    bot: Any,
    *,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> Sequence[Sticker]:
    """Fetch custom emoji stickers available for forum topic icons.

    Telegram ``getForumTopicIconStickers`` has no parameters and returns a list
    of ``Sticker`` objects that can be used as ``icon_custom_emoji_id`` when
    creating or editing forum topics. The project pins ``aiogram==3.3.0``, so
    this Bot API method is called through an isolated raw HTTP helper while the
    returned payload is still parsed into aiogram ``Sticker`` models.
    """
    url = _build_api_url(bot, "getForumTopicIconStickers")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json={})
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "get_forum_topic_icon_stickers_failed",
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise GetForumTopicIconStickersError(
            f"getForumTopicIconStickers request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "get_forum_topic_icon_stickers_failed",
            error_code=error_code,
            error=description,
        )
        raise GetForumTopicIconStickersError(description, error_code=error_code)

    stickers = [
        Sticker.model_validate(sticker_data)
        for sticker_data in data.get("result") or []
    ]
    logger.info(
        "forum_topic_icon_stickers_fetched",
        sticker_count=len(stickers),
    )
    return stickers


def format_forum_topic_icon_stickers(stickers: Sequence[Sticker]) -> str:
    lines = [
        "<b>getForumTopicIconStickers</b>",
        f"Stickers: {len(stickers)}",
    ]

    for index, sticker in enumerate(stickers, start=1):
        emoji = getattr(sticker, "emoji", None) or "no emoji"
        custom_emoji_id = getattr(sticker, "custom_emoji_id", None) or "none"
        set_name = getattr(sticker, "set_name", None)
        lines.append(
            f"{index}. {escape(str(emoji))} "
            f"custom_emoji_id: <code>{escape(str(custom_emoji_id))}</code>"
        )
        if set_name:
            lines.append(f"   Set: {escape(str(set_name))}")

    return "\n".join(lines)
