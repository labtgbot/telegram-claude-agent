from datetime import datetime
from html import escape
from typing import Any, Optional

import structlog
from aiogram.exceptions import TelegramAPIError

logger = structlog.get_logger()


async def perform_ban_chat_member(
    bot: Any,
    *,
    chat_id: int,
    user_id: int,
    until_date: Optional[datetime] = None,
    revoke_messages: Optional[bool] = None,
) -> bool:
    """Ban a user from a chat via the typed aiogram API.

    Calls the typed aiogram ``Bot.ban_chat_member()`` wrapper for the
    Telegram ``banChatMember`` method. The bot must be an administrator in the
    chat with the ``can_restrict_members`` right.

    Parameters
    ----------
    chat_id:
        Unique identifier for the target chat. The bot must be an
        administrator with ``can_restrict_members`` in that chat.
    user_id:
        Unique identifier of the target user to be banned.
    until_date:
        Date when the user will be automatically unbanned. Telegram ignores
        this if it is less than 30 seconds or more than 366 days in the
        future; in those cases the ban is permanent. Use ``None`` for a
        permanent ban.
    revoke_messages:
        Pass ``True`` to delete all messages from the chat for the user that
        is being removed. If ``False``, the user will be able to see messages
        in the group that were sent before the user was removed.
        Always ``True`` for supergroups and channels.

    Returns
    -------
    bool
        ``True`` on success, as returned by the Telegram Bot API.

    Raises
    ------
    TelegramAPIError
        Re-raised without modification after logging, so callers can handle it.
    """
    try:
        result = await bot.ban_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            until_date=until_date,
            revoke_messages=revoke_messages,
        )
    except TelegramAPIError as exc:
        logger.warning(
            "ban_chat_member_failed",
            chat_id=chat_id,
            user_id=user_id,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise

    logger.info(
        "ban_chat_member_succeeded",
        chat_id=chat_id,
        user_id=user_id,
        until_date=until_date.isoformat() if until_date else None,
        revoke_messages=revoke_messages,
    )
    return result


def format_ban_result(
    chat_id: int,
    user_id: int,
    until_date: Optional[datetime],
    revoke_messages: Optional[bool],
) -> str:
    """Format a successful banChatMember result into a human-readable HTML string.

    The result is safe for ``parse_mode="HTML"`` because all user-controlled
    values are escaped through ``html.escape``.
    """
    lines = [
        "<b>banChatMember</b>",
        f"Chat ID: {escape(str(chat_id))}",
        f"User ID: {escape(str(user_id))}",
    ]

    if until_date is None:
        lines.append("Ban type: permanent")
    else:
        lines.append(f"Banned until: {escape(until_date.strftime('%Y-%m-%d %H:%M:%S UTC'))}")

    if revoke_messages is True:
        lines.append("Messages revoked: yes")
    elif revoke_messages is False:
        lines.append("Messages revoked: no")

    lines.append("Status: banned successfully.")
    return "\n".join(lines)
