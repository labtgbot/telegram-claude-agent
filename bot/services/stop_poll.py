from typing import Any, Optional

import structlog
from aiogram.exceptions import TelegramAPIError
from aiogram.types import Poll

logger = structlog.get_logger()


class StopPollValidationError(ValueError):
    """Raised when ``stopPoll`` input is invalid before Telegram call."""


async def perform_stop_poll(
    bot: Any,
    *,
    chat_id: int | str,
    message_id: int,
    reply_markup: Optional[Any] = None,
) -> Poll:
    """Stop an active poll through aiogram's typed ``Bot.stop_poll()`` wrapper."""
    if isinstance(chat_id, str) and not chat_id.strip():
        raise StopPollValidationError("chat_id must be provided.")
    if message_id <= 0:
        raise StopPollValidationError("message_id must be positive.")

    try:
        result = await bot.stop_poll(
            chat_id=chat_id,
            message_id=message_id,
            reply_markup=reply_markup,
        )
    except TelegramAPIError as exc:
        logger.warning(
            "stop_poll_failed",
            error_type=exc.__class__.__name__,
            error=str(exc),
            chat_id=chat_id,
            message_id=message_id,
        )
        raise

    logger.info(
        "poll_stopped",
        chat_id=chat_id,
        message_id=message_id,
        poll_id=getattr(result, "id", None),
        option_count=len(getattr(result, "options", []) or []),
    )
    return result


def format_stop_poll_result(poll: Poll, *, chat_id: int | str, message_id: int) -> str:
    total_voter_count = getattr(poll, "total_voter_count", None)
    voter_text = (
        f"\nTotal voters: <code>{total_voter_count}</code>"
        if total_voter_count is not None
        else ""
    )
    return (
        "Stopped poll with <code>stopPoll</code>.\n"
        f"Chat: <code>{chat_id}</code>\n"
        f"Message: <code>{message_id}</code>"
        f"{voter_text}"
    )
