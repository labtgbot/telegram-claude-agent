from html import escape
from typing import Any

import structlog
from aiogram.exceptions import TelegramAPIError
from aiogram.types import ChatMember

logger = structlog.get_logger()

MEMBER_RIGHT_FIELDS = (
    "can_be_edited",
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
    "can_send_messages",
    "can_send_audios",
    "can_send_documents",
    "can_send_photos",
    "can_send_videos",
    "can_send_video_notes",
    "can_send_voice_notes",
    "can_send_polls",
    "can_send_other_messages",
    "can_add_web_page_previews",
)


async def perform_get_chat_member(
    bot: Any,
    *,
    chat_id: int,
    user_id: int,
) -> ChatMember:
    """Fetch a chat member via the typed aiogram API.

    Calls the typed aiogram ``Bot.get_chat_member()`` wrapper for the Telegram
    ``getChatMember`` method. The bot must already be able to access the target
    chat; depending on the chat type and privacy settings Telegram may require
    the bot to be a member or administrator.
    """
    try:
        member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
    except TelegramAPIError as exc:
        logger.warning(
            "get_chat_member_failed",
            chat_id=chat_id,
            user_id=user_id,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise

    logger.info(
        "chat_member_fetched",
        chat_id=chat_id,
        user_id=user_id,
        status=getattr(member, "status", None),
    )
    return member


def format_get_chat_member_result(
    chat_id: int,
    user_id: int,
    member: ChatMember,
) -> str:
    """Format ``getChatMember`` result for an HTML admin response."""
    user = getattr(member, "user", None)
    lines = [
        "<b>getChatMember</b>",
        f"Chat ID: {escape(str(chat_id))}",
        f"Requested user ID: {escape(str(user_id))}",
        f"Status: {escape(str(getattr(member, 'status', 'unknown')))}",
        f"User: {_format_user_display_name(user)}",
    ]

    member_user_id = getattr(user, "id", None)
    if member_user_id is not None:
        lines.append(f"User ID: {escape(str(member_user_id))}")

    custom_title = getattr(member, "custom_title", None)
    if custom_title:
        lines.append(f"Title: {escape(str(custom_title))}")

    until_date = getattr(member, "until_date", None)
    if until_date:
        lines.append(f"Until date: {escape(str(until_date))}")

    flags = [
        label
        for field, label in (
            ("is_anonymous", "anonymous"),
            ("is_member", "member"),
        )
        if getattr(member, field, None) is True
    ]
    if flags:
        lines.append(f"Flags: {escape(', '.join(flags))}")

    rights = [
        field
        for field in MEMBER_RIGHT_FIELDS
        if getattr(member, field, None) is True
    ]
    if rights:
        lines.append(f"Rights: {escape(', '.join(rights))}")

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
