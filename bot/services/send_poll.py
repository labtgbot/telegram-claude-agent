from typing import Any, List, Optional

import structlog
from aiogram.exceptions import TelegramAPIError

logger = structlog.get_logger()


async def perform_send_poll(
    bot: Any,
    *,
    chat_id: int,
    question: str,
    options: List[str],
    is_anonymous: Optional[bool] = None,
    type: Optional[str] = None,
    allows_multiple_answers: Optional[bool] = None,
    correct_option_id: Optional[int] = None,
    explanation: Optional[str] = None,
    open_period: Optional[int] = None,
    close_date: Optional[Any] = None,
    is_closed: Optional[bool] = None,
    message_thread_id: Optional[int] = None,
    disable_notification: Optional[bool] = None,
    protect_content: Optional[bool] = None,
) -> Any:
    """Send a native poll into a chat via the typed aiogram API.

    Calls the typed aiogram ``Bot.send_poll()`` wrapper for the Telegram
    ``sendPoll`` method so the bot can deliver an interactive native poll
    instead of only a textual interpretation. The Telegram method requires
    ``chat_id``, the ``question`` (1-300 characters) and the ``options`` (2-10
    answer strings, 1-100 characters each) and returns the sent ``Message`` on
    success. By default a poll is anonymous and of ``type`` ``regular``; pass
    ``type="quiz"`` together with ``correct_option_id`` (and optionally an
    ``explanation``) to send a quiz-style poll. ``open_period`` (5-600 seconds)
    or ``close_date`` schedule automatic closing, and ``is_closed`` sends an
    already-closed poll for preview. The parameters passed here are the ones
    available in the pinned ``aiogram==3.3.0`` (Bot API 7.0) typed wrapper.

    The poll question and the answer options are content the operator chose to
    broadcast, so they are intentionally kept out of the structured logs; only
    the number of options, whether the poll is a quiz and the sent message id
    are logged.
    """
    try:
        result = await bot.send_poll(
            chat_id=chat_id,
            question=question,
            options=options,
            is_anonymous=is_anonymous,
            type=type,
            allows_multiple_answers=allows_multiple_answers,
            correct_option_id=correct_option_id,
            explanation=explanation,
            open_period=open_period,
            close_date=close_date,
            is_closed=is_closed,
            message_thread_id=message_thread_id,
            disable_notification=disable_notification,
            protect_content=protect_content,
        )
    except TelegramAPIError as exc:
        logger.warning(
            "send_poll_failed",
            # ``type`` is a poll parameter here, so reach the exception class
            # through ``__class__`` instead of the shadowed ``type`` builtin.
            error_type=exc.__class__.__name__,
            error=str(exc),
            chat_id=chat_id,
        )
        raise

    logger.info(
        "poll_sent",
        chat_id=chat_id,
        option_count=len(options),
        is_quiz=type == "quiz",
        protect_content=bool(protect_content),
        sent_message_id=getattr(result, "message_id", None),
    )
    return result
