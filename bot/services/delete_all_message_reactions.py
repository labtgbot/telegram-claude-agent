from html import escape
from typing import Any, Optional

import httpx
import structlog

from bot.services.send_checklist import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()


class DeleteAllMessageReactionsError(Exception):
    """Raised when ``deleteAllMessageReactions`` validation or raw call fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


async def perform_delete_all_message_reactions(
    bot: Any,
    *,
    chat_id: int,
    message_id: int,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> bool:
    """Delete all reactions from a message through raw Telegram Bot API."""
    if message_id < 1:
        raise DeleteAllMessageReactionsError("message_id must be a positive integer.")

    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
    }
    url = _build_api_url(bot, "deleteAllMessageReactions")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "delete_all_message_reactions_failed",
            chat_id=chat_id,
            message_id=message_id,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise DeleteAllMessageReactionsError(
            f"deleteAllMessageReactions request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "delete_all_message_reactions_failed",
            chat_id=chat_id,
            message_id=message_id,
            error_code=error_code,
            error=description,
        )
        raise DeleteAllMessageReactionsError(description, error_code=error_code)

    result = data.get("result")
    if result is not True:
        raise DeleteAllMessageReactionsError(
            "Telegram returned an unexpected deleteAllMessageReactions result."
        )

    logger.info(
        "all_message_reactions_deleted",
        chat_id=chat_id,
        message_id=message_id,
    )
    return True


def format_delete_all_message_reactions_result(
    *,
    chat_id: int,
    message_id: int,
) -> str:
    """Format a successful ``deleteAllMessageReactions`` result."""
    return "\n".join(
        [
            "<b>deleteAllMessageReactions</b>",
            f"Chat ID: {escape(str(chat_id))}",
            f"Message ID: {escape(str(message_id))}",
            "Status: all reactions deleted.",
        ]
    )
