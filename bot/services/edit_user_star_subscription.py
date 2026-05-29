from html import escape
from typing import Any, Optional

import httpx
import structlog

from bot.services.send_checklist import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()


class EditUserStarSubscriptionError(Exception):
    """Raised when ``editUserStarSubscription`` validation or call fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


async def perform_edit_user_star_subscription(
    bot: Any,
    *,
    user_id: int,
    telegram_payment_charge_id: str,
    is_canceled: bool,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> bool:
    """Edit a Telegram Stars subscription state by charge id."""
    if not isinstance(user_id, int) or isinstance(user_id, bool):
        raise EditUserStarSubscriptionError("user_id must be an integer.")
    if user_id <= 0:
        raise EditUserStarSubscriptionError("user_id must be a positive integer.")
    if not isinstance(is_canceled, bool):
        raise EditUserStarSubscriptionError("is_canceled must be a boolean.")

    telegram_payment_charge_id = telegram_payment_charge_id.strip()
    if not telegram_payment_charge_id:
        raise EditUserStarSubscriptionError("telegram_payment_charge_id is required.")

    payload = {
        "user_id": user_id,
        "telegram_payment_charge_id": telegram_payment_charge_id,
        "is_canceled": is_canceled,
    }
    url = _build_api_url(bot, "editUserStarSubscription")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "edit_user_star_subscription_failed",
            user_id=user_id,
            telegram_payment_charge_id=telegram_payment_charge_id,
            is_canceled=is_canceled,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise EditUserStarSubscriptionError(
            f"editUserStarSubscription request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "edit_user_star_subscription_failed",
            user_id=user_id,
            telegram_payment_charge_id=telegram_payment_charge_id,
            is_canceled=is_canceled,
            error_code=error_code,
            error=description,
        )
        raise EditUserStarSubscriptionError(description, error_code=error_code)

    result = data.get("result")
    if result is not True:
        raise EditUserStarSubscriptionError(
            "Telegram returned an unexpected editUserStarSubscription result."
        )

    logger.info(
        "user_star_subscription_edited",
        user_id=user_id,
        telegram_payment_charge_id=telegram_payment_charge_id,
        is_canceled=is_canceled,
    )
    return True


def format_edit_user_star_subscription_result(
    *,
    user_id: int,
    telegram_payment_charge_id: str,
    is_canceled: bool,
    duplicate: bool = False,
) -> str:
    """Format a successful or idempotent ``editUserStarSubscription`` result."""
    state = "canceled" if is_canceled else "active"
    status = (
        "subscription edit already recorded in this bot process."
        if duplicate
        else "Stars subscription update accepted by Telegram."
    )
    return "\n".join(
        [
            "<b>editUserStarSubscription</b>",
            f"User id: <code>{escape(str(user_id))}</code>",
            "Telegram payment charge id: "
            f"<code>{escape(telegram_payment_charge_id)}</code>",
            f"Target state: <code>{escape(state)}</code>",
            f"Status: {status}",
            "Audit: reconcile this subscription in billing records.",
        ]
    )
