from html import escape
from typing import Any, Sequence

import structlog
from aiogram.exceptions import TelegramAPIError
from aiogram.types import ChatMember

logger = structlog.get_logger()

ADMINISTRATOR_RIGHT_FIELDS = (
    "can_manage_chat",
    "can_delete_messages",
    "can_manage_video_chats",
    "can_restrict_members",
    "can_promote_members",
    "can_change_info",
    "can_invite_users",
    "can_post_messages",
    "can_edit_messages",
    "can_pin_messages",
    "can_post_stories",
    "can_edit_stories",
    "can_delete_stories",
    "can_manage_topics",
)


async def perform_get_chat_administrators(
    bot: Any,
    *,
    chat_id: int,
) -> Sequence[ChatMember]:
    """Fetch chat administrators via the typed aiogram API.

    Calls the typed aiogram ``Bot.get_chat_administrators()`` wrapper for the
    Telegram ``getChatAdministrators`` method. For groups, supergroups and
    channels Telegram requires the bot to access the target chat; in practice
    it should be a chat member and may need administrator rights depending on
    chat type and privacy settings.
    """
    try:
        administrators = await bot.get_chat_administrators(chat_id=chat_id)
    except TelegramAPIError as exc:
        logger.warning(
            "get_chat_administrators_failed",
            chat_id=chat_id,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise

    logger.info(
        "chat_administrators_fetched",
        chat_id=chat_id,
        administrator_count=len(administrators),
    )
    return administrators


def format_get_chat_administrators_result(
    chat_id: int,
    administrators: Sequence[ChatMember],
) -> str:
    """Format ``getChatAdministrators`` result for an HTML admin response."""
    lines = [
        "<b>getChatAdministrators</b>",
        f"Chat ID: {escape(str(chat_id))}",
        f"Administrators: {len(administrators)}",
    ]

    for index, administrator in enumerate(administrators, start=1):
        user = getattr(administrator, "user", None)
        user_id = getattr(user, "id", "unknown")
        display_name = _format_user_display_name(user)
        status = getattr(administrator, "status", "unknown")
        lines.append(
            f"{index}. {display_name} - {escape(str(status))} "
            f"(id: {escape(str(user_id))})"
        )

        custom_title = getattr(administrator, "custom_title", None)
        if custom_title:
            lines.append(f"   Title: {escape(str(custom_title))}")

        if getattr(administrator, "is_anonymous", False):
            lines.append("   Flags: anonymous")

        rights = [
            field
            for field in ADMINISTRATOR_RIGHT_FIELDS
            if getattr(administrator, field, None) is True
        ]
        if rights:
            lines.append(f"   Rights: {escape(', '.join(rights))}")

    return "\n".join(lines)


def _format_user_display_name(user: Any) -> str:
    if user is None:
        return "Unknown user"

    name_parts = [
        getattr(user, "first_name", None),
        getattr(user, "last_name", None),
    ]
    name = " ".join(str(part) for part in name_parts if part) or "Unknown user"

    username = getattr(user, "username", None)
    if username:
        name = f"{name} (@{username})"

    return escape(name)
