from html import escape
from typing import Any, Optional

import httpx
import structlog

from bot.services.send_checklist import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()


class RefundStarPaymentError(Exception):
    """Raised when ``refundStarPayment`` validation or call fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


async def perform_refund_star_payment(
    bot: Any,
    *,
    user_id: int,
    telegram_payment_charge_id: str,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> bool:
    """Refund a Telegram Stars payment by charge id."""
    if not isinstance(user_id, int) or isinstance(user_id, bool):
        raise RefundStarPaymentError("user_id must be an integer.")
    if user_id <= 0:
        raise RefundStarPaymentError("user_id must be a positive integer.")

    telegram_payment_charge_id = telegram_payment_charge_id.strip()
    if not telegram_payment_charge_id:
        raise RefundStarPaymentError("telegram_payment_charge_id is required.")

    payload = {
        "user_id": user_id,
        "telegram_payment_charge_id": telegram_payment_charge_id,
    }
    url = _build_api_url(bot, "refundStarPayment")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "refund_star_payment_failed",
            user_id=user_id,
            telegram_payment_charge_id=telegram_payment_charge_id,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise RefundStarPaymentError(
            f"refundStarPayment request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "refund_star_payment_failed",
            user_id=user_id,
            telegram_payment_charge_id=telegram_payment_charge_id,
            error_code=error_code,
            error=description,
        )
        raise RefundStarPaymentError(description, error_code=error_code)

    result = data.get("result")
    if result is not True:
        raise RefundStarPaymentError(
            "Telegram returned an unexpected refundStarPayment result."
        )

    logger.info(
        "star_payment_refunded",
        user_id=user_id,
        telegram_payment_charge_id=telegram_payment_charge_id,
    )
    return True


def format_refund_star_payment_result(
    *,
    user_id: int,
    telegram_payment_charge_id: str,
    duplicate: bool = False,
) -> str:
    """Format a successful or idempotent ``refundStarPayment`` result."""
    status = (
        "refund already recorded in this bot process."
        if duplicate
        else "Stars payment refund accepted by Telegram."
    )
    return "\n".join(
        [
            "<b>refundStarPayment</b>",
            f"User id: <code>{escape(str(user_id))}</code>",
            "Telegram payment charge id: "
            f"<code>{escape(telegram_payment_charge_id)}</code>",
            f"Status: {status}",
            "Audit: reconcile this charge in /startransactions.",
        ]
    )
