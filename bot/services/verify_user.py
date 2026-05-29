from typing import Any, Optional

import httpx
import structlog

from bot.services.send_checklist import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()

VERIFY_USER_DESCRIPTION_LIMIT = 70


class VerifyUserError(Exception):
    """Raised when the raw ``verifyUser`` Bot API call fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


async def perform_verify_user(
    bot: Any,
    *,
    user_id: int,
    custom_description: Optional[str] = None,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> bool:
    """Verify a user through an isolated raw Bot API helper."""
    if user_id <= 0:
        raise VerifyUserError("user_id must be a positive integer.")
    if (
        custom_description is not None
        and len(custom_description) > VERIFY_USER_DESCRIPTION_LIMIT
    ):
        raise VerifyUserError(
            f"custom_description must be at most {VERIFY_USER_DESCRIPTION_LIMIT} "
            "characters."
        )

    request_payload: dict[str, Any] = {"user_id": user_id}
    if custom_description is not None:
        request_payload["custom_description"] = custom_description

    url = _build_api_url(bot, "verifyUser")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=request_payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "verify_user_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            user_id=user_id,
            has_custom_description=custom_description is not None,
        )
        raise VerifyUserError(f"verifyUser request failed: {exc}") from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "verify_user_failed",
            error_code=error_code,
            error=description,
            user_id=user_id,
            has_custom_description=custom_description is not None,
        )
        raise VerifyUserError(description, error_code=error_code)

    if data.get("result") is not True:
        logger.warning(
            "verify_user_failed",
            error="unexpected result",
            user_id=user_id,
            has_custom_description=custom_description is not None,
        )
        raise VerifyUserError("Telegram returned an unexpected verifyUser result.")

    logger.info(
        "user_verified",
        user_id=user_id,
        has_custom_description=bool(custom_description),
    )
    return True
