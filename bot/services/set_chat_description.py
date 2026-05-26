from html import escape
from typing import Any

import structlog
from aiogram.exceptions import TelegramAPIError

logger = structlog.get_logger()

SET_CHAT_DESCRIPTION_LIMIT = 255


async def perform_set_chat_description(
    bot: Any,
    *,
    chat_id: int,
    description: str,
) -> bool:
    """Set a chat description via the typed aiogram API.

    Calls Telegram ``setChatDescription`` through
    ``Bot.set_chat_description()``. The bot must be an administrator in the
    target group, supergroup or channel with the right to change chat
    information.
    """
    try:
        result = await bot.set_chat_description(
            chat_id=chat_id,
            description=description,
        )
    except TelegramAPIError as exc:
        logger.warning(
            "set_chat_description_failed",
            chat_id=chat_id,
            description_length=len(description),
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise

    logger.info(
        "set_chat_description_succeeded",
        chat_id=chat_id,
        description_length=len(description),
    )
    return result


def format_set_chat_description_result(*, chat_id: int, description: str) -> str:
    """Format a successful ``setChatDescription`` result for HTML responses."""
    description_label = escape(description) if description else "<i>empty</i>"
    return "\n".join(
        [
            "<b>setChatDescription</b>",
            f"Chat ID: {escape(str(chat_id))}",
            f"Description: {description_label}",
            "Status: chat description updated.",
        ]
    )
