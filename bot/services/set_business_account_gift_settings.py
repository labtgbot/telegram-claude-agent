from html import escape
from typing import Any, Optional

import httpx
import structlog

from bot.services.send_message_draft import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()

ACCEPTED_GIFT_TYPE_KEYS = (
    "unlimited_gifts",
    "limited_gifts",
    "unique_gifts",
    "premium_subscription",
    "gifts_from_channels",
)


class SetBusinessAccountGiftSettingsError(Exception):
    """Raised when ``setBusinessAccountGiftSettings`` validation or call fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


def normalize_accepted_gift_types(
    accepted_gift_types: dict[str, bool],
) -> dict[str, bool]:
    """Validate and order ``AcceptedGiftTypes`` payload for Telegram."""
    if not isinstance(accepted_gift_types, dict):
        raise SetBusinessAccountGiftSettingsError(
            "accepted_gift_types must be an object."
        )

    unknown_keys = set(accepted_gift_types) - set(ACCEPTED_GIFT_TYPE_KEYS)
    if unknown_keys:
        unknown = ", ".join(sorted(unknown_keys))
        raise SetBusinessAccountGiftSettingsError(
            f"accepted_gift_types contains unknown keys: {unknown}."
        )

    missing_keys = [
        key for key in ACCEPTED_GIFT_TYPE_KEYS if key not in accepted_gift_types
    ]
    if missing_keys:
        missing = ", ".join(missing_keys)
        raise SetBusinessAccountGiftSettingsError(
            f"accepted_gift_types is missing keys: {missing}."
        )

    normalized: dict[str, bool] = {}
    for key in ACCEPTED_GIFT_TYPE_KEYS:
        value = accepted_gift_types[key]
        if not isinstance(value, bool):
            raise SetBusinessAccountGiftSettingsError(
                f"accepted_gift_types.{key} must be a boolean."
            )
        normalized[key] = value

    return normalized


async def perform_set_business_account_gift_settings(
    bot: Any,
    *,
    business_connection_id: str,
    show_gift_button: bool,
    accepted_gift_types: dict[str, bool],
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> bool:
    """Change incoming gift settings for a connected business account."""
    business_connection_id = business_connection_id.strip()
    if not business_connection_id:
        raise SetBusinessAccountGiftSettingsError(
            "business_connection_id is required."
        )
    if not isinstance(show_gift_button, bool):
        raise SetBusinessAccountGiftSettingsError(
            "show_gift_button must be a boolean."
        )

    normalized_gift_types = normalize_accepted_gift_types(accepted_gift_types)
    payload = {
        "business_connection_id": business_connection_id,
        "show_gift_button": show_gift_button,
        "accepted_gift_types": normalized_gift_types,
    }
    url = _build_api_url(bot, "setBusinessAccountGiftSettings")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "set_business_account_gift_settings_failed",
            business_connection_id=business_connection_id,
            show_gift_button=show_gift_button,
            accepted_gift_type_count=sum(normalized_gift_types.values()),
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise SetBusinessAccountGiftSettingsError(
            f"setBusinessAccountGiftSettings request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "set_business_account_gift_settings_failed",
            business_connection_id=business_connection_id,
            show_gift_button=show_gift_button,
            accepted_gift_type_count=sum(normalized_gift_types.values()),
            error_code=error_code,
            error=description,
        )
        raise SetBusinessAccountGiftSettingsError(
            description, error_code=error_code
        )

    result = data.get("result")
    if result is not True:
        raise SetBusinessAccountGiftSettingsError(
            "Telegram returned an unexpected setBusinessAccountGiftSettings result."
        )

    logger.info(
        "business_account_gift_settings_set",
        business_connection_id=business_connection_id,
        show_gift_button=show_gift_button,
        accepted_gift_type_count=sum(normalized_gift_types.values()),
    )
    return True


def format_set_business_account_gift_settings_result(
    *,
    business_connection_id: str,
    show_gift_button: bool,
    accepted_gift_types: dict[str, bool],
) -> str:
    """Format a successful ``setBusinessAccountGiftSettings`` result."""
    enabled = [
        key for key in ACCEPTED_GIFT_TYPE_KEYS if accepted_gift_types.get(key)
    ]
    enabled_text = ", ".join(enabled) if enabled else "none"
    return "\n".join(
        [
            "<b>setBusinessAccountGiftSettings</b>",
            f"Business connection: {escape(business_connection_id)}",
            f"Gift button: {escape(str(show_gift_button).lower())}",
            f"Accepted gift types: {escape(enabled_text)}",
            "Status: business account gift settings updated.",
            "Rollback: run this command again with the previous values.",
        ]
    )
