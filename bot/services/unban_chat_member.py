from html import escape
from typing import Any, Optional

import structlog
from aiogram.exceptions import TelegramAPIError

logger = structlog.get_logger()


async def perform_unban_chat_member(
    bot: Any,
    *,
    chat_id: int,
    user_id: int,
    only_if_banned: Optional[bool] = None,
) -> bool:
    """Unban a user from a chat via the typed aiogram API.

    Calls the typed aiogram ``Bot.unban_chat_member()`` wrapper for the
    Telegram ``unbanChatMember`` method. The bot must be an administrator in
    the target chat with the ``can_restrict_members`` right.
    """
    try:
        result = await bot.unban_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            only_if_banned=only_if_banned,
        )
    except TelegramAPIError as exc:
        logger.warning(
            "unban_chat_member_failed",
            chat_id=chat_id,
            user_id=user_id,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise

    logger.info(
        "unban_chat_member_succeeded",
        chat_id=chat_id,
        user_id=user_id,
        only_if_banned=only_if_banned,
    )
    return result


def format_unban_result(
    chat_id: int,
    user_id: int,
    only_if_banned: Optional[bool],
) -> str:
    """Format a successful unbanChatMember result for HTML responses."""
    lines = [
        "<b>unbanChatMember</b>",
        f"Chat ID: {escape(str(chat_id))}",
        f"User ID: {escape(str(user_id))}",
    ]

    if only_if_banned is True:
        lines.append("Only if banned: yes")
    elif only_if_banned is False:
        lines.append("Only if banned: no")

    lines.append("Status: unbanned successfully.")
    return "\n".join(lines)
