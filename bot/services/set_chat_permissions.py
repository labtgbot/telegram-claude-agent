from html import escape
from typing import Any, Optional

import structlog
from aiogram.exceptions import TelegramAPIError
from aiogram.types import ChatPermissions

logger = structlog.get_logger()


async def perform_set_chat_permissions(
    bot: Any,
    *,
    chat_id: int,
    permissions: ChatPermissions,
    use_independent_chat_permissions: Optional[bool] = None,
) -> bool:
    """Set default chat permissions via the typed aiogram API.

    Calls Telegram ``setChatPermissions`` through ``Bot.set_chat_permissions()``.
    The bot must be an administrator in the target group or supergroup with the
    ``can_restrict_members`` right.
    """
    try:
        result = await bot.set_chat_permissions(
            chat_id=chat_id,
            permissions=permissions,
            use_independent_chat_permissions=use_independent_chat_permissions,
        )
    except TelegramAPIError as exc:
        logger.warning(
            "set_chat_permissions_failed",
            chat_id=chat_id,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise

    logger.info(
        "set_chat_permissions_succeeded",
        chat_id=chat_id,
        use_independent_chat_permissions=use_independent_chat_permissions,
    )
    return result


def format_set_chat_permissions_result(
    *,
    chat_id: int,
    preset: str,
    permissions: ChatPermissions,
    use_independent_chat_permissions: Optional[bool],
) -> str:
    """Format a successful setChatPermissions result for HTML responses."""
    lines = [
        "<b>setChatPermissions</b>",
        f"Chat ID: {escape(str(chat_id))}",
        f"Preset: {escape(preset)}",
    ]

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
        lines.append(f"Allowed by default: {escape(', '.join(allowed))}")
    if denied:
        lines.append(f"Denied by default: {escape(', '.join(denied))}")

    lines.append("Status: default chat permissions updated.")
    return "\n".join(lines)
