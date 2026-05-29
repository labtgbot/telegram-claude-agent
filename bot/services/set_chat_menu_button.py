from html import escape
from typing import Any

import structlog
from aiogram.exceptions import TelegramAPIError
from aiogram.types import MenuButton

logger = structlog.get_logger()


async def perform_set_chat_menu_button(
    bot: Any,
    *,
    menu_button: MenuButton,
    chat_id: int | None = None,
) -> bool:
    """Set a chat menu button via the typed aiogram API.

    Calls Telegram ``setChatMenuButton`` through ``Bot.set_chat_menu_button()``.
    Without ``chat_id`` Telegram updates the default menu button for all chats.
    """
    try:
        result = await bot.set_chat_menu_button(chat_id=chat_id, menu_button=menu_button)
    except TelegramAPIError as exc:
        logger.warning(
            "set_chat_menu_button_failed",
            chat_id=chat_id,
            menu_button_type=getattr(menu_button, "type", None),
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise

    logger.info(
        "set_chat_menu_button_succeeded",
        chat_id=chat_id,
        menu_button_type=getattr(menu_button, "type", None),
    )
    return result


def format_set_chat_menu_button_result(
    *,
    chat_id: int | None,
    menu_button: MenuButton,
) -> str:
    """Format a successful ``setChatMenuButton`` result for HTML responses."""
    lines = [
        "<b>setChatMenuButton</b>",
        f"Chat ID: {escape(str(chat_id)) if chat_id is not None else 'default'}",
        f"Type: {escape(str(getattr(menu_button, 'type', 'unknown')))}",
        "Status: chat menu button updated.",
    ]

    text = getattr(menu_button, "text", None)
    if text:
        lines.insert(3, f"Text: {escape(str(text))}")

    web_app = getattr(menu_button, "web_app", None)
    url = getattr(web_app, "url", None)
    if url:
        lines.insert(4 if text else 3, f"Web App URL: {escape(str(url))}")

    return "\n".join(lines)
