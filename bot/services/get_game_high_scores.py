from typing import Any, Optional

import structlog
from aiogram.exceptions import TelegramAPIError

logger = structlog.get_logger()


class GetGameHighScoresValidationError(ValueError):
    """Raised when ``getGameHighScores`` input is invalid before Telegram is called."""


async def perform_get_game_high_scores(
    bot: Any,
    *,
    user_id: int,
    chat_id: Optional[int] = None,
    message_id: Optional[int] = None,
    inline_message_id: Optional[str] = None,
) -> Any:
    """Fetch Telegram game high scores via the typed aiogram API.

    Calls the typed aiogram ``Bot.get_game_high_scores()`` wrapper for Telegram
    ``getGameHighScores``. Telegram requires the user id and exactly one game
    target: ``chat_id`` plus ``message_id`` for a normal game message, or
    ``inline_message_id`` for an inline game message. The command layer keeps
    this operation behind the strict admin allowlist and the global rate-limit
    middleware.
    """
    if user_id <= 0:
        raise GetGameHighScoresValidationError("user_id must be a positive integer.")

    inline_id = inline_message_id.strip() if inline_message_id is not None else None
    if inline_id == "":
        raise GetGameHighScoresValidationError("inline_message_id must be non-empty.")

    has_chat_message = chat_id is not None or message_id is not None
    has_inline_message = inline_id is not None
    if has_chat_message == has_inline_message:
        raise GetGameHighScoresValidationError(
            "Provide either chat_id and message_id, or inline_message_id."
        )
    if has_chat_message and (chat_id is None or message_id is None):
        raise GetGameHighScoresValidationError(
            "chat_id and message_id must be provided together."
        )

    try:
        result = await bot.get_game_high_scores(
            user_id=user_id,
            chat_id=chat_id,
            message_id=message_id,
            inline_message_id=inline_id,
        )
    except TelegramAPIError as exc:
        logger.warning(
            "get_game_high_scores_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            user_id=user_id,
            chat_id=chat_id,
            message_id=message_id,
            has_inline_message_id=inline_id is not None,
        )
        raise

    logger.info(
        "game_high_scores_fetched",
        user_id=user_id,
        chat_id=chat_id,
        message_id=message_id,
        has_inline_message_id=inline_id is not None,
        score_count=len(result) if hasattr(result, "__len__") else None,
    )
    return result
