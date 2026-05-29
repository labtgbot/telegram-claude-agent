from html import escape
from typing import Any, Optional

import httpx
import structlog

from bot.services.send_checklist import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()


class GetMyStarBalanceError(Exception):
    """Raised when ``getMyStarBalance`` validation or call fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


async def perform_get_my_star_balance(
    bot: Any,
    *,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> dict[str, Any]:
    """Fetch the bot's Telegram Star balance."""
    url = _build_api_url(bot, "getMyStarBalance")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json={})
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "get_my_star_balance_failed",
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise GetMyStarBalanceError(
            f"getMyStarBalance request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "get_my_star_balance_failed",
            error_code=error_code,
            error=description,
        )
        raise GetMyStarBalanceError(description, error_code=error_code)

    result = data.get("result")
    if not isinstance(result, dict) or not isinstance(result.get("amount"), int):
        logger.warning("get_my_star_balance_failed", error="unexpected result")
        raise GetMyStarBalanceError(
            "Telegram returned an unexpected bot Star balance result."
        )

    nanostar_amount = result.get("nanostar_amount")
    if nanostar_amount is not None and not isinstance(nanostar_amount, int):
        raise GetMyStarBalanceError(
            "Telegram returned an unexpected nanostar_amount value."
        )

    logger.info(
        "my_star_balance_fetched",
        has_nanostar_amount=nanostar_amount is not None,
    )
    return result


def format_my_star_balance(balance: dict[str, Any]) -> str:
    """Render a compact HTML admin response for ``StarAmount``."""
    lines = [
        "<b>Bot Star balance</b>",
        f"Stars: <code>{escape(str(balance.get('amount', 'unknown')))}</code>",
    ]
    if balance.get("nanostar_amount") is not None:
        lines.append(
            f"Nanostars: <code>{escape(str(balance['nanostar_amount']))}</code>"
        )
    lines.append("Read-only balance check. Transfers require separate commands.")
    return "\n".join(lines)
