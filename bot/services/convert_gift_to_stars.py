from html import escape
from typing import Any, Optional

import httpx
import structlog

from bot.services.send_checklist import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()


class ConvertGiftToStarsError(Exception):
    """Raised when ``convertGiftToStars`` validation or call fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


async def perform_convert_gift_to_stars(
    bot: Any,
    *,
    business_connection_id: str,
    owned_gift_id: str,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> bool:
    """Convert a regular gift owned by a business account to Telegram Stars."""
    business_connection_id = business_connection_id.strip()
    if not business_connection_id:
        raise ConvertGiftToStarsError("business_connection_id is required.")

    owned_gift_id = owned_gift_id.strip()
    if not owned_gift_id:
        raise ConvertGiftToStarsError("owned_gift_id is required.")

    payload = {
        "business_connection_id": business_connection_id,
        "owned_gift_id": owned_gift_id,
    }
    url = _build_api_url(bot, "convertGiftToStars")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "convert_gift_to_stars_failed",
            business_connection_id=business_connection_id,
            owned_gift_id=owned_gift_id,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise ConvertGiftToStarsError(
            f"convertGiftToStars request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "convert_gift_to_stars_failed",
            business_connection_id=business_connection_id,
            owned_gift_id=owned_gift_id,
            error_code=error_code,
            error=description,
        )
        raise ConvertGiftToStarsError(description, error_code=error_code)

    result = data.get("result")
    if result is not True:
        raise ConvertGiftToStarsError(
            "Telegram returned an unexpected convertGiftToStars result."
        )

    logger.info(
        "gift_converted_to_stars",
        business_connection_id=business_connection_id,
        owned_gift_id=owned_gift_id,
    )
    return True


def format_convert_gift_to_stars_result(
    *,
    business_connection_id: str,
    owned_gift_id: str,
) -> str:
    """Format a successful ``convertGiftToStars`` result."""
    return "\n".join(
        [
            "<b>convertGiftToStars</b>",
            f"Business connection: <code>{escape(business_connection_id)}</code>",
            f"Owned gift: <code>{escape(owned_gift_id)}</code>",
            "Status: gift converted to Telegram Stars.",
            "Rollback: this conversion cannot be reversed by the bot.",
        ]
    )
