from html import escape
from typing import Any, Optional

import httpx
import structlog

from bot.services.send_checklist import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()


class GetBusinessAccountStarBalanceError(Exception):
    """Raised when ``getBusinessAccountStarBalance`` validation or call fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


async def perform_get_business_account_star_balance(
    bot: Any,
    *,
    business_connection_id: str,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> dict[str, Any]:
    """Fetch the Telegram Star balance of a connected business account."""
    business_connection_id = business_connection_id.strip()
    if not business_connection_id:
        raise GetBusinessAccountStarBalanceError(
            "business_connection_id is required."
        )

    payload = {"business_connection_id": business_connection_id}
    url = _build_api_url(bot, "getBusinessAccountStarBalance")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "get_business_account_star_balance_failed",
            business_connection_id=business_connection_id,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise GetBusinessAccountStarBalanceError(
            f"getBusinessAccountStarBalance request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "get_business_account_star_balance_failed",
            business_connection_id=business_connection_id,
            error_code=error_code,
            error=description,
        )
        raise GetBusinessAccountStarBalanceError(
            description, error_code=error_code
        )

    result = data.get("result")
    if not isinstance(result, dict) or not isinstance(result.get("amount"), int):
        logger.warning(
            "get_business_account_star_balance_failed",
            business_connection_id=business_connection_id,
            error="unexpected result",
        )
        raise GetBusinessAccountStarBalanceError(
            "Telegram returned an unexpected business account Star balance result."
        )

    nanostar_amount = result.get("nanostar_amount")
    if nanostar_amount is not None and not isinstance(nanostar_amount, int):
        raise GetBusinessAccountStarBalanceError(
            "Telegram returned an unexpected nanostar_amount value."
        )

    logger.info(
        "business_account_star_balance_fetched",
        business_connection_id=business_connection_id,
        has_nanostar_amount=nanostar_amount is not None,
    )
    return result


def format_business_account_star_balance(
    balance: dict[str, Any],
    *,
    business_connection_id: str,
) -> str:
    """Render a compact HTML admin response for ``StarAmount``."""
    lines = [
        "<b>Business account Star balance</b>",
        f"Business connection: <code>{escape(business_connection_id)}</code>",
        f"Stars: <code>{escape(str(balance.get('amount', 'unknown')))}</code>",
    ]
    if balance.get("nanostar_amount") is not None:
        lines.append(
            f"Nanostars: <code>{escape(str(balance['nanostar_amount']))}</code>"
        )
    lines.append(
        "Read-only balance check. Transfers require a separate explicit command."
    )
    return "\n".join(lines)
