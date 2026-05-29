from typing import Any, Optional

import structlog
from aiogram.exceptions import TelegramAPIError

logger = structlog.get_logger()


class SendGameValidationError(ValueError):
    """Raised when ``sendGame`` input is invalid before Telegram is called."""


async def perform_send_game(
    bot: Any,
    *,
    chat_id: int,
    game_short_name: str,
    message_thread_id: Optional[int] = None,
    disable_notification: Optional[bool] = None,
    protect_content: Optional[bool] = None,
) -> Any:
    """Send a Telegram game into a chat via the typed aiogram API.

    Calls the typed aiogram ``Bot.send_game()`` wrapper for Telegram
    ``sendGame``. Telegram requires ``chat_id`` and ``game_short_name``; the
    game must be created for this bot in BotFather before Telegram accepts the
    request. The command layer keeps this operation behind the strict admin
    allowlist and the global rate-limit middleware.
    """
    short_name = game_short_name.strip()
    if not short_name:
        raise SendGameValidationError("game_short_name must be non-empty.")

    try:
        result = await bot.send_game(
            chat_id=chat_id,
            game_short_name=short_name,
            message_thread_id=message_thread_id,
            disable_notification=disable_notification,
            protect_content=protect_content,
        )
    except TelegramAPIError as exc:
        logger.warning(
            "send_game_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            chat_id=chat_id,
            game_short_name=short_name,
        )
        raise

    logger.info(
        "game_sent",
        chat_id=chat_id,
        game_short_name=short_name,
        protect_content=bool(protect_content),
        sent_message_id=getattr(result, "message_id", None),
    )
    return result
