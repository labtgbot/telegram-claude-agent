from typing import Any, Optional

import structlog
from aiogram.exceptions import TelegramAPIError

logger = structlog.get_logger()


class SetGameScoreValidationError(ValueError):
    """Raised when ``setGameScore`` input is invalid before Telegram is called."""


async def perform_set_game_score(
    bot: Any,
    *,
    user_id: int,
    score: int,
    chat_id: Optional[int] = None,
    message_id: Optional[int] = None,
    inline_message_id: Optional[str] = None,
    force: Optional[bool] = None,
    disable_edit_message: Optional[bool] = None,
) -> Any:
    """Set a Telegram game score via the typed aiogram API.

    Calls the typed aiogram ``Bot.set_game_score()`` wrapper for Telegram
    ``setGameScore``. Telegram requires ``user_id`` and a non-negative ``score``.
    The target game message is identified either by ``chat_id`` plus
    ``message_id`` for a normal chat message or by ``inline_message_id`` for an
    inline game message. The command layer keeps this operation behind the
    strict admin allowlist and the global rate-limit middleware.
    """
    if score < 0:
        raise SetGameScoreValidationError("score must be non-negative.")

    inline_id = inline_message_id.strip() if inline_message_id is not None else None
    if inline_id == "":
        raise SetGameScoreValidationError("inline_message_id must be non-empty.")

    has_chat_message = chat_id is not None or message_id is not None
    has_inline_message = inline_id is not None
    if has_chat_message == has_inline_message:
        raise SetGameScoreValidationError(
            "Provide either chat_id and message_id, or inline_message_id."
        )
    if has_chat_message and (chat_id is None or message_id is None):
        raise SetGameScoreValidationError("chat_id and message_id must be provided together.")

    try:
        result = await bot.set_game_score(
            user_id=user_id,
            score=score,
            force=force,
            disable_edit_message=disable_edit_message,
            chat_id=chat_id,
            message_id=message_id,
            inline_message_id=inline_id,
        )
    except TelegramAPIError as exc:
        logger.warning(
            "set_game_score_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            user_id=user_id,
            score=score,
            chat_id=chat_id,
            message_id=message_id,
            has_inline_message_id=inline_id is not None,
        )
        raise

    logger.info(
        "game_score_set",
        user_id=user_id,
        score=score,
        chat_id=chat_id,
        message_id=message_id,
        has_inline_message_id=inline_id is not None,
        force=bool(force),
        disable_edit_message=bool(disable_edit_message),
    )
    return result
