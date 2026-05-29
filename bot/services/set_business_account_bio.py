from typing import Any, Optional

import httpx
import structlog

from bot.services.send_checklist import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()

MAX_BUSINESS_ACCOUNT_BIO_LENGTH = 140


class SetBusinessAccountBioError(Exception):
    """Raised when ``setBusinessAccountBio`` validation or raw call fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


async def perform_set_business_account_bio(
    bot: Any,
    *,
    business_connection_id: str,
    bio: Optional[str] = None,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> bool:
    """Set or clear the bio of a connected Telegram business account."""
    business_connection_id = business_connection_id.strip()
    bio = bio.strip() if bio is not None else None

    if not business_connection_id:
        raise SetBusinessAccountBioError("business_connection_id is required.")
    if bio is not None and len(bio) > MAX_BUSINESS_ACCOUNT_BIO_LENGTH:
        raise SetBusinessAccountBioError(
            f"bio must be at most {MAX_BUSINESS_ACCOUNT_BIO_LENGTH} characters."
        )

    payload = {"business_connection_id": business_connection_id}
    if bio is not None:
        payload["bio"] = bio

    url = _build_api_url(bot, "setBusinessAccountBio")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "set_business_account_bio_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            business_connection_id=business_connection_id,
            has_bio=bio is not None,
        )
        raise SetBusinessAccountBioError(
            f"setBusinessAccountBio request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "set_business_account_bio_failed",
            error_code=error_code,
            error=description,
            business_connection_id=business_connection_id,
            has_bio=bio is not None,
        )
        raise SetBusinessAccountBioError(description, error_code=error_code)

    result = data.get("result")
    if result is not True:
        raise SetBusinessAccountBioError(
            "Telegram returned an unexpected setBusinessAccountBio result."
        )

    logger.info(
        "business_account_bio_set",
        business_connection_id=business_connection_id,
        has_bio=bio is not None,
    )
    return True
