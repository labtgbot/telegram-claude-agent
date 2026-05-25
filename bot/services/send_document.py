from typing import Any, Optional

import structlog
from aiogram.exceptions import TelegramAPIError

logger = structlog.get_logger()


async def perform_send_document(
    bot: Any,
    *,
    chat_id: int,
    document: str,
    caption: Optional[str] = None,
    parse_mode: Optional[str] = None,
    thumbnail: Optional[str] = None,
    message_thread_id: Optional[int] = None,
    disable_content_type_detection: Optional[bool] = None,
    disable_notification: Optional[bool] = None,
    protect_content: Optional[bool] = None,
) -> Any:
    """Send a general file into a chat via the typed aiogram API.

    Calls the typed aiogram ``Bot.send_document()`` wrapper for the Telegram
    ``sendDocument`` method so the bot can return large text, PDF or source
    artifacts as a downloadable document when ``sendMessage`` does not fit
    instead of only a textual interpretation. The Telegram method requires
    ``chat_id`` and ``document`` and returns the sent ``Message`` on success.
    ``document`` may be an HTTP(S) URL that Telegram fetches, a ``file_id`` of a
    file that already exists on Telegram servers, or an uploaded file; this
    helper accepts the URL/``file_id`` string form. Telegram limits a file sent
    by URL to 20 MB and the ``caption`` to 1024 characters after entities
    parsing. ``disable_content_type_detection`` turns off automatic server-side
    content type detection and ``thumbnail`` sets a custom preview image. The
    parameters passed here are the ones available in the pinned
    ``aiogram==3.3.0`` (Bot API 7.0) typed wrapper.
    """
    try:
        result = await bot.send_document(
            chat_id=chat_id,
            document=document,
            caption=caption,
            parse_mode=parse_mode,
            thumbnail=thumbnail,
            message_thread_id=message_thread_id,
            disable_content_type_detection=disable_content_type_detection,
            disable_notification=disable_notification,
            protect_content=protect_content,
        )
    except TelegramAPIError as exc:
        logger.warning(
            "send_document_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            chat_id=chat_id,
        )
        raise

    logger.info(
        "document_sent",
        chat_id=chat_id,
        has_caption=bool(caption),
        has_thumbnail=bool(thumbnail),
        disable_content_type_detection=bool(disable_content_type_detection),
        protect_content=bool(protect_content),
        sent_message_id=getattr(result, "message_id", None),
    )
    return result
