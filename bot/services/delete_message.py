from html import escape
from typing import Any

import structlog
from aiogram.exceptions import TelegramAPIError

logger = structlog.get_logger()


async def perform_delete_message(
    bot: Any,
    *,
    chat_id: int,
    message_id: int,
) -> bool:
    """Delete one Telegram message via the typed aiogram API.

    Calls Telegram ``deleteMessage`` through ``Bot.delete_message()``. The bot
    can delete its own messages, service messages and, with the appropriate
    admin rights, other messages in groups, supergroups and channels. Telegram
    rejects messages that are too old, dice messages in private chats that are
    too new, or messages outside the bot's deletion rights.
    """
    try:
        result = await bot.delete_message(
            chat_id=chat_id,
            message_id=message_id,
        )
    except TelegramAPIError as exc:
        logger.warning(
            "delete_message_failed",
            chat_id=chat_id,
            message_id=message_id,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise

    logger.info(
        "message_deleted",
        chat_id=chat_id,
        message_id=message_id,
    )
    return result


def format_delete_message_result(
    *,
    chat_id: int,
    message_id: int,
) -> str:
    """Format a successful ``deleteMessage`` result for HTML responses."""
    return "\n".join(
        [
            "<b>deleteMessage</b>",
            f"Chat ID: {escape(str(chat_id))}",
            f"Message ID: {escape(str(message_id))}",
            "Status: message deleted.",
        ]
    )
