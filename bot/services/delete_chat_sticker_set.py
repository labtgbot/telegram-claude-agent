from html import escape
from typing import Any

import structlog
from aiogram.exceptions import TelegramAPIError

logger = structlog.get_logger()


async def perform_delete_chat_sticker_set(
    bot: Any,
    *,
    chat_id: int,
) -> bool:
    """Delete a supergroup sticker set via the typed aiogram API.

    Calls Telegram ``deleteChatStickerSet`` through
    ``Bot.delete_chat_sticker_set()``. The bot must be an administrator in the
    target supergroup with the right to change chat information.
    """
    try:
        result = await bot.delete_chat_sticker_set(chat_id=chat_id)
    except TelegramAPIError as exc:
        logger.warning(
            "delete_chat_sticker_set_failed",
            chat_id=chat_id,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise

    logger.info("delete_chat_sticker_set_succeeded", chat_id=chat_id)
    return result


def format_delete_chat_sticker_set_result(*, chat_id: int) -> str:
    """Format a successful ``deleteChatStickerSet`` result for HTML responses."""
    return "\n".join(
        [
            "<b>deleteChatStickerSet</b>",
            f"Chat ID: {escape(str(chat_id))}",
            "Status: chat sticker set deleted.",
        ]
    )
