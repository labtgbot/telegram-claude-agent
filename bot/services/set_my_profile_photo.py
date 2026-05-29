from html import escape
from pathlib import Path
from typing import Any, Optional

import httpx
import structlog

from bot.services.send_message_draft import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()


class SetMyProfilePhotoError(Exception):
    """Raised when ``setMyProfilePhoto`` validation or raw upload fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


async def perform_set_my_profile_photo(
    bot: Any,
    *,
    photo_path: str,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> bool:
    """Set the bot's profile photo through a raw multipart Bot API upload."""
    path = Path(photo_path)
    if not path.is_file():
        raise SetMyProfilePhotoError(f"Photo file does not exist: {photo_path}")

    url = _build_api_url(bot, "setMyProfilePhoto")

    try:
        with path.open("rb") as photo_file:
            async with httpx.AsyncClient(timeout=request_timeout) as client:
                response = await client.post(
                    url,
                    files={"photo": (path.name, photo_file)},
                )
                data = response.json()
    except (OSError, httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "set_my_profile_photo_failed",
            photo_path=photo_path,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise SetMyProfilePhotoError(
            f"setMyProfilePhoto request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "set_my_profile_photo_failed",
            photo_path=photo_path,
            error_code=error_code,
            error=description,
        )
        raise SetMyProfilePhotoError(description, error_code=error_code)

    result = data.get("result", True)
    logger.info(
        "set_my_profile_photo_succeeded",
        photo_path=photo_path,
    )
    return result


def format_set_my_profile_photo_result(*, photo_path: str) -> str:
    """Format a successful ``setMyProfilePhoto`` result for HTML responses."""
    return "\n".join(
        [
            "<b>setMyProfilePhoto</b>",
            f"Photo: {escape(photo_path)}",
            "Status: bot profile photo updated.",
        ]
    )
