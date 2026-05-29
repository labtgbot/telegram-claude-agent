from typing import Any, Optional

import httpx
import structlog

from bot.services.send_message_draft import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()


class RemoveMyProfilePhotoError(Exception):
    """Raised when ``removeMyProfilePhoto`` raw Bot API call fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


async def perform_remove_my_profile_photo(
    bot: Any,
    *,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> bool:
    """Remove the bot's current profile photo through raw Bot API.

    aiogram 3.3.0 does not expose a typed wrapper for the Bot API 10.0
    ``removeMyProfilePhoto`` method, so the project keeps the raw HTTP call
    isolated in this service.
    """
    url = _build_api_url(bot, "removeMyProfilePhoto")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "remove_my_profile_photo_failed",
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise RemoveMyProfilePhotoError(
            f"removeMyProfilePhoto request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "remove_my_profile_photo_failed",
            error_code=error_code,
            error=description,
        )
        raise RemoveMyProfilePhotoError(description, error_code=error_code)

    result = data.get("result", True)
    logger.info("remove_my_profile_photo_succeeded")
    return result


def format_remove_my_profile_photo_result() -> str:
    """Format a successful ``removeMyProfilePhoto`` result for HTML responses."""
    return "\n".join(
        [
            "<b>removeMyProfilePhoto</b>",
            "Status: bot profile photo removed.",
            "Rollback: run <code>/setmyprofilephoto &lt;photo_path&gt;</code> "
            "with the previous image.",
        ]
    )
