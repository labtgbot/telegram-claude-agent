from typing import Any, List, Optional

import structlog
from aiogram.exceptions import TelegramAPIError

logger = structlog.get_logger()


async def perform_forward_messages(
    bot: Any,
    *,
    chat_id: int,
    from_chat_id: int,
    message_ids: List[int],
    message_thread_id: Optional[int] = None,
    disable_notification: Optional[bool] = None,
    protect_content: Optional[bool] = None,
) -> Any:
    """Forward multiple messages between chats via the typed aiogram API.

    Calls the typed aiogram ``Bot.forward_messages()`` wrapper for the Telegram
    ``forwardMessages`` method. The Telegram method requires ``chat_id``,
    ``from_chat_id`` and ``message_ids`` (1-100 identifiers of messages in
    ``from_chat_id`` specified in a strictly increasing order) and returns an
    array of ``MessageId`` of the sent messages on success. Messages that can't
    be forwarded are skipped, so the returned list may be shorter than
    ``message_ids``; if none of them can be forwarded the call fails. Unlike
    ``forwardMessage``, ``forwardMessages`` preserves album grouping: messages
    that originally belonged to one album are re-sent together as an album.
    Service messages and messages with protected content cannot be forwarded,
    and the bot must be able to access ``from_chat_id`` (it is a member of that
    chat). ``protect_content`` forwards the messages with forwarding and saving
    disabled, which keeps moderated content from being re-shared further. The
    parameters passed here are the ones available in the pinned
    ``aiogram==3.3.0`` (Bot API 7.0) typed wrapper.
    """
    try:
        result = await bot.forward_messages(
            chat_id=chat_id,
            from_chat_id=from_chat_id,
            message_ids=message_ids,
            message_thread_id=message_thread_id,
            disable_notification=disable_notification,
            protect_content=protect_content,
        )
    except TelegramAPIError as exc:
        logger.warning(
            "forward_messages_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            from_chat_id=from_chat_id,
            message_ids=message_ids,
        )
        raise

    logger.info(
        "messages_forwarded",
        chat_id=chat_id,
        from_chat_id=from_chat_id,
        message_ids=message_ids,
        protect_content=bool(protect_content),
        forwarded_count=len(result) if hasattr(result, "__len__") else None,
    )
    return result
