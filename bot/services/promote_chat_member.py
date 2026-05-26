from html import escape
from typing import Any

import structlog
from aiogram.exceptions import TelegramAPIError
from aiogram.types import ChatAdministratorRights

logger = structlog.get_logger()


async def perform_promote_chat_member(
    bot: Any,
    *,
    chat_id: int,
    user_id: int,
    rights: ChatAdministratorRights,
) -> bool:
    """Promote or demote a chat member via the typed aiogram API.

    Calls the typed aiogram ``Bot.promote_chat_member()`` wrapper for the
    Telegram ``promoteChatMember`` method. The bot must be an administrator in
    the target chat with the ``can_promote_members`` right.
    """
    kwargs = rights.model_dump(exclude_none=True)
    try:
        result = await bot.promote_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            **kwargs,
        )
    except TelegramAPIError as exc:
        logger.warning(
            "promote_chat_member_failed",
            chat_id=chat_id,
            user_id=user_id,
            rights=kwargs,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise

    logger.info(
        "promote_chat_member_succeeded",
        chat_id=chat_id,
        user_id=user_id,
        rights=kwargs,
    )
    return result


def format_promote_result(
    *,
    chat_id: int,
    user_id: int,
    preset: str,
    rights: ChatAdministratorRights,
) -> str:
    """Format a successful promoteChatMember result for HTML responses."""
    lines = [
        "<b>promoteChatMember</b>",
        f"Chat ID: {escape(str(chat_id))}",
        f"User ID: {escape(str(user_id))}",
        f"Preset: {escape(preset)}",
    ]

    enabled = [
        name for name, value in rights.model_dump(exclude_none=True).items() if value is True
    ]
    disabled = [
        name for name, value in rights.model_dump(exclude_none=True).items() if value is False
    ]
    if enabled:
        lines.append(f"Enabled rights: {escape(', '.join(enabled))}")
    if disabled:
        lines.append(f"Disabled rights: {escape(', '.join(disabled))}")

    status = "demoted successfully" if preset == "demote" else "promoted successfully"
    lines.append(f"Status: {status}.")
    return "\n".join(lines)
