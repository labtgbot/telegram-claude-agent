from html import escape
from typing import Any, Optional

import httpx
import structlog

from bot.services.send_checklist import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()


class GetAvailableGiftsError(Exception):
    """Raised when the raw ``getAvailableGifts`` Bot API call fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


async def perform_get_available_gifts(
    bot: Any,
    *,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> dict[str, Any]:
    """Fetch Telegram's regular gift catalog through an isolated raw helper."""
    url = _build_api_url(bot, "getAvailableGifts")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json={})
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "get_available_gifts_failed",
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise GetAvailableGiftsError(
            f"getAvailableGifts request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "get_available_gifts_failed",
            error_code=error_code,
            error=description,
        )
        raise GetAvailableGiftsError(description, error_code=error_code)

    result = data.get("result")
    if not isinstance(result, dict) or not isinstance(result.get("gifts"), list):
        logger.warning("get_available_gifts_failed", error="unexpected result")
        raise GetAvailableGiftsError(
            "Telegram returned an unexpected available gifts result."
        )

    logger.info(
        "available_gifts_fetched",
        gifts_count=len(result["gifts"]),
        gift_ids=[
            gift.get("id")
            for gift in result["gifts"]
            if isinstance(gift, dict) and gift.get("id")
        ],
    )
    return result


def format_available_gifts(gifts: dict[str, Any]) -> str:
    """Render a compact HTML admin response for ``getAvailableGifts``."""
    gift_items = gifts.get("gifts", [])
    if not isinstance(gift_items, list):
        gift_items = []

    lines = [
        "<b>Available gifts</b>",
        f"Count: <code>{len(gift_items)}</code>",
    ]
    if not gift_items:
        lines.append("Telegram returned an empty gift catalog.")
        return "\n".join(lines)

    for gift in gift_items[:10]:
        if not isinstance(gift, dict):
            continue
        gift_id = escape(str(gift.get("id", "unknown")))
        star_count = gift.get("star_count")
        total_count = gift.get("total_count")
        remaining_count = gift.get("remaining_count")
        line = f"- <code>{gift_id}</code>"
        if star_count is not None:
            line += f" stars=<code>{escape(str(star_count))}</code>"
        if total_count is not None:
            line += f" total=<code>{escape(str(total_count))}</code>"
        if remaining_count is not None:
            line += f" remaining=<code>{escape(str(remaining_count))}</code>"
        lines.append(line)

    if len(gift_items) > 10:
        lines.append(f"...and <code>{len(gift_items) - 10}</code> more.")
    lines.append(
        "Read-only catalog fetch. Spending actions require separate explicit "
        "confirmation in their own commands."
    )
    return "\n".join(lines)
