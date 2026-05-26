from html import escape
from typing import Any

import structlog
from aiogram.exceptions import TelegramAPIError
from aiogram.types import Chat

logger = structlog.get_logger()


async def perform_get_chat(
    bot: Any,
    *,
    chat_id: int,
) -> Chat:
    """Fetch chat information via the typed aiogram API.

    Calls the typed aiogram ``Bot.get_chat()`` wrapper for the Telegram
    ``getChat`` method. The bot must already be able to access the target chat:
    for groups, supergroups and channels this usually means the bot is a member
    of the chat.
    """
    try:
        chat = await bot.get_chat(chat_id=chat_id)
    except TelegramAPIError as exc:
        logger.warning(
            "get_chat_failed",
            chat_id=chat_id,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise

    logger.info(
        "chat_fetched",
        chat_id=chat_id,
        resolved_chat_id=getattr(chat, "id", None),
        chat_type=getattr(chat, "type", None),
    )
    return chat


def format_get_chat_result(chat: Chat) -> str:
    """Format ``getChat`` result for a concise HTML admin response."""
    lines = [
        "<b>getChat</b>",
        f"Chat ID: {escape(str(chat.id))}",
        f"Type: {escape(str(chat.type))}",
    ]

    optional_fields = [
        ("Title", "title"),
        ("Username", "username"),
        ("First name", "first_name"),
        ("Last name", "last_name"),
        ("Bio", "bio"),
        ("Description", "description"),
        ("Invite link", "invite_link"),
    ]
    for label, attr in optional_fields:
        value = getattr(chat, attr, None)
        if value is None:
            continue
        if attr == "username":
            value = f"@{value}"
        lines.append(f"{label}: {escape(str(value))}")

    for label, attr in [
        ("Is forum", "is_forum"),
        ("Has protected content", "has_protected_content"),
        ("Linked chat ID", "linked_chat_id"),
        ("Message auto-delete time", "message_auto_delete_time"),
        ("Slow mode delay", "slow_mode_delay"),
    ]:
        value = getattr(chat, attr, None)
        if value is not None:
            lines.append(f"{label}: {escape(str(value))}")

    return "\n".join(lines)
