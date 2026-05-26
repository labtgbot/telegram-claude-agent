from html import escape
from typing import Any

import structlog
from aiogram.exceptions import TelegramAPIError

logger = structlog.get_logger()


async def perform_set_chat_member_tag(
    bot: Any,
    *,
    chat_id: int,
    user_id: int,
    tag: str | None,
) -> bool:
    """Set or clear a chat member tag via the typed aiogram API."""
    try:
        result = await bot.set_chat_member_tag(
            chat_id=chat_id,
            user_id=user_id,
            tag=tag,
        )
    except TelegramAPIError as exc:
        logger.warning(
            "set_chat_member_tag_failed",
            chat_id=chat_id,
            user_id=user_id,
            tag=tag,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise

    logger.info(
        "set_chat_member_tag_succeeded",
        chat_id=chat_id,
        user_id=user_id,
        tag=tag,
    )
    return result


def format_set_chat_member_tag_result(
    *,
    chat_id: int,
    user_id: int,
    tag: str | None,
) -> str:
    """Format a successful setChatMemberTag result for HTML responses."""
    tag_line = "Tag: cleared" if tag is None else f"Tag: {escape(tag)}"
    status = "cleared" if tag is None else "updated"
    return "\n".join(
        [
            "<b>setChatMemberTag</b>",
            f"Chat ID: {escape(str(chat_id))}",
            f"User ID: {escape(str(user_id))}",
            tag_line,
            f"Status: member tag {status} successfully.",
        ]
    )
