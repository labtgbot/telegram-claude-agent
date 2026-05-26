from html import escape
from typing import Any

import structlog
from aiogram.exceptions import TelegramAPIError

logger = structlog.get_logger()


async def perform_delete_chat_photo(
    bot: Any,
    *,
    chat_id: int,
) -> bool:
    """Delete a chat photo via the typed aiogram API.

    Calls Telegram ``deleteChatPhoto`` through ``Bot.delete_chat_photo()``.
    The bot must be an administrator in the target group or supergroup with the
    right to change chat information. No special update subscription is needed
    for the command-driven scenario.
    """
    try:
        result = await bot.delete_chat_photo(chat_id=chat_id)
    except TelegramAPIError as exc:
        logger.warning(
            "delete_chat_photo_failed",
            chat_id=chat_id,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise

    logger.info("delete_chat_photo_succeeded", chat_id=chat_id)
    return result


def format_delete_chat_photo_result(*, chat_id: int) -> str:
    """Format a successful ``deleteChatPhoto`` result for HTML responses."""
    return "\n".join(
        [
            "<b>deleteChatPhoto</b>",
            f"Chat ID: {escape(str(chat_id))}",
            "Status: chat photo deleted.",
        ]
    )
