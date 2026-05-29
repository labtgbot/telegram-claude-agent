from html import escape
from typing import Any, Optional

import httpx
import structlog

from bot.services.send_checklist import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()


class TransferBusinessAccountStarsError(Exception):
    """Raised when ``transferBusinessAccountStars`` validation or call fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


async def perform_transfer_business_account_stars(
    bot: Any,
    *,
    business_connection_id: str,
    star_count: int,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> bool:
    """Transfer Telegram Stars from a business account to the bot balance."""
    business_connection_id = business_connection_id.strip()
    if not business_connection_id:
        raise TransferBusinessAccountStarsError(
            "business_connection_id is required."
        )
    if not isinstance(star_count, int):
        raise TransferBusinessAccountStarsError("star_count must be an integer.")
    if star_count <= 0:
        raise TransferBusinessAccountStarsError(
            "star_count must be a positive integer."
        )

    payload = {
        "business_connection_id": business_connection_id,
        "star_count": star_count,
    }
    url = _build_api_url(bot, "transferBusinessAccountStars")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "transfer_business_account_stars_failed",
            business_connection_id=business_connection_id,
            star_count=star_count,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise TransferBusinessAccountStarsError(
            f"transferBusinessAccountStars request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "transfer_business_account_stars_failed",
            business_connection_id=business_connection_id,
            star_count=star_count,
            error_code=error_code,
            error=description,
        )
        raise TransferBusinessAccountStarsError(
            description, error_code=error_code
        )

    result = data.get("result")
    if result is not True:
        raise TransferBusinessAccountStarsError(
            "Telegram returned an unexpected transferBusinessAccountStars result."
        )

    logger.info(
        "business_account_stars_transferred",
        business_connection_id=business_connection_id,
        star_count=star_count,
    )
    return True


def format_transfer_business_account_stars_result(
    *,
    business_connection_id: str,
    star_count: int,
) -> str:
    """Format a successful ``transferBusinessAccountStars`` result."""
    return "\n".join(
        [
            "<b>transferBusinessAccountStars</b>",
            f"Business connection: <code>{escape(business_connection_id)}</code>",
            f"Transferred Stars: <code>{escape(str(star_count))}</code>",
            "Status: Stars moved to the bot balance.",
            "Rollback: this transfer cannot be reversed by the bot.",
        ]
    )
