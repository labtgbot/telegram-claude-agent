from html import escape
from typing import Any, Sequence

import structlog
from aiogram.exceptions import TelegramAPIError
from aiogram.types import Message

logger = structlog.get_logger()

GET_USER_PERSONAL_CHAT_MESSAGES_MIN_LIMIT = 1
GET_USER_PERSONAL_CHAT_MESSAGES_MAX_LIMIT = 100


async def perform_get_user_personal_chat_messages(
    bot: Any,
    *,
    user_id: int,
    limit: int,
) -> Sequence[Message]:
    """Fetch messages from a user's personal chat via the typed aiogram API.

    Calls the typed aiogram ``Bot.get_user_personal_chat_messages()`` wrapper
    for Telegram ``getUserPersonalChatMessages``. Telegram returns messages
    from the personal chat between the user and the bot; visibility depends on
    Telegram-side privacy and access rules for that user.
    """
    if not (
        GET_USER_PERSONAL_CHAT_MESSAGES_MIN_LIMIT
        <= limit
        <= GET_USER_PERSONAL_CHAT_MESSAGES_MAX_LIMIT
    ):
        raise ValueError(
            "limit must be between "
            f"{GET_USER_PERSONAL_CHAT_MESSAGES_MIN_LIMIT} and "
            f"{GET_USER_PERSONAL_CHAT_MESSAGES_MAX_LIMIT}"
        )

    try:
        messages = await bot.get_user_personal_chat_messages(
            user_id=user_id,
            limit=limit,
        )
    except TelegramAPIError as exc:
        logger.warning(
            "get_user_personal_chat_messages_failed",
            user_id=user_id,
            limit=limit,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise

    logger.info(
        "user_personal_chat_messages_fetched",
        user_id=user_id,
        limit=limit,
        message_count=len(messages),
    )
    return messages


def format_get_user_personal_chat_messages_result(
    *,
    user_id: int,
    limit: int,
    messages: Sequence[Message],
) -> str:
    """Format ``getUserPersonalChatMessages`` for an HTML admin response."""
    lines = [
        "<b>getUserPersonalChatMessages</b>",
        f"User ID: {escape(str(user_id))}",
        f"Requested limit: {escape(str(limit))}",
        f"Messages: {len(messages)}",
    ]

    for index, message in enumerate(messages, start=1):
        message_id = getattr(message, "message_id", "unknown")
        chat = getattr(message, "chat", None)
        chat_id = getattr(chat, "id", "unknown")
        chat_type = getattr(chat, "type", "unknown")
        chat_title = getattr(chat, "title", None)
        date = getattr(message, "date", None)

        line = (
            f"{index}. message_id: {escape(str(message_id))}; "
            f"chat: {escape(str(chat_id))} ({escape(str(chat_type))})"
        )
        if chat_title:
            line += f"; title: {escape(str(chat_title))}"
        if date is not None:
            line += f"; date: {escape(str(date))}"
        lines.append(line)

    return "\n".join(lines)
