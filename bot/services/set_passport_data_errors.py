import json
from typing import Any, Optional

import httpx
import structlog

from bot.services.send_paid_media import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()


class SetPassportDataErrorsError(Exception):
    """Raised when ``setPassportDataErrors`` validation or raw call fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


async def perform_set_passport_data_errors(
    bot: Any,
    *,
    user_id: int,
    errors: list[dict[str, Any]],
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> bool:
    """Send Telegram Passport validation errors through the raw Bot API.

    Telegram requires this method only after a user submitted Passport data to
    the bot. The pinned ``aiogram==3.3.0`` has no typed wrapper for this Bot API
    method, so the helper posts directly to Telegram and intentionally logs only
    counts and Telegram error metadata, not sensitive Passport field values.
    """
    if user_id <= 0:
        raise SetPassportDataErrorsError("user_id must be a positive integer")
    if not errors:
        raise SetPassportDataErrorsError("errors must contain at least one item")
    if not all(isinstance(error, dict) and error for error in errors):
        raise SetPassportDataErrorsError("each passport error must be a non-empty object")

    request_payload = {
        "user_id": user_id,
        "errors": json.dumps(errors),
    }
    url = _build_api_url(bot, "setPassportDataErrors")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=request_payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "set_passport_data_errors_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            user_id=user_id,
            error_count=len(errors),
        )
        raise SetPassportDataErrorsError(
            f"setPassportDataErrors request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "set_passport_data_errors_failed",
            error_code=error_code,
            error=description,
            user_id=user_id,
            error_count=len(errors),
        )
        raise SetPassportDataErrorsError(description, error_code=error_code)

    logger.info(
        "passport_data_errors_set",
        user_id=user_id,
        error_count=len(errors),
    )
    return bool(data.get("result", True))
