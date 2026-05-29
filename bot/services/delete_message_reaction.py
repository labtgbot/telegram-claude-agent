from html import escape
from typing import Any

import structlog
from aiogram.exceptions import TelegramAPIError

logger = structlog.get_logger()


async def perform_delete_message_reaction(
    bot: Any,
    *,
    chat_id: int,
    message_id: int,
    user_id: int,
) -> bool:
    """Delete a user's reaction from a message via the typed aiogram API."""
    try:
        result = await bot.delete_message_reaction(
            chat_id=chat_id,
            message_id=message_id,
            user_id=user_id,
        )
    except TelegramAPIError as exc:
        logger.warning(
            "delete_message_reaction_failed",
            chat_id=chat_id,
            message_id=message_id,
            user_id=user_id,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise

    logger.info(
        "message_reaction_deleted",
        chat_id=chat_id,
        message_id=message_id,
        user_id=user_id,
    )
    return result


def format_delete_message_reaction_result(
    *,
    chat_id: int,
    message_id: int,
    user_id: int,
) -> str:
    """Format a successful ``deleteMessageReaction`` result for HTML responses."""
    return "\n".join(
        [
            "<b>deleteMessageReaction</b>",
            f"Chat ID: {escape(str(chat_id))}",
            f"Message ID: {escape(str(message_id))}",
            f"User ID: {escape(str(user_id))}",
            "Status: reaction deleted.",
        ]
    )
