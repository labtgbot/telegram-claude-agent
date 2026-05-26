from typing import Any, Optional

import structlog
from aiogram.exceptions import TelegramAPIError

logger = structlog.get_logger()


async def perform_forward_message(
    bot: Any,
    *,
    chat_id: int,
    from_chat_id: int,
    message_id: int,
    message_thread_id: Optional[int] = None,
    disable_notification: Optional[bool] = None,
    protect_content: Optional[bool] = None,
) -> Any:
    """Forward a single message between chats via the typed aiogram API.

    Calls the typed aiogram ``Bot.forward_message()`` wrapper for the Telegram
    ``forwardMessage`` method. The Telegram method requires ``chat_id``,
    ``from_chat_id`` and ``message_id`` and returns the sent ``Message`` on
    success. Service messages and messages with protected content cannot be
    forwarded, and the bot must be able to access ``from_chat_id`` (it is a
    member of that chat). ``protect_content`` forwards the message with
    forwarding and saving disabled, which keeps moderated content from being
    re-shared further. ``forwardMessage`` handles a single message; album
    grouping is the job of ``forwardMessages``.
    """
    try:
        result = await bot.forward_message(
            chat_id=chat_id,
            from_chat_id=from_chat_id,
            message_id=message_id,
            message_thread_id=message_thread_id,
            disable_notification=disable_notification,
            protect_content=protect_content,
        )
    except TelegramAPIError as exc:
        logger.warning(
            "forward_message_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            from_chat_id=from_chat_id,
            message_id=message_id,
        )
        raise

    logger.info(
        "message_forwarded",
        chat_id=chat_id,
        from_chat_id=from_chat_id,
        message_id=message_id,
        protect_content=bool(protect_content),
        forwarded_message_id=getattr(result, "message_id", None),
    )
    return result
