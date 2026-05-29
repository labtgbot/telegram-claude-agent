from typing import Any, Optional

import httpx
import structlog

from bot.services.send_checklist import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()

MIN_PREMIUM_MONTHS = 3
MAX_PREMIUM_MONTHS = 12


class GiftPremiumSubscriptionError(Exception):
    """Raised when the raw ``giftPremiumSubscription`` Bot API call fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


async def perform_gift_premium_subscription(
    bot: Any,
    *,
    user_id: int,
    month_count: int,
    star_count: int,
    text: Optional[str] = None,
    text_parse_mode: Optional[str] = None,
    text_entities: Optional[list[dict[str, Any]]] = None,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> bool:
    """Gift Telegram Premium to a user through an isolated raw Bot API helper."""
    if user_id <= 0:
        raise GiftPremiumSubscriptionError("user_id must be a positive integer.")
    if not (MIN_PREMIUM_MONTHS <= month_count <= MAX_PREMIUM_MONTHS):
        raise GiftPremiumSubscriptionError(
            f"month_count must be between {MIN_PREMIUM_MONTHS} and "
            f"{MAX_PREMIUM_MONTHS}."
        )
    if star_count <= 0:
        raise GiftPremiumSubscriptionError("star_count must be a positive integer.")

    request_payload: dict[str, Any] = {
        "user_id": user_id,
        "month_count": month_count,
        "star_count": star_count,
    }
    optional = {
        "text": text,
        "text_parse_mode": text_parse_mode,
        "text_entities": text_entities,
    }
    request_payload.update(
        {key: value for key, value in optional.items() if value is not None}
    )

    url = _build_api_url(bot, "giftPremiumSubscription")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=request_payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "gift_premium_subscription_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            user_id=user_id,
            month_count=month_count,
            star_count=star_count,
        )
        raise GiftPremiumSubscriptionError(
            f"giftPremiumSubscription request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "gift_premium_subscription_failed",
            error_code=error_code,
            error=description,
            user_id=user_id,
            month_count=month_count,
            star_count=star_count,
        )
        raise GiftPremiumSubscriptionError(description, error_code=error_code)

    if data.get("result") is not True:
        logger.warning(
            "gift_premium_subscription_failed",
            error="unexpected result",
            user_id=user_id,
            month_count=month_count,
            star_count=star_count,
        )
        raise GiftPremiumSubscriptionError(
            "Telegram returned an unexpected giftPremiumSubscription result."
        )

    logger.info(
        "premium_subscription_gifted",
        user_id=user_id,
        month_count=month_count,
        star_count=star_count,
        has_text=bool(text),
    )
    return True
