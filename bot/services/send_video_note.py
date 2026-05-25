from typing import Any, Optional

import structlog
from aiogram.exceptions import TelegramAPIError

logger = structlog.get_logger()


async def perform_send_video_note(
    bot: Any,
    *,
    chat_id: int,
    video_note: str,
    duration: Optional[int] = None,
    length: Optional[int] = None,
    thumbnail: Optional[str] = None,
    message_thread_id: Optional[int] = None,
    disable_notification: Optional[bool] = None,
    protect_content: Optional[bool] = None,
) -> Any:
    """Send a rounded square video message (video note) via the typed aiogram API.

    Calls the typed aiogram ``Bot.send_video_note()`` wrapper for the Telegram
    ``sendVideoNote`` method so the bot can deliver a generated or received clip
    as a playable rounded square video message instead of only a textual
    interpretation. The Telegram method requires ``chat_id`` and ``video_note``
    and returns the sent ``Message`` on success. Unlike ``sendVideo``, Telegram
    currently does **not** support sending video notes by URL, so ``video_note``
    must be a ``file_id`` of a video note that already exists on Telegram servers
    or an uploaded file; this helper accepts the ``file_id`` string form. Video
    notes have no caption and do not accept ``parse_mode``. ``duration`` (in
    seconds) and ``length`` (the diameter of the square video message) describe
    the clip and ``thumbnail`` sets a custom preview image. The parameters passed
    here are the ones available in the pinned ``aiogram==3.3.0`` (Bot API 7.0)
    typed wrapper.
    """
    try:
        result = await bot.send_video_note(
            chat_id=chat_id,
            video_note=video_note,
            duration=duration,
            length=length,
            thumbnail=thumbnail,
            message_thread_id=message_thread_id,
            disable_notification=disable_notification,
            protect_content=protect_content,
        )
    except TelegramAPIError as exc:
        logger.warning(
            "send_video_note_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            chat_id=chat_id,
        )
        raise

    logger.info(
        "video_note_sent",
        chat_id=chat_id,
        has_duration=duration is not None,
        has_length=length is not None,
        has_thumbnail=bool(thumbnail),
        protect_content=bool(protect_content),
        sent_message_id=getattr(result, "message_id", None),
    )
    return result
