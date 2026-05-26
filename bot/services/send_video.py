from typing import Any, Optional

import structlog
from aiogram.exceptions import TelegramAPIError

logger = structlog.get_logger()


async def perform_send_video(
    bot: Any,
    *,
    chat_id: int,
    video: str,
    caption: Optional[str] = None,
    parse_mode: Optional[str] = None,
    duration: Optional[int] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
    thumbnail: Optional[str] = None,
    has_spoiler: Optional[bool] = None,
    supports_streaming: Optional[bool] = None,
    message_thread_id: Optional[int] = None,
    disable_notification: Optional[bool] = None,
    protect_content: Optional[bool] = None,
) -> Any:
    """Send a video file into a chat via the typed aiogram API.

    Calls the typed aiogram ``Bot.send_video()`` wrapper for the Telegram
    ``sendVideo`` method so the bot can deliver a generated or received clip as
    a playable video instead of only a textual interpretation. The Telegram
    method requires ``chat_id`` and ``video`` and returns the sent ``Message``
    on success. ``video`` may be an HTTP(S) URL that Telegram fetches, a
    ``file_id`` of a video that already exists on Telegram servers, or an
    uploaded file; this helper accepts the URL/``file_id`` string form. Telegram
    clients support MPEG4 videos (other formats may be sent as a ``Document``),
    limit a file sent by URL to 20 MB, and limit the ``caption`` to 1024
    characters after entities parsing. ``duration`` (in seconds), ``width`` and
    ``height`` describe the video, ``thumbnail`` sets a custom preview image,
    ``has_spoiler`` covers the video with a spoiler animation and
    ``supports_streaming`` marks the file as suitable for streaming. The
    parameters passed here are the ones available in the pinned
    ``aiogram==3.3.0`` (Bot API 7.0) typed wrapper.
    """
    try:
        result = await bot.send_video(
            chat_id=chat_id,
            video=video,
            caption=caption,
            parse_mode=parse_mode,
            duration=duration,
            width=width,
            height=height,
            thumbnail=thumbnail,
            has_spoiler=has_spoiler,
            supports_streaming=supports_streaming,
            message_thread_id=message_thread_id,
            disable_notification=disable_notification,
            protect_content=protect_content,
        )
    except TelegramAPIError as exc:
        logger.warning(
            "send_video_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            chat_id=chat_id,
        )
        raise

    logger.info(
        "video_sent",
        chat_id=chat_id,
        has_caption=bool(caption),
        has_thumbnail=bool(thumbnail),
        has_spoiler=bool(has_spoiler),
        supports_streaming=bool(supports_streaming),
        protect_content=bool(protect_content),
        sent_message_id=getattr(result, "message_id", None),
    )
    return result
