from typing import Any

import structlog
from aiogram.exceptions import TelegramAPIError

logger = structlog.get_logger()


async def delete_webhook(bot: Any, drop_pending_updates: bool = False) -> bool:
    try:
        result = await bot.delete_webhook(drop_pending_updates=drop_pending_updates)
    except TelegramAPIError as exc:
        logger.warning(
            "webhook_delete_failed",
            drop_pending_updates=drop_pending_updates,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise

    logger.info(
        "webhook_deleted",
        drop_pending_updates=drop_pending_updates,
        result=bool(result),
    )
    return result
