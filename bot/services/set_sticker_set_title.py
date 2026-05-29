from html import escape
from typing import Any, Optional

import httpx
import structlog

from bot.services.create_new_sticker_set import _validate_required_text
from bot.services.get_sticker_set import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()

SET_STICKER_SET_TITLE_LIMIT = 64


class SetStickerSetTitleError(Exception):
    """Raised when raw ``setStickerSetTitle`` validation or request fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


def validate_sticker_set_title(title: str) -> str:
    normalized = title.strip()
    if not normalized:
        raise SetStickerSetTitleError("title must not be empty.")
    if len(normalized) > SET_STICKER_SET_TITLE_LIMIT:
        raise SetStickerSetTitleError(
            f"title must be up to {SET_STICKER_SET_TITLE_LIMIT} characters."
        )
    return normalized


async def perform_set_sticker_set_title(
    bot: Any,
    *,
    name: str,
    title: str,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> bool:
    """Change the title of a bot-created Telegram sticker set."""
    try:
        normalized_name = _validate_required_text(name, "name")
        normalized_title = validate_sticker_set_title(title)
    except Exception as exc:
        raise SetStickerSetTitleError(str(exc)) from exc

    payload = {
        "name": normalized_name,
        "title": normalized_title,
    }
    url = _build_api_url(bot, "setStickerSetTitle")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "set_sticker_set_title_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            sticker_set_name=normalized_name,
        )
        raise SetStickerSetTitleError(
            f"setStickerSetTitle request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "set_sticker_set_title_failed",
            error_code=error_code,
            error=description,
            sticker_set_name=normalized_name,
        )
        raise SetStickerSetTitleError(description, error_code=error_code)

    logger.info(
        "sticker_set_title_set",
        sticker_set_name=normalized_name,
        title_length=len(normalized_title),
    )
    return bool(data.get("result"))


def format_set_sticker_set_title_result(
    *,
    name: str,
    title: str,
) -> str:
    """Format a successful ``setStickerSetTitle`` result for HTML."""
    return "\n".join(
        [
            "<b>setStickerSetTitle</b>",
            "Sticker set title updated.",
            f"Name: <code>{escape(name)}</code>",
            f"Title: {escape(title)}",
        ]
    )
