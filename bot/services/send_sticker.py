from typing import Any, Optional

import structlog
from aiogram.exceptions import TelegramAPIError

logger = structlog.get_logger()


async def perform_send_sticker(
    bot: Any,
    *,
    chat_id: int,
    sticker: str,
    emoji: Optional[str] = None,
    message_thread_id: Optional[int] = None,
    disable_notification: Optional[bool] = None,
    protect_content: Optional[bool] = None,
) -> Any:
    """Send a sticker or custom emoji into a chat via the typed aiogram API.

    Calls the typed aiogram ``Bot.send_sticker()`` wrapper for the Telegram
    ``sendSticker`` method so an operator can post a reusable sticker/custom
    emoji asset by URL or ``file_id`` without mixing sticker delivery into the
    normal Claude chat flow. Telegram returns the sent ``Message`` on success.
    ``sticker`` may be an HTTP(S) URL that Telegram fetches, a ``file_id`` of a
    sticker already on Telegram servers, or an uploaded file; this helper
    accepts the URL/``file_id`` string form. Static stickers are limited to
    512 KB, animated stickers to 512 KB, video stickers to 256 KB, and sticker
    dimensions must fit in a 512x512 square. The optional ``emoji`` parameter
    associates the sticker with one or more emoji for Telegram clients. The
    parameters passed here are the ones available in the pinned
    ``aiogram==3.3.0`` typed wrapper.
    """
    try:
        result = await bot.send_sticker(
            chat_id=chat_id,
            sticker=sticker,
            message_thread_id=message_thread_id,
            emoji=emoji,
            disable_notification=disable_notification,
            protect_content=protect_content,
        )
    except TelegramAPIError as exc:
        logger.warning(
            "send_sticker_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            chat_id=chat_id,
        )
        raise

    logger.info(
        "sticker_sent",
        chat_id=chat_id,
        has_emoji=bool(emoji),
        protect_content=bool(protect_content),
        sent_message_id=getattr(result, "message_id", None),
    )
    return result
