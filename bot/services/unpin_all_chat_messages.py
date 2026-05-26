from html import escape
from typing import Any

import structlog
from aiogram.exceptions import TelegramAPIError

logger = structlog.get_logger()


async def perform_unpin_all_chat_messages(
    bot: Any,
    *,
    chat_id: int,
) -> bool:
    """Unpin all chat messages via the typed aiogram API.

    Calls Telegram ``unpinAllChatMessages`` through
    ``Bot.unpin_all_chat_messages()``. The bot must be an administrator in the
    target chat with the ``can_pin_messages`` right in groups/supergroups or the
    ``can_edit_messages`` right in channels.
    """
    try:
        result = await bot.unpin_all_chat_messages(chat_id=chat_id)
    except TelegramAPIError as exc:
        logger.warning(
            "unpin_all_chat_messages_failed",
            chat_id=chat_id,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise

    logger.info("unpin_all_chat_messages_succeeded", chat_id=chat_id)
    return result


def format_unpin_all_chat_messages_result(*, chat_id: int) -> str:
    """Format a successful ``unpinAllChatMessages`` result for HTML responses."""
    return "\n".join(
        [
            "<b>unpinAllChatMessages</b>",
            f"Chat ID: {escape(str(chat_id))}",
            "Status: all pinned chat messages unpinned.",
        ]
    )
