from html import escape
from typing import Any

import structlog
from aiogram.exceptions import TelegramAPIError

logger = structlog.get_logger()


async def perform_get_chat_member_count(
    bot: Any,
    *,
    chat_id: int,
) -> int:
    """Fetch the number of members in a chat via the typed aiogram API.

    Calls the typed aiogram ``Bot.get_chat_member_count()`` wrapper for the
    Telegram ``getChatMemberCount`` method. The bot must already be able to
    access the target chat; for groups, supergroups and channels this usually
    means the bot is a member of the chat.
    """
    try:
        member_count = await bot.get_chat_member_count(chat_id=chat_id)
    except TelegramAPIError as exc:
        logger.warning(
            "get_chat_member_count_failed",
            chat_id=chat_id,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise

    logger.info(
        "chat_member_count_fetched",
        chat_id=chat_id,
        member_count=member_count,
    )
    return member_count


def format_get_chat_member_count_result(chat_id: int, member_count: int) -> str:
    """Format ``getChatMemberCount`` result for a concise HTML admin response."""
    return "\n".join(
        [
            "<b>getChatMemberCount</b>",
            f"Chat ID: {escape(str(chat_id))}",
            f"Member count: {escape(str(member_count))}",
        ]
    )
