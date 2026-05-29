from typing import Any, Optional

import httpx
import structlog

from bot.services.send_checklist import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()

MAX_BUSINESS_ACCOUNT_NAME_LENGTH = 64


class SetBusinessAccountNameError(Exception):
    """Raised when ``setBusinessAccountName`` validation or raw call fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


async def perform_set_business_account_name(
    bot: Any,
    *,
    business_connection_id: str,
    first_name: str,
    last_name: Optional[str] = None,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> bool:
    """Set the name of a connected Telegram business account."""
    business_connection_id = business_connection_id.strip()
    first_name = first_name.strip()
    last_name = last_name.strip() if last_name is not None else None

    if not business_connection_id:
        raise SetBusinessAccountNameError("business_connection_id is required.")
    if not first_name:
        raise SetBusinessAccountNameError("first_name is required.")
    if len(first_name) > MAX_BUSINESS_ACCOUNT_NAME_LENGTH:
        raise SetBusinessAccountNameError(
            f"first_name must be at most {MAX_BUSINESS_ACCOUNT_NAME_LENGTH} characters."
        )
    if last_name is not None and len(last_name) > MAX_BUSINESS_ACCOUNT_NAME_LENGTH:
        raise SetBusinessAccountNameError(
            f"last_name must be at most {MAX_BUSINESS_ACCOUNT_NAME_LENGTH} characters."
        )

    payload = {
        "business_connection_id": business_connection_id,
        "first_name": first_name,
    }
    if last_name is not None:
        payload["last_name"] = last_name

    url = _build_api_url(bot, "setBusinessAccountName")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "set_business_account_name_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            business_connection_id=business_connection_id,
            has_last_name=last_name is not None,
        )
        raise SetBusinessAccountNameError(
            f"setBusinessAccountName request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "set_business_account_name_failed",
            error_code=error_code,
            error=description,
            business_connection_id=business_connection_id,
            has_last_name=last_name is not None,
        )
        raise SetBusinessAccountNameError(description, error_code=error_code)

    result = data.get("result")
    if result is not True:
        raise SetBusinessAccountNameError(
            "Telegram returned an unexpected setBusinessAccountName result."
        )

    logger.info(
        "business_account_name_set",
        business_connection_id=business_connection_id,
        has_last_name=last_name is not None,
    )
    return True
