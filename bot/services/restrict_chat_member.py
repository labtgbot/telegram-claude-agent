from datetime import datetime
from html import escape
from typing import Any, Optional

import structlog
from aiogram.exceptions import TelegramAPIError
from aiogram.types import ChatPermissions

logger = structlog.get_logger()


async def perform_restrict_chat_member(
    bot: Any,
    *,
    chat_id: int,
    user_id: int,
    permissions: ChatPermissions,
    until_date: Optional[datetime] = None,
    use_independent_chat_permissions: Optional[bool] = None,
) -> bool:
    """Restrict a chat member via the typed aiogram API.

    Calls the typed aiogram ``Bot.restrict_chat_member()`` wrapper for the
    Telegram ``restrictChatMember`` method. The bot must be an administrator
    in the target chat with the ``can_restrict_members`` right.
    """
    try:
        result = await bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            permissions=permissions,
            until_date=until_date,
            use_independent_chat_permissions=use_independent_chat_permissions,
        )
    except TelegramAPIError as exc:
        logger.warning(
            "restrict_chat_member_failed",
            chat_id=chat_id,
            user_id=user_id,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise

    logger.info(
        "restrict_chat_member_succeeded",
        chat_id=chat_id,
        user_id=user_id,
        until_date=until_date.isoformat() if until_date else None,
        use_independent_chat_permissions=use_independent_chat_permissions,
    )
    return result


def format_restrict_result(
    *,
    chat_id: int,
    user_id: int,
    preset: str,
    permissions: ChatPermissions,
    until_date: Optional[datetime],
    use_independent_chat_permissions: Optional[bool],
) -> str:
    """Format a successful restrictChatMember result for HTML responses."""
    lines = [
        "<b>restrictChatMember</b>",
        f"Chat ID: {escape(str(chat_id))}",
        f"User ID: {escape(str(user_id))}",
        f"Preset: {escape(preset)}",
    ]

    if until_date is None:
        lines.append("Restriction type: permanent")
    else:
        lines.append(
            f"Restricted until: {escape(until_date.strftime('%Y-%m-%d %H:%M:%S UTC'))}"
        )

    if use_independent_chat_permissions is True:
        lines.append("Independent permissions: yes")
    elif use_independent_chat_permissions is False:
        lines.append("Independent permissions: no")

    allowed = [
        name
        for name, value in permissions.model_dump(exclude_none=True).items()
        if value is True
    ]
    denied = [
        name
        for name, value in permissions.model_dump(exclude_none=True).items()
        if value is False
    ]
    if allowed:
        lines.append(f"Allowed: {escape(', '.join(allowed))}")
    if denied:
        lines.append(f"Denied: {escape(', '.join(denied))}")

    lines.append("Status: restricted successfully.")
    return "\n".join(lines)
