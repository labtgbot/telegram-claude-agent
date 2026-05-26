from html import escape
from typing import Any

import structlog
from aiogram.exceptions import TelegramAPIError

logger = structlog.get_logger()


async def perform_set_chat_sticker_set(
    bot: Any,
    *,
    chat_id: int,
    sticker_set_name: str,
) -> bool:
    """Set a supergroup sticker set via the typed aiogram API.

    Calls Telegram ``setChatStickerSet`` through ``Bot.set_chat_sticker_set()``.
    The bot must be an administrator in the target supergroup with the right to
    change chat information.
    """
    try:
        result = await bot.set_chat_sticker_set(
            chat_id=chat_id,
            sticker_set_name=sticker_set_name,
        )
    except TelegramAPIError as exc:
        logger.warning(
            "set_chat_sticker_set_failed",
            chat_id=chat_id,
            sticker_set_name=sticker_set_name,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise

    logger.info(
        "set_chat_sticker_set_succeeded",
        chat_id=chat_id,
        sticker_set_name=sticker_set_name,
    )
    return result


def format_set_chat_sticker_set_result(*, chat_id: int, sticker_set_name: str) -> str:
    """Format a successful ``setChatStickerSet`` result for HTML responses."""
    return "\n".join(
        [
            "<b>setChatStickerSet</b>",
            f"Chat ID: {escape(str(chat_id))}",
            f"Sticker set: {escape(sticker_set_name)}",
            "Status: chat sticker set updated.",
        ]
    )
