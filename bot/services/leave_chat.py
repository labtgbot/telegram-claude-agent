from html import escape
from typing import Any

import structlog
from aiogram.exceptions import TelegramAPIError

logger = structlog.get_logger()


async def perform_leave_chat(
    bot: Any,
    *,
    chat_id: int,
) -> bool:
    """Leave a group, supergroup, or channel via the typed aiogram API.

    Calls the typed aiogram ``Bot.leave_chat()`` wrapper for Telegram
    ``leaveChat``. The bot must currently be a member of the target chat.
    This is a destructive membership action and callers must guard it with a
    strict admin allowlist and explicit confirmation.
    """
    try:
        result = await bot.leave_chat(chat_id=chat_id)
    except TelegramAPIError as exc:
        logger.warning(
            "leave_chat_failed",
            chat_id=chat_id,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise

    logger.info(
        "leave_chat_succeeded",
        chat_id=chat_id,
        result=result,
    )
    return result


def format_leave_chat_result(*, chat_id: int) -> str:
    """Format a successful leaveChat result for HTML responses."""
    return "\n".join(
        [
            "<b>leaveChat</b>",
            f"Chat ID: {escape(str(chat_id))}",
            "Status: bot left the chat successfully.",
            "Rollback: add the bot to the chat again and restore required "
            "administrator rights manually.",
        ]
    )
