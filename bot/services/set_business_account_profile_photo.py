from html import escape
from pathlib import Path
from typing import Any, Optional

import httpx
import structlog

from bot.services.send_message_draft import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()


class SetBusinessAccountProfilePhotoError(Exception):
    """Raised when ``setBusinessAccountProfilePhoto`` validation or upload fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


async def perform_set_business_account_profile_photo(
    bot: Any,
    *,
    business_connection_id: str,
    photo_path: str,
    is_public: bool = False,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> bool:
    """Set a connected Telegram business account profile photo."""
    business_connection_id = business_connection_id.strip()
    if not business_connection_id:
        raise SetBusinessAccountProfilePhotoError("business_connection_id is required.")

    path = Path(photo_path)
    if not path.is_file():
        raise SetBusinessAccountProfilePhotoError(
            f"Photo file does not exist: {photo_path}"
        )

    url = _build_api_url(bot, "setBusinessAccountProfilePhoto")

    try:
        with path.open("rb") as photo_file:
            async with httpx.AsyncClient(timeout=request_timeout) as client:
                response = await client.post(
                    url,
                    data={
                        "business_connection_id": business_connection_id,
                        "photo": '{"type":"static","photo":"attach://photo"}',
                        **({"is_public": "true"} if is_public else {}),
                    },
                    files={"photo": (path.name, photo_file, "image/jpeg")},
                )
                data = response.json()
    except (OSError, httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "set_business_account_profile_photo_failed",
            business_connection_id=business_connection_id,
            photo_path=photo_path,
            is_public=is_public,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise SetBusinessAccountProfilePhotoError(
            f"setBusinessAccountProfilePhoto request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "set_business_account_profile_photo_failed",
            business_connection_id=business_connection_id,
            photo_path=photo_path,
            is_public=is_public,
            error_code=error_code,
            error=description,
        )
        raise SetBusinessAccountProfilePhotoError(
            description, error_code=error_code
        )

    result = data.get("result")
    if result is not True:
        raise SetBusinessAccountProfilePhotoError(
            "Telegram returned an unexpected setBusinessAccountProfilePhoto result."
        )

    logger.info(
        "business_account_profile_photo_set",
        business_connection_id=business_connection_id,
        photo_path=photo_path,
        is_public=is_public,
    )
    return True


def format_set_business_account_profile_photo_result(
    *,
    business_connection_id: str,
    photo_path: str,
    is_public: bool,
) -> str:
    """Format a successful ``setBusinessAccountProfilePhoto`` result."""
    visibility = "public fallback photo" if is_public else "main profile photo"
    return "\n".join(
        [
            "<b>setBusinessAccountProfilePhoto</b>",
            f"Business connection: {escape(business_connection_id)}",
            f"Photo: {escape(photo_path)}",
            f"Visibility: {escape(visibility)}",
            "Status: business account profile photo updated.",
        ]
    )
