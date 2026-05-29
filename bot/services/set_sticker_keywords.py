from html import escape
from typing import Any, Optional

import httpx
import structlog

from bot.services.create_new_sticker_set import _validate_required_text
from bot.services.get_sticker_set import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()

SET_STICKER_KEYWORDS_LIMIT = 20


class SetStickerKeywordsError(Exception):
    """Raised when raw ``setStickerKeywords`` validation or request fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


def validate_sticker_keywords(keywords: list[str]) -> list[str]:
    normalized = [keyword.strip() for keyword in keywords if keyword.strip()]
    if len(normalized) > SET_STICKER_KEYWORDS_LIMIT:
        raise SetStickerKeywordsError(
            f"keywords must contain at most {SET_STICKER_KEYWORDS_LIMIT} items."
        )
    return normalized


async def perform_set_sticker_keywords(
    bot: Any,
    *,
    sticker: str,
    keywords: list[str],
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> bool:
    """Replace search keywords for one sticker in a bot-created sticker set."""
    try:
        normalized_sticker = _validate_required_text(sticker, "sticker")
        normalized_keywords = validate_sticker_keywords(keywords)
    except Exception as exc:
        raise SetStickerKeywordsError(str(exc)) from exc

    payload = {
        "sticker": normalized_sticker,
        "keywords": normalized_keywords,
    }
    url = _build_api_url(bot, "setStickerKeywords")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "set_sticker_keywords_failed",
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise SetStickerKeywordsError(
            f"setStickerKeywords request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "set_sticker_keywords_failed",
            error_code=error_code,
            error=description,
        )
        raise SetStickerKeywordsError(description, error_code=error_code)

    logger.info(
        "sticker_keywords_set",
        keyword_count=len(normalized_keywords),
    )
    return bool(data.get("result"))


def format_set_sticker_keywords_result(
    *,
    sticker: str,
    keywords: list[str],
) -> str:
    """Format a successful ``setStickerKeywords`` result for HTML."""
    keyword_text = ", ".join(keywords) if keywords else "cleared"
    return "\n".join(
        [
            "<b>setStickerKeywords</b>",
            "Sticker keywords updated.",
            f"Sticker file id: <code>{escape(sticker)}</code>",
            f"Keywords: {escape(keyword_text)}",
        ]
    )
