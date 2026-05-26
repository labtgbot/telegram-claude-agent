from typing import Any

import structlog
from aiogram.exceptions import TelegramAPIError

logger = structlog.get_logger()

ANSWER_CALLBACK_QUERY_TEXT_LIMIT = 200


class AnswerCallbackQueryError(ValueError):
    """Raised when ``answerCallbackQuery`` input is invalid."""


async def perform_answer_callback_query(
    bot: Any,
    *,
    callback_query_id: str,
    text: str | None = None,
    show_alert: bool | None = None,
    url: str | None = None,
    cache_time: int | None = None,
) -> bool:
    """Answer a Telegram callback query through aiogram's typed Bot API.

    Telegram requires every callback query from an inline keyboard to be
    answered, even when the bot also sends or edits a message. The optional
    text is limited to 200 characters by Telegram Bot API.
    """
    if not callback_query_id:
        raise AnswerCallbackQueryError("callback_query_id is required")
    if text is not None and len(text) > ANSWER_CALLBACK_QUERY_TEXT_LIMIT:
        raise AnswerCallbackQueryError("answerCallbackQuery text is too long")
    if cache_time is not None and cache_time < 0:
        raise AnswerCallbackQueryError("cache_time must be non-negative")

    try:
        result = await bot.answer_callback_query(
            callback_query_id=callback_query_id,
            text=text,
            show_alert=show_alert,
            url=url,
            cache_time=cache_time,
        )
    except TelegramAPIError as exc:
        logger.warning(
            "answer_callback_query_failed",
            callback_query_id=callback_query_id,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise

    logger.info("callback_query_answered", callback_query_id=callback_query_id)
    return result
