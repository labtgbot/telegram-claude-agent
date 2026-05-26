from html import escape
from typing import Any

import structlog
from aiogram.exceptions import TelegramAPIError

logger = structlog.get_logger()

SET_CHAT_TITLE_LIMIT = 128


async def perform_set_chat_title(
    bot: Any,
    *,
    chat_id: int,
    title: str,
) -> bool:
    """Set a chat title via the typed aiogram API.

    Calls Telegram ``setChatTitle`` through ``Bot.set_chat_title()``. The bot
    must be an administrator in the target group, supergroup or channel with
    the right to change chat information.
    """
    try:
        result = await bot.set_chat_title(chat_id=chat_id, title=title)
    except TelegramAPIError as exc:
        logger.warning(
            "set_chat_title_failed",
            chat_id=chat_id,
            title_length=len(title),
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise

    logger.info(
        "set_chat_title_succeeded",
        chat_id=chat_id,
        title_length=len(title),
    )
    return result


def format_set_chat_title_result(*, chat_id: int, title: str) -> str:
    """Format a successful ``setChatTitle`` result for HTML responses."""
    return "\n".join(
        [
            "<b>setChatTitle</b>",
            f"Chat ID: {escape(str(chat_id))}",
            f"Title: {escape(title)}",
            "Status: chat title updated.",
        ]
    )
