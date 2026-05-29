from typing import Any, Optional

import httpx
import structlog

from bot.services.send_checklist import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()

MAX_DELETE_BUSINESS_MESSAGES = 100


class DeleteBusinessMessagesError(Exception):
    """Raised when ``deleteBusinessMessages`` validation or raw call fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


async def perform_delete_business_messages(
    bot: Any,
    *,
    business_connection_id: str,
    message_ids: list[int],
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> bool:
    """Delete business-account messages through raw Telegram Bot API.

    Telegram ``deleteBusinessMessages`` deletes 1-100 messages owned by the
    supplied live business connection. The pinned ``aiogram==3.3.0`` has no
    typed wrapper for this Bot API 10.0 method, so this helper keeps the raw
    HTTP call isolated and leaves ownership/right checks to Telegram.
    """
    business_connection_id = business_connection_id.strip()
    if not business_connection_id:
        raise DeleteBusinessMessagesError("business_connection_id is required.")
    if not message_ids:
        raise DeleteBusinessMessagesError("at least one message_id is required.")
    if len(message_ids) > MAX_DELETE_BUSINESS_MESSAGES:
        raise DeleteBusinessMessagesError(
            f"message_ids must contain at most {MAX_DELETE_BUSINESS_MESSAGES} ids."
        )
    if any(message_id <= 0 for message_id in message_ids):
        raise DeleteBusinessMessagesError("message_ids must be positive integers.")

    payload = {
        "business_connection_id": business_connection_id,
        "message_ids": message_ids,
    }
    url = _build_api_url(bot, "deleteBusinessMessages")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "delete_business_messages_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            business_connection_id=business_connection_id,
            message_count=len(message_ids),
        )
        raise DeleteBusinessMessagesError(
            f"deleteBusinessMessages request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "delete_business_messages_failed",
            error_code=error_code,
            error=description,
            business_connection_id=business_connection_id,
            message_count=len(message_ids),
        )
        raise DeleteBusinessMessagesError(description, error_code=error_code)

    result = data.get("result")
    if result is not True:
        raise DeleteBusinessMessagesError(
            "Telegram returned an unexpected deleteBusinessMessages result."
        )

    logger.info(
        "business_messages_deleted",
        business_connection_id=business_connection_id,
        message_count=len(message_ids),
    )
    return True
