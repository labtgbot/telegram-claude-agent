from html import escape
from typing import Any, Optional

import structlog
from aiogram.exceptions import TelegramAPIError

logger = structlog.get_logger()


async def perform_pin_chat_message(
    bot: Any,
    *,
    chat_id: int,
    message_id: int,
    disable_notification: Optional[bool] = None,
) -> bool:
    """Pin a chat message via the typed aiogram API.

    Calls Telegram ``pinChatMessage`` through ``Bot.pin_chat_message()``. The
    bot must be an administrator in the target chat with the
    ``can_pin_messages`` right in groups/supergroups or the ``can_edit_messages``
    right in channels. ``disable_notification`` controls whether members are
    notified about the new pin; ``None`` leaves Telegram's default behaviour.
    """
    try:
        result = await bot.pin_chat_message(
            chat_id=chat_id,
            message_id=message_id,
            disable_notification=disable_notification,
        )
    except TelegramAPIError as exc:
        logger.warning(
            "pin_chat_message_failed",
            chat_id=chat_id,
            message_id=message_id,
            disable_notification=disable_notification,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise

    logger.info(
        "pin_chat_message_succeeded",
        chat_id=chat_id,
        message_id=message_id,
        disable_notification=disable_notification,
    )
    return result


def format_pin_chat_message_result(
    *,
    chat_id: int,
    message_id: int,
    disable_notification: Optional[bool] = None,
) -> str:
    """Format a successful ``pinChatMessage`` result for HTML responses."""
    if disable_notification is True:
        notification = "Notification: disabled."
    elif disable_notification is False:
        notification = "Notification: enabled."
    else:
        notification = "Notification: Telegram default."

    return "\n".join(
        [
            "<b>pinChatMessage</b>",
            f"Chat ID: {escape(str(chat_id))}",
            f"Message ID: {escape(str(message_id))}",
            notification,
            "Status: chat message pinned.",
        ]
    )
