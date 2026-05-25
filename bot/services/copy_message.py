from typing import Any, Optional

import structlog
from aiogram.exceptions import TelegramAPIError

logger = structlog.get_logger()


async def perform_copy_message(
    bot: Any,
    *,
    chat_id: int,
    from_chat_id: int,
    message_id: int,
    message_thread_id: Optional[int] = None,
    caption: Optional[str] = None,
    parse_mode: Optional[str] = None,
    disable_notification: Optional[bool] = None,
    protect_content: Optional[bool] = None,
) -> Any:
    """Copy a single message between chats via the typed aiogram API.

    Calls the typed aiogram ``Bot.copy_message()`` wrapper for the Telegram
    ``copyMessage`` method. Unlike ``forwardMessage``, ``copyMessage`` copies the
    message content as a brand new message **without a link to the original**
    (there is no "forwarded from" header), which makes it the right primitive
    when an operator wants to re-post moderated content without exposing the
    source. The Telegram method requires ``chat_id``, ``from_chat_id`` and
    ``message_id`` and returns the new ``MessageId`` on success. Service
    messages, paid media, giveaway/giveaway-winners and invoice messages cannot
    be copied, and the bot must be able to access ``from_chat_id`` (it is a
    member of that chat). An optional ``caption`` overrides the original caption
    of media messages. ``protect_content`` copies the message with forwarding
    and saving disabled, which keeps moderated content from being re-shared
    further. ``copyMessage`` handles a single message; album grouping is the job
    of ``copyMessages``.
    """
    try:
        result = await bot.copy_message(
            chat_id=chat_id,
            from_chat_id=from_chat_id,
            message_id=message_id,
            message_thread_id=message_thread_id,
            caption=caption,
            parse_mode=parse_mode,
            disable_notification=disable_notification,
            protect_content=protect_content,
        )
    except TelegramAPIError as exc:
        logger.warning(
            "copy_message_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            from_chat_id=from_chat_id,
            message_id=message_id,
        )
        raise

    logger.info(
        "message_copied",
        chat_id=chat_id,
        from_chat_id=from_chat_id,
        message_id=message_id,
        protect_content=bool(protect_content),
        copied_message_id=getattr(result, "message_id", None),
    )
    return result
