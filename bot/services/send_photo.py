from typing import Any, Optional

import structlog
from aiogram.exceptions import TelegramAPIError

logger = structlog.get_logger()


async def perform_send_photo(
    bot: Any,
    *,
    chat_id: int,
    photo: str,
    caption: Optional[str] = None,
    parse_mode: Optional[str] = None,
    message_thread_id: Optional[int] = None,
    has_spoiler: Optional[bool] = None,
    disable_notification: Optional[bool] = None,
    protect_content: Optional[bool] = None,
) -> Any:
    """Send a photo into a chat via the typed aiogram API.

    Calls the typed aiogram ``Bot.send_photo()`` wrapper for the Telegram
    ``sendPhoto`` method so the bot can deliver a generated or received image as
    an actual photo instead of only a textual interpretation. The Telegram
    method requires ``chat_id`` and ``photo`` and returns the sent ``Message``
    on success. ``photo`` may be an HTTP(S) URL that Telegram fetches, a
    ``file_id`` of a photo that already exists on Telegram servers, or an
    uploaded file; this helper accepts the URL/``file_id`` string form. Telegram
    limits the photo to 10 MB, its dimensions to a total of 10000 (width +
    height) and a width/height ratio of at most 20, and the ``caption`` to 1024
    characters after entities parsing. ``has_spoiler`` covers the photo with a
    spoiler animation. The parameters passed here are the ones available in the
    pinned ``aiogram==3.3.0`` (Bot API 7.0) typed wrapper.
    """
    try:
        result = await bot.send_photo(
            chat_id=chat_id,
            photo=photo,
            caption=caption,
            parse_mode=parse_mode,
            message_thread_id=message_thread_id,
            has_spoiler=has_spoiler,
            disable_notification=disable_notification,
            protect_content=protect_content,
        )
    except TelegramAPIError as exc:
        logger.warning(
            "send_photo_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            chat_id=chat_id,
        )
        raise

    logger.info(
        "photo_sent",
        chat_id=chat_id,
        has_caption=bool(caption),
        has_spoiler=bool(has_spoiler),
        protect_content=bool(protect_content),
        sent_message_id=getattr(result, "message_id", None),
    )
    return result
