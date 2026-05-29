from typing import Any, Optional

import httpx
import structlog

from bot.services.send_checklist import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()


class ReadBusinessMessageError(Exception):
    """Raised when ``readBusinessMessage`` validation or raw call fails.

    The pinned ``aiogram==3.3.0`` predates Telegram Bot API 10.0 and does not
    expose a typed wrapper for this business-account method, so this helper
    calls the raw HTTP endpoint directly. ``error_code`` holds Telegram's
    ``error_code`` when the failure comes from a Telegram response.
    """

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


async def perform_read_business_message(
    bot: Any,
    *,
    business_connection_id: str,
    message_id: int,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> bool:
    """Mark a business-account message as read via raw Telegram Bot API.

    Telegram ``readBusinessMessage`` requires a live ``business_connection_id``
    owned by the connected business account and the target ``message_id``.
    Telegram enforces the ownership and permission checks; this helper validates
    only the local shape of the request before posting the payload. The command
    handler keeps the operation behind the strict admin allowlist.
    """
    business_connection_id = business_connection_id.strip()
    if not business_connection_id:
        raise ReadBusinessMessageError("business_connection_id is required.")
    if message_id <= 0:
        raise ReadBusinessMessageError("message_id must be a positive integer.")

    payload = {
        "business_connection_id": business_connection_id,
        "message_id": message_id,
    }
    url = _build_api_url(bot, "readBusinessMessage")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "read_business_message_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            business_connection_id=business_connection_id,
            message_id=message_id,
        )
        raise ReadBusinessMessageError(
            f"readBusinessMessage request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "read_business_message_failed",
            error_code=error_code,
            error=description,
            business_connection_id=business_connection_id,
            message_id=message_id,
        )
        raise ReadBusinessMessageError(description, error_code=error_code)

    result = data.get("result")
    if result is not True:
        raise ReadBusinessMessageError(
            "Telegram returned an unexpected readBusinessMessage result."
        )

    logger.info(
        "business_message_read",
        business_connection_id=business_connection_id,
        message_id=message_id,
    )
    return True
