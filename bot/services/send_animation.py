from typing import Any, Optional

import structlog
from aiogram.exceptions import TelegramAPIError

logger = structlog.get_logger()


async def perform_send_animation(
    bot: Any,
    *,
    chat_id: int,
    animation: str,
    caption: Optional[str] = None,
    parse_mode: Optional[str] = None,
    duration: Optional[int] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
    thumbnail: Optional[str] = None,
    has_spoiler: Optional[bool] = None,
    message_thread_id: Optional[int] = None,
    disable_notification: Optional[bool] = None,
    protect_content: Optional[bool] = None,
) -> Any:
    """Send an animation (GIF or soundless H.264 video) via the typed aiogram API.

    Calls the typed aiogram ``Bot.send_animation()`` wrapper for the Telegram
    ``sendAnimation`` method so the bot can deliver a generated or received
    GIF/animation as a playable looping clip instead of only a textual
    interpretation. The Telegram method requires ``chat_id`` and ``animation``
    and returns the sent ``Message`` on success. ``animation`` may be an
    HTTP(S) URL that Telegram fetches, a ``file_id`` of an animation that
    already exists on Telegram servers, or an uploaded file; this helper
    accepts the URL/``file_id`` string form. Telegram delivers GIF and
    H.264/MPEG-4 AVC files without sound, limits a file sent by URL to 20 MB,
    and limits the ``caption`` to 1024 characters after entities parsing.
    ``duration`` (in seconds), ``width`` and ``height`` describe the animation,
    ``thumbnail`` sets a custom preview image and ``has_spoiler`` covers the
    animation with a spoiler animation. The parameters passed here are the ones
    available in the pinned ``aiogram==3.3.0`` (Bot API 7.0) typed wrapper.
    """
    try:
        result = await bot.send_animation(
            chat_id=chat_id,
            animation=animation,
            caption=caption,
            parse_mode=parse_mode,
            duration=duration,
            width=width,
            height=height,
            thumbnail=thumbnail,
            has_spoiler=has_spoiler,
            message_thread_id=message_thread_id,
            disable_notification=disable_notification,
            protect_content=protect_content,
        )
    except TelegramAPIError as exc:
        logger.warning(
            "send_animation_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            chat_id=chat_id,
        )
        raise

    logger.info(
        "animation_sent",
        chat_id=chat_id,
        has_caption=bool(caption),
        has_thumbnail=bool(thumbnail),
        has_spoiler=bool(has_spoiler),
        protect_content=bool(protect_content),
        sent_message_id=getattr(result, "message_id", None),
    )
    return result
