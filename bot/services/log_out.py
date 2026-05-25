from typing import Any

import structlog
from aiogram.exceptions import TelegramAPIError

logger = structlog.get_logger()


async def perform_log_out(bot: Any) -> bool:
    """Log the bot out of the cloud Telegram Bot API server.

    Calls the typed aiogram ``Bot.log_out()`` wrapper for the Telegram
    ``logOut`` method. The method takes no parameters and returns ``True`` on
    success. After a successful call the bot stops receiving updates from the
    cloud Bot API server and cannot log back into it for 10 minutes, so this is
    a destructive lifecycle operation that callers must guard explicitly.
    """
    try:
        result = await bot.log_out()
    except TelegramAPIError as exc:
        logger.warning(
            "bot_log_out_failed",
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise

    logger.info("bot_logged_out", result=result)
    return result
