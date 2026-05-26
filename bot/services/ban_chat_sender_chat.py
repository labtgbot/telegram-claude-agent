from html import escape
from typing import Any

import structlog
from aiogram.exceptions import TelegramAPIError

logger = structlog.get_logger()


async def perform_ban_chat_sender_chat(
    bot: Any,
    *,
    chat_id: int,
    sender_chat_id: int,
) -> bool:
    """Ban a channel chat from sending messages into a target chat.

    Calls the typed aiogram ``Bot.ban_chat_sender_chat()`` wrapper for the
    Telegram ``banChatSenderChat`` method. The target chat must be a supergroup
    or channel, and the bot must be an administrator there with the
    ``can_restrict_members`` right.
    """
    try:
        result = await bot.ban_chat_sender_chat(
            chat_id=chat_id,
            sender_chat_id=sender_chat_id,
        )
    except TelegramAPIError as exc:
        logger.warning(
            "ban_chat_sender_chat_failed",
            chat_id=chat_id,
            sender_chat_id=sender_chat_id,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise

    logger.info(
        "ban_chat_sender_chat_succeeded",
        chat_id=chat_id,
        sender_chat_id=sender_chat_id,
    )
    return result


def format_ban_sender_chat_result(chat_id: int, sender_chat_id: int) -> str:
    """Format a successful banChatSenderChat result for HTML parse mode."""
    return "\n".join(
        [
            "<b>banChatSenderChat</b>",
            f"Chat ID: {escape(str(chat_id))}",
            f"Sender chat ID: {escape(str(sender_chat_id))}",
            "Status: banned successfully.",
        ]
    )
