from html import escape
from typing import Any, Optional

import httpx
import structlog

from bot.services.send_checklist import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()

GET_STAR_TRANSACTIONS_MIN_LIMIT = 1
GET_STAR_TRANSACTIONS_MAX_LIMIT = 100


class GetStarTransactionsError(Exception):
    """Raised when ``getStarTransactions`` validation or call fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


def normalize_get_star_transactions_options(
    *,
    offset: int | None = None,
    limit: int | None = None,
) -> dict[str, int]:
    """Validate optional ``getStarTransactions`` pagination parameters."""
    payload: dict[str, int] = {}
    if offset is not None:
        if not isinstance(offset, int) or isinstance(offset, bool):
            raise GetStarTransactionsError("offset must be an integer.")
        if offset < 0:
            raise GetStarTransactionsError("offset must be zero or greater.")
        payload["offset"] = offset
    if limit is not None:
        if not isinstance(limit, int) or isinstance(limit, bool):
            raise GetStarTransactionsError("limit must be an integer.")
        if not (
            GET_STAR_TRANSACTIONS_MIN_LIMIT
            <= limit
            <= GET_STAR_TRANSACTIONS_MAX_LIMIT
        ):
            raise GetStarTransactionsError("limit must be between 1 and 100.")
        payload["limit"] = limit
    return payload


async def perform_get_star_transactions(
    bot: Any,
    *,
    offset: int | None = None,
    limit: int | None = None,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> dict[str, Any]:
    """Fetch the bot's Telegram Star transaction history."""
    payload = normalize_get_star_transactions_options(offset=offset, limit=limit)
    url = _build_api_url(bot, "getStarTransactions")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "get_star_transactions_failed",
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise GetStarTransactionsError(
            f"getStarTransactions request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "get_star_transactions_failed",
            error_code=error_code,
            error=description,
        )
        raise GetStarTransactionsError(description, error_code=error_code)

    result = data.get("result")
    if not isinstance(result, dict) or not isinstance(result.get("transactions"), list):
        logger.warning("get_star_transactions_failed", error="unexpected result")
        raise GetStarTransactionsError(
            "Telegram returned an unexpected Star transactions result."
        )

    logger.info(
        "star_transactions_fetched",
        transaction_count=len(result["transactions"]),
        has_offset=offset is not None,
        has_limit=limit is not None,
    )
    return result


def format_star_transactions(
    transactions: dict[str, Any],
    *,
    offset: int | None = None,
    limit: int | None = None,
) -> str:
    """Render compact HTML admin diagnostics for ``StarTransactions``."""
    items = transactions.get("transactions", [])
    if not isinstance(items, list):
        items = []

    lines = [
        "<b>Bot Star transactions</b>",
        f"Count: <code>{len(items)}</code>",
    ]
    if offset is not None:
        lines.append(f"Offset: <code>{escape(str(offset))}</code>")
    if limit is not None:
        lines.append(f"Limit: <code>{escape(str(limit))}</code>")

    for item in items[:10]:
        if not isinstance(item, dict):
            continue
        transaction_id = item.get("id", "unknown")
        amount = item.get("amount", "unknown")
        date = item.get("date", "unknown")
        direction = "incoming" if item.get("source") is not None else "outgoing"
        line = (
            f"- <code>{escape(str(transaction_id))}</code>: "
            f"{escape(str(amount))} Stars, {direction}, date "
            f"<code>{escape(str(date))}</code>"
        )
        if item.get("nanostar_amount") is not None:
            line += f", nanostars <code>{escape(str(item['nanostar_amount']))}</code>"
        lines.append(line)

    if len(items) > 10:
        lines.append(f"...and {len(items) - 10} more transaction(s).")
    lines.append("Read-only audit view. Refunds use a separate confirmed command.")
    return "\n".join(lines)
