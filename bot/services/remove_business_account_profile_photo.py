from html import escape
from typing import Any, Optional

import httpx
import structlog

from bot.services.send_message_draft import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()


class RemoveBusinessAccountProfilePhotoError(Exception):
    """Raised when ``removeBusinessAccountProfilePhoto`` validation or call fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


async def perform_remove_business_account_profile_photo(
    bot: Any,
    *,
    business_connection_id: str,
    is_public: bool = False,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> bool:
    """Remove a connected Telegram business account profile photo.

    The pinned ``aiogram==3.3.0`` predates Bot API 10.0 and has no typed
    wrapper for this method. Telegram validates that the supplied connection
    belongs to the connected business account and that the bot has permission
    to edit its profile photo.
    """
    business_connection_id = business_connection_id.strip()
    if not business_connection_id:
        raise RemoveBusinessAccountProfilePhotoError(
            "business_connection_id is required."
        )

    payload = {
        "business_connection_id": business_connection_id,
        **({"is_public": True} if is_public else {}),
    }
    url = _build_api_url(bot, "removeBusinessAccountProfilePhoto")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "remove_business_account_profile_photo_failed",
            business_connection_id=business_connection_id,
            is_public=is_public,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise RemoveBusinessAccountProfilePhotoError(
            f"removeBusinessAccountProfilePhoto request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "remove_business_account_profile_photo_failed",
            business_connection_id=business_connection_id,
            is_public=is_public,
            error_code=error_code,
            error=description,
        )
        raise RemoveBusinessAccountProfilePhotoError(
            description, error_code=error_code
        )

    result = data.get("result")
    if result is not True:
        raise RemoveBusinessAccountProfilePhotoError(
            "Telegram returned an unexpected removeBusinessAccountProfilePhoto result."
        )

    logger.info(
        "business_account_profile_photo_removed",
        business_connection_id=business_connection_id,
        is_public=is_public,
    )
    return True


def format_remove_business_account_profile_photo_result(
    *,
    business_connection_id: str,
    is_public: bool,
) -> str:
    """Format a successful ``removeBusinessAccountProfilePhoto`` result."""
    visibility = "public fallback photo" if is_public else "main profile photo"
    return "\n".join(
        [
            "<b>removeBusinessAccountProfilePhoto</b>",
            f"Business connection: {escape(business_connection_id)}",
            f"Removed: {escape(visibility)}",
            "Status: business account profile photo removed.",
            "Rollback: run <code>/setbusinessaccountprofilephoto</code> "
            "with the previous image.",
        ]
    )
