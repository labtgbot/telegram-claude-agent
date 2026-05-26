from typing import Any, Optional

import structlog
from aiogram.exceptions import TelegramAPIError

logger = structlog.get_logger()


async def perform_send_media_group(
    bot: Any,
    *,
    chat_id: int,
    media: list[Any],
    message_thread_id: Optional[int] = None,
    disable_notification: Optional[bool] = None,
    protect_content: Optional[bool] = None,
) -> Any:
    """Send a group of media as a single album via the typed aiogram API.

    Calls the typed aiogram ``Bot.send_media_group()`` wrapper for the Telegram
    ``sendMediaGroup`` method so the bot can deliver several photos, videos,
    documents or audio files as one album instead of separate messages or only a
    textual interpretation. The Telegram method requires ``chat_id`` and
    ``media`` (an array of 2-10 ``InputMediaPhoto``, ``InputMediaVideo``,
    ``InputMediaDocument`` or ``InputMediaAudio`` items) and returns the list of
    sent ``Message`` objects on success. Telegram only allows a few type
    combinations in one album: documents must be grouped with documents and
    audio with audio, while photos and videos may be mixed; passing items of a
    single type therefore always yields a valid combination. A single album
    caption is expressed by setting the ``caption`` on the first item only. The
    parameters passed here are the ones available in the pinned
    ``aiogram==3.3.0`` (Bot API 7.0) typed wrapper.
    """
    try:
        result = await bot.send_media_group(
            chat_id=chat_id,
            media=media,
            message_thread_id=message_thread_id,
            disable_notification=disable_notification,
            protect_content=protect_content,
        )
    except TelegramAPIError as exc:
        logger.warning(
            "send_media_group_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            chat_id=chat_id,
        )
        raise

    sent_message_ids = (
        [getattr(item, "message_id", None) for item in result] if result else []
    )
    logger.info(
        "media_group_sent",
        chat_id=chat_id,
        media_count=len(media),
        protect_content=bool(protect_content),
        sent_message_ids=sent_message_ids,
    )
    return result
