from typing import Any, Optional

import structlog
from aiogram.exceptions import TelegramAPIError

logger = structlog.get_logger()


async def perform_send_audio(
    bot: Any,
    *,
    chat_id: int,
    audio: str,
    caption: Optional[str] = None,
    parse_mode: Optional[str] = None,
    duration: Optional[int] = None,
    performer: Optional[str] = None,
    title: Optional[str] = None,
    message_thread_id: Optional[int] = None,
    disable_notification: Optional[bool] = None,
    protect_content: Optional[bool] = None,
) -> Any:
    """Send an audio file into a chat via the typed aiogram API.

    Calls the typed aiogram ``Bot.send_audio()`` wrapper for the Telegram
    ``sendAudio`` method so the bot can deliver a generated or received sound
    clip as a playable music track instead of only a textual interpretation.
    The Telegram method requires ``chat_id`` and ``audio`` and returns the sent
    ``Message`` on success. ``audio`` may be an HTTP(S) URL that Telegram
    fetches, a ``file_id`` of an audio file that already exists on Telegram
    servers, or an uploaded file; this helper accepts the URL/``file_id`` string
    form. Telegram expects the audio to be in the ``.MP3`` or ``.M4A`` format,
    limits a file sent by URL or ``file_id`` to 20 MB, and limits the
    ``caption`` to 1024 characters after entities parsing. ``duration`` (in
    seconds), ``performer`` and ``title`` set the music metadata shown to the
    recipient. The parameters passed here are the ones available in the pinned
    ``aiogram==3.3.0`` (Bot API 7.0) typed wrapper.
    """
    try:
        result = await bot.send_audio(
            chat_id=chat_id,
            audio=audio,
            caption=caption,
            parse_mode=parse_mode,
            duration=duration,
            performer=performer,
            title=title,
            message_thread_id=message_thread_id,
            disable_notification=disable_notification,
            protect_content=protect_content,
        )
    except TelegramAPIError as exc:
        logger.warning(
            "send_audio_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            chat_id=chat_id,
        )
        raise

    logger.info(
        "audio_sent",
        chat_id=chat_id,
        has_caption=bool(caption),
        has_performer=bool(performer),
        has_title=bool(title),
        protect_content=bool(protect_content),
        sent_message_id=getattr(result, "message_id", None),
    )
    return result
