from html import escape
from typing import Any, Optional

import structlog
from aiogram.exceptions import TelegramAPIError

logger = structlog.get_logger()


async def perform_unpin_chat_message(
    bot: Any,
    *,
    chat_id: int,
    message_id: Optional[int] = None,
) -> bool:
    """Unpin a chat message via the typed aiogram API.

    Calls Telegram ``unpinChatMessage`` through ``Bot.unpin_chat_message()``.
    The bot must be an administrator in the target chat with the
    ``can_pin_messages`` right in groups/supergroups or the ``can_edit_messages``
    right in channels. When ``message_id`` is omitted, Telegram unpins the most
    recently pinned message.
    """
    try:
        result = await bot.unpin_chat_message(
            chat_id=chat_id,
            message_id=message_id,
        )
    except TelegramAPIError as exc:
        logger.warning(
            "unpin_chat_message_failed",
            chat_id=chat_id,
            message_id=message_id,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise

    logger.info(
        "unpin_chat_message_succeeded",
        chat_id=chat_id,
        message_id=message_id,
    )
    return result


def format_unpin_chat_message_result(
    *,
    chat_id: int,
    message_id: Optional[int] = None,
) -> str:
    """Format a successful ``unpinChatMessage`` result for HTML responses."""
    target = (
        f"Message ID: {escape(str(message_id))}"
        if message_id is not None
        else "Message ID: most recent pinned message"
    )
    return "\n".join(
        [
            "<b>unpinChatMessage</b>",
            f"Chat ID: {escape(str(chat_id))}",
            target,
            "Status: chat message unpinned.",
        ]
    )
