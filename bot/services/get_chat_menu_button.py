from html import escape
from typing import Any

import structlog
from aiogram.exceptions import TelegramAPIError
from aiogram.types import MenuButton

logger = structlog.get_logger()


async def perform_get_chat_menu_button(
    bot: Any,
    *,
    chat_id: int | None = None,
) -> MenuButton:
    """Fetch a chat menu button via the typed aiogram API."""
    try:
        result = await bot.get_chat_menu_button(chat_id=chat_id)
    except TelegramAPIError as exc:
        logger.warning(
            "get_chat_menu_button_failed",
            chat_id=chat_id,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise

    logger.info(
        "get_chat_menu_button_succeeded",
        chat_id=chat_id,
        menu_button_type=getattr(result, "type", None),
    )
    return result


def format_get_chat_menu_button_result(
    menu_button: MenuButton,
    *,
    chat_id: int | None = None,
) -> str:
    """Format a successful ``getChatMenuButton`` result for HTML responses."""
    lines = [
        "<b>getChatMenuButton</b>",
        f"Chat ID: {escape(str(chat_id)) if chat_id is not None else 'default'}",
        f"Type: {escape(str(getattr(menu_button, 'type', 'unknown')))}",
        "Status: chat menu button fetched.",
    ]

    text = getattr(menu_button, "text", None)
    if text:
        lines.append(f"Text: {escape(str(text))}")

    web_app = getattr(menu_button, "web_app", None)
    url = getattr(web_app, "url", None)
    if url:
        lines.append(f"Web App URL: {escape(str(url))}")

    return "\n".join(lines)
