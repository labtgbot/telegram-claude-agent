from typing import Any, List, Optional

import structlog
from aiogram.exceptions import TelegramAPIError

logger = structlog.get_logger()


async def perform_copy_messages(
    bot: Any,
    *,
    chat_id: int,
    from_chat_id: int,
    message_ids: List[int],
    message_thread_id: Optional[int] = None,
    disable_notification: Optional[bool] = None,
    protect_content: Optional[bool] = None,
    remove_caption: Optional[bool] = None,
) -> Any:
    """Copy multiple messages between chats via the typed aiogram API.

    Calls the typed aiogram ``Bot.copy_messages()`` wrapper for the Telegram
    ``copyMessages`` method. The Telegram method requires ``chat_id``,
    ``from_chat_id`` and ``message_ids`` (1-100 identifiers of messages in
    ``from_chat_id`` specified in a strictly increasing order) and returns an
    array of ``MessageId`` of the sent messages on success. Like ``copyMessage``
    and unlike ``forwardMessages``, the copies have **no link to the original**
    message (there is no "forwarded from" header), which makes it the right
    primitive when an operator wants to re-post moderated content without
    exposing the source. Like ``forwardMessages`` it **preserves album
    grouping**: messages that originally belonged to one album are re-sent
    together as an album. Messages that can't be copied are skipped, so the
    returned list may be shorter than ``message_ids``; service, giveaway,
    giveaway-winners and invoice messages can't be copied, and the bot must be
    able to access ``from_chat_id`` (it is a member of that chat).
    ``protect_content`` copies the messages with forwarding and saving disabled,
    which keeps moderated content from being re-shared further, and
    ``remove_caption`` drops the original captions of all copied messages.
    Unlike ``copyMessage`` there is no per-message ``caption`` override; the
    parameters passed here are the ones available in the pinned
    ``aiogram==3.3.0`` (Bot API 7.0) typed wrapper.
    """
    try:
        result = await bot.copy_messages(
            chat_id=chat_id,
            from_chat_id=from_chat_id,
            message_ids=message_ids,
            message_thread_id=message_thread_id,
            disable_notification=disable_notification,
            protect_content=protect_content,
            remove_caption=remove_caption,
        )
    except TelegramAPIError as exc:
        logger.warning(
            "copy_messages_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            from_chat_id=from_chat_id,
            message_ids=message_ids,
        )
        raise

    logger.info(
        "messages_copied",
        chat_id=chat_id,
        from_chat_id=from_chat_id,
        message_ids=message_ids,
        protect_content=bool(protect_content),
        remove_caption=bool(remove_caption),
        copied_count=len(result) if hasattr(result, "__len__") else None,
    )
    return result
