from html import escape
from typing import Any

import structlog
from aiogram.exceptions import TelegramAPIError

logger = structlog.get_logger()


async def perform_export_chat_invite_link(
    bot: Any,
    *,
    chat_id: int,
) -> str:
    """Export a new primary invite link via the typed aiogram API.

    Calls the typed aiogram ``Bot.export_chat_invite_link()`` wrapper for the
    Telegram ``exportChatInviteLink`` method. Telegram revokes the previously
    generated primary invite link, and the bot must be an administrator in the
    target chat with the ``can_invite_users`` right.
    """
    try:
        invite_link = await bot.export_chat_invite_link(chat_id=chat_id)
    except TelegramAPIError as exc:
        logger.warning(
            "export_chat_invite_link_failed",
            chat_id=chat_id,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise

    logger.info(
        "export_chat_invite_link_succeeded",
        chat_id=chat_id,
    )
    return invite_link


def format_export_chat_invite_link_result(
    *,
    chat_id: int,
    invite_link: str,
) -> str:
    """Format a successful exportChatInviteLink result for HTML responses."""
    return "\n".join(
        [
            "<b>exportChatInviteLink</b>",
            f"Chat ID: {escape(str(chat_id))}",
            f"Invite link: {escape(invite_link)}",
            "Status: new primary invite link exported successfully; the "
            "previous primary invite link is revoked.",
        ]
    )
