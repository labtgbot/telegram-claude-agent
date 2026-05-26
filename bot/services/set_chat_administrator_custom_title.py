from html import escape
from typing import Any

import structlog
from aiogram.exceptions import TelegramAPIError

logger = structlog.get_logger()


async def perform_set_chat_administrator_custom_title(
    bot: Any,
    *,
    chat_id: int,
    user_id: int,
    custom_title: str,
) -> bool:
    """Set a custom title for a chat administrator via the typed aiogram API.

    Calls the typed aiogram ``Bot.set_chat_administrator_custom_title()``
    wrapper for the Telegram ``setChatAdministratorCustomTitle`` method. The
    bot must be an administrator in the target chat with the
    ``can_promote_members`` right.
    """
    try:
        result = await bot.set_chat_administrator_custom_title(
            chat_id=chat_id,
            user_id=user_id,
            custom_title=custom_title,
        )
    except TelegramAPIError as exc:
        logger.warning(
            "set_chat_administrator_custom_title_failed",
            chat_id=chat_id,
            user_id=user_id,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise

    logger.info(
        "set_chat_administrator_custom_title_succeeded",
        chat_id=chat_id,
        user_id=user_id,
        custom_title=custom_title,
    )
    return result


def format_set_chat_administrator_custom_title_result(
    *,
    chat_id: int,
    user_id: int,
    custom_title: str,
) -> str:
    """Format a successful setChatAdministratorCustomTitle result for HTML."""
    return "\n".join(
        [
            "<b>setChatAdministratorCustomTitle</b>",
            f"Chat ID: {escape(str(chat_id))}",
            f"User ID: {escape(str(user_id))}",
            f"Custom title: {escape(custom_title)}",
            "Status: custom title updated successfully.",
        ]
    )
