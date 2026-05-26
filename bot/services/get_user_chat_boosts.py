from html import escape
from typing import Any

import structlog
from aiogram.exceptions import TelegramAPIError
from aiogram.types import UserChatBoosts

logger = structlog.get_logger()


async def perform_get_user_chat_boosts(
    bot: Any,
    *,
    chat_id: int | str,
    user_id: int,
) -> UserChatBoosts:
    """Fetch boosts added by a user to a chat via the typed aiogram API.

    Calls the typed aiogram ``Bot.get_user_chat_boosts()`` wrapper for
    Telegram ``getUserChatBoosts``. The bot must be an administrator in the
    target chat; Telegram only returns boosts that were added by the requested
    user.
    """
    try:
        boosts = await bot.get_user_chat_boosts(chat_id=chat_id, user_id=user_id)
    except TelegramAPIError as exc:
        logger.warning(
            "get_user_chat_boosts_failed",
            chat_id=chat_id,
            user_id=user_id,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise

    logger.info(
        "user_chat_boosts_fetched",
        chat_id=chat_id,
        user_id=user_id,
        boost_count=len(getattr(boosts, "boosts", [])),
    )
    return boosts


def format_get_user_chat_boosts_result(
    *,
    chat_id: int | str,
    user_id: int,
    boosts: UserChatBoosts,
) -> str:
    """Format ``getUserChatBoosts`` for an HTML admin response."""
    boost_items = getattr(boosts, "boosts", [])
    lines = [
        "<b>getUserChatBoosts</b>",
        f"Chat ID: {escape(str(chat_id))}",
        f"Requested user ID: {escape(str(user_id))}",
        f"Boosts: {len(boost_items)}",
    ]

    for index, boost in enumerate(boost_items, start=1):
        source = getattr(boost, "source", None)
        source_type = getattr(source, "source", "unknown")
        boost_id = getattr(boost, "boost_id", "unknown")
        add_date = getattr(boost, "add_date", None)
        expiration_date = getattr(boost, "expiration_date", None)

        line = (
            f"{index}. boost_id: {escape(str(boost_id))}; "
            f"source: {escape(str(source_type))}"
        )
        if add_date is not None:
            line += f"; add_date: {escape(str(add_date))}"
        if expiration_date is not None:
            line += f"; expiration_date: {escape(str(expiration_date))}"
        lines.append(line)

    return "\n".join(lines)
