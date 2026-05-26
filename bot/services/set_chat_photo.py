from html import escape
from typing import Any

import structlog
from aiogram.exceptions import TelegramAPIError
from aiogram.types import FSInputFile

logger = structlog.get_logger()


async def perform_set_chat_photo(
    bot: Any,
    *,
    chat_id: int,
    photo_path: str,
) -> bool:
    """Set a chat photo via the typed aiogram API.

    Calls Telegram ``setChatPhoto`` through ``Bot.set_chat_photo()``. Telegram
    requires a freshly uploaded image file, so this helper accepts a local file
    path and wraps it in ``FSInputFile``. The bot must be an administrator in
    the target group or supergroup with the right to change chat information.
    No special update subscription is needed for the command-driven scenario.
    """
    photo = FSInputFile(photo_path)

    try:
        result = await bot.set_chat_photo(chat_id=chat_id, photo=photo)
    except TelegramAPIError as exc:
        logger.warning(
            "set_chat_photo_failed",
            chat_id=chat_id,
            photo_path=photo_path,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise

    logger.info(
        "set_chat_photo_succeeded",
        chat_id=chat_id,
        photo_path=photo_path,
    )
    return result


def format_set_chat_photo_result(*, chat_id: int, photo_path: str) -> str:
    """Format a successful ``setChatPhoto`` result for HTML responses."""
    return "\n".join(
        [
            "<b>setChatPhoto</b>",
            f"Chat ID: {escape(str(chat_id))}",
            f"Photo: {escape(photo_path)}",
            "Status: chat photo updated.",
        ]
    )
