from html import escape
from typing import Any, Optional

import httpx
import structlog

from bot.services.send_checklist import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()


class UpgradeGiftError(Exception):
    """Raised when ``upgradeGift`` validation or call fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


async def perform_upgrade_gift(
    bot: Any,
    *,
    business_connection_id: str,
    owned_gift_id: str,
    keep_original_details: Optional[bool] = None,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> bool:
    """Upgrade a business account owned gift through raw Telegram Bot API."""
    business_connection_id = business_connection_id.strip()
    if not business_connection_id:
        raise UpgradeGiftError("business_connection_id is required.")

    owned_gift_id = owned_gift_id.strip()
    if not owned_gift_id:
        raise UpgradeGiftError("owned_gift_id is required.")

    if keep_original_details is not None and not isinstance(
        keep_original_details, bool
    ):
        raise UpgradeGiftError("keep_original_details must be a boolean.")

    payload: dict[str, Any] = {
        "business_connection_id": business_connection_id,
        "owned_gift_id": owned_gift_id,
    }
    if keep_original_details is not None:
        payload["keep_original_details"] = keep_original_details

    url = _build_api_url(bot, "upgradeGift")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "upgrade_gift_failed",
            business_connection_id=business_connection_id,
            owned_gift_id=owned_gift_id,
            keep_original_details=keep_original_details,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise UpgradeGiftError(f"upgradeGift request failed: {exc}") from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "upgrade_gift_failed",
            business_connection_id=business_connection_id,
            owned_gift_id=owned_gift_id,
            keep_original_details=keep_original_details,
            error_code=error_code,
            error=description,
        )
        raise UpgradeGiftError(description, error_code=error_code)

    result = data.get("result")
    if result is not True:
        raise UpgradeGiftError("Telegram returned an unexpected upgradeGift result.")

    logger.info(
        "gift_upgraded",
        business_connection_id=business_connection_id,
        owned_gift_id=owned_gift_id,
        keep_original_details=keep_original_details,
    )
    return True


def format_upgrade_gift_result(
    *,
    business_connection_id: str,
    owned_gift_id: str,
    keep_original_details: Optional[bool] = None,
) -> str:
    """Format a successful ``upgradeGift`` result."""
    lines = [
        "<b>upgradeGift</b>",
        f"Business connection: <code>{escape(business_connection_id)}</code>",
        f"Owned gift: <code>{escape(owned_gift_id)}</code>",
    ]
    if keep_original_details is not None:
        lines.append(
            "Keep original details: "
            f"<code>{escape(str(keep_original_details).lower())}</code>"
        )
    lines.extend(
        [
            "Status: gift upgraded.",
            "Rollback: this upgrade cannot be reversed by the bot.",
        ]
    )
    return "\n".join(lines)
