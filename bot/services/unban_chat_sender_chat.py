from html import escape
from typing import Any

import structlog
from aiogram.exceptions import TelegramAPIError

logger = structlog.get_logger()


async def perform_unban_chat_sender_chat(
    bot: Any,
    *,
    chat_id: int,
    sender_chat_id: int,
) -> bool:
    """Unban a sender chat from a target chat via the typed aiogram API.

    Calls the typed aiogram ``Bot.unban_chat_sender_chat()`` wrapper for the
    Telegram ``unbanChatSenderChat`` method. The target chat must be a
    supergroup or channel, and the bot must be an administrator there with the
    ``can_restrict_members`` right.
    """
    try:
        result = await bot.unban_chat_sender_chat(
            chat_id=chat_id,
            sender_chat_id=sender_chat_id,
        )
    except TelegramAPIError as exc:
        logger.warning(
            "unban_chat_sender_chat_failed",
            chat_id=chat_id,
            sender_chat_id=sender_chat_id,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise

    logger.info(
        "unban_chat_sender_chat_succeeded",
        chat_id=chat_id,
        sender_chat_id=sender_chat_id,
    )
    return result


def format_unban_sender_chat_result(chat_id: int, sender_chat_id: int) -> str:
    """Format a successful unbanChatSenderChat result for HTML parse mode."""
    return "\n".join(
        [
            "<b>unbanChatSenderChat</b>",
            f"Chat ID: {escape(str(chat_id))}",
            f"Sender chat ID: {escape(str(sender_chat_id))}",
            "Status: unbanned successfully.",
        ]
    )
