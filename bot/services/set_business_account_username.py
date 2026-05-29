from typing import Any, Optional

import httpx
import structlog

from bot.services.send_checklist import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()

MAX_BUSINESS_ACCOUNT_USERNAME_LENGTH = 32
MIN_BUSINESS_ACCOUNT_USERNAME_LENGTH = 5


class SetBusinessAccountUsernameError(Exception):
    """Raised when ``setBusinessAccountUsername`` validation or raw call fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


async def perform_set_business_account_username(
    bot: Any,
    *,
    business_connection_id: str,
    username: str,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> bool:
    """Set the username of a connected Telegram business account."""
    business_connection_id = business_connection_id.strip()
    username = username.strip().lstrip("@")

    if not business_connection_id:
        raise SetBusinessAccountUsernameError("business_connection_id is required.")
    if not username:
        raise SetBusinessAccountUsernameError("username is required.")
    if not (
        MIN_BUSINESS_ACCOUNT_USERNAME_LENGTH
        <= len(username)
        <= MAX_BUSINESS_ACCOUNT_USERNAME_LENGTH
    ):
        raise SetBusinessAccountUsernameError(
            "username must be between "
            f"{MIN_BUSINESS_ACCOUNT_USERNAME_LENGTH} and "
            f"{MAX_BUSINESS_ACCOUNT_USERNAME_LENGTH} characters."
        )

    payload = {
        "business_connection_id": business_connection_id,
        "username": username,
    }
    url = _build_api_url(bot, "setBusinessAccountUsername")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "set_business_account_username_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            business_connection_id=business_connection_id,
        )
        raise SetBusinessAccountUsernameError(
            f"setBusinessAccountUsername request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "set_business_account_username_failed",
            error_code=error_code,
            error=description,
            business_connection_id=business_connection_id,
        )
        raise SetBusinessAccountUsernameError(description, error_code=error_code)

    result = data.get("result")
    if result is not True:
        raise SetBusinessAccountUsernameError(
            "Telegram returned an unexpected setBusinessAccountUsername result."
        )

    logger.info(
        "business_account_username_set",
        business_connection_id=business_connection_id,
    )
    return True
