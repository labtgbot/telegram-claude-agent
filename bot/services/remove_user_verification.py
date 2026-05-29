from typing import Any, Optional

import httpx
import structlog

from bot.services.send_checklist import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()


class RemoveUserVerificationError(Exception):
    """Raised when the raw ``removeUserVerification`` Bot API call fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


async def perform_remove_user_verification(
    bot: Any,
    *,
    user_id: int,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> bool:
    """Remove a user's Telegram verification through an isolated raw helper."""
    if user_id <= 0:
        raise RemoveUserVerificationError("user_id must be a positive integer.")

    request_payload: dict[str, Any] = {"user_id": user_id}
    url = _build_api_url(bot, "removeUserVerification")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=request_payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "remove_user_verification_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            user_id=user_id,
        )
        raise RemoveUserVerificationError(
            f"removeUserVerification request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "remove_user_verification_failed",
            error_code=error_code,
            error=description,
            user_id=user_id,
        )
        raise RemoveUserVerificationError(description, error_code=error_code)

    if data.get("result") is not True:
        logger.warning(
            "remove_user_verification_failed",
            error="unexpected result",
            user_id=user_id,
        )
        raise RemoveUserVerificationError(
            "Telegram returned an unexpected removeUserVerification result."
        )

    logger.info("user_verification_removed", user_id=user_id)
    return True
