from typing import Any

import structlog
from aiogram.exceptions import TelegramAPIError

logger = structlog.get_logger()


async def perform_close(bot: Any) -> bool:
    """Close the bot instance on the current Bot API server.

    Calls the typed aiogram ``Bot.close()`` wrapper for the Telegram ``close``
    method. The method takes no parameters and returns ``True`` on success.
    It is used to close the running bot instance before moving it from one
    local Bot API server to another. The webhook must be deleted beforehand so
    the bot is not relaunched after a server restart, and Telegram returns
    error 429 if it is called within the first 10 minutes after the bot was
    launched. This is a destructive lifecycle operation that callers must guard
    explicitly.
    """
    try:
        result = await bot.close()
    except TelegramAPIError as exc:
        logger.warning(
            "bot_close_failed",
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise

    logger.info("bot_closed", result=result)
    return result
