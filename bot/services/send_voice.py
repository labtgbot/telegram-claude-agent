from typing import Any, Optional

import structlog
from aiogram.exceptions import TelegramAPIError

logger = structlog.get_logger()


async def perform_send_voice(
    bot: Any,
    *,
    chat_id: int,
    voice: str,
    caption: Optional[str] = None,
    parse_mode: Optional[str] = None,
    duration: Optional[int] = None,
    message_thread_id: Optional[int] = None,
    disable_notification: Optional[bool] = None,
    protect_content: Optional[bool] = None,
) -> Any:
    """Send a voice message into a chat via the typed aiogram API.

    Calls the typed aiogram ``Bot.send_voice()`` wrapper for the Telegram
    ``sendVoice`` method so the bot can deliver a generated or received audio
    clip as a playable voice message (displayed as a waveform) instead of only
    a textual interpretation. The Telegram method requires ``chat_id`` and
    ``voice`` and returns the sent ``Message`` on success. ``voice`` may be an
    HTTP(S) URL that Telegram fetches, a ``file_id`` of a voice message that
    already exists on Telegram servers, or an uploaded file; this helper accepts
    the URL/``file_id`` string form. For the audio to be displayed as a playable
    voice message Telegram expects it to be in an ``.OGG`` file encoded with
    OPUS, or in ``.MP3`` or ``.M4A`` format; other formats may be sent as audio
    or document. Telegram limits a file sent by URL or ``file_id`` to 20 MB and
    limits the ``caption`` to 1024 characters after entities parsing.
    ``duration`` is the length of the voice message in seconds. The parameters
    passed here are the ones available in the pinned ``aiogram==3.3.0``
    (Bot API 7.0) typed wrapper.
    """
    try:
        result = await bot.send_voice(
            chat_id=chat_id,
            voice=voice,
            caption=caption,
            parse_mode=parse_mode,
            duration=duration,
            message_thread_id=message_thread_id,
            disable_notification=disable_notification,
            protect_content=protect_content,
        )
    except TelegramAPIError as exc:
        logger.warning(
            "send_voice_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            chat_id=chat_id,
        )
        raise

    logger.info(
        "voice_sent",
        chat_id=chat_id,
        has_caption=bool(caption),
        has_duration=duration is not None,
        protect_content=bool(protect_content),
        sent_message_id=getattr(result, "message_id", None),
    )
    return result
