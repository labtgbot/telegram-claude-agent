from typing import Any, Optional

import structlog
from aiogram.exceptions import TelegramAPIError

logger = structlog.get_logger()


async def perform_send_dice(
    bot: Any,
    *,
    chat_id: int,
    emoji: Optional[str] = None,
    message_thread_id: Optional[int] = None,
    disable_notification: Optional[bool] = None,
    protect_content: Optional[bool] = None,
) -> Any:
    """Send an animated dice into a chat via the typed aiogram API.

    Calls the typed aiogram ``Bot.send_dice()`` wrapper for the Telegram
    ``sendDice`` method so the bot can deliver an animated emoji that shows a
    random value (a real Telegram dice) instead of only a textual
    interpretation. The Telegram method requires only ``chat_id`` and returns
    the sent ``Message`` on success; the rolled value is chosen by Telegram and
    exposed on the returned ``Message.dice``. ``emoji`` selects the animation
    and must be one of ``🎲``, ``🎯``, ``🏀``, ``⚽``, ``🎳`` or ``🎰`` (the
    value range depends on the emoji: 1-6 for ``🎲``, ``🎯`` and ``🎳``, 1-5
    for ``🏀`` and ``⚽`` and 1-64 for ``🎰``); when omitted Telegram defaults
    to ``🎲``. The parameters passed here are the ones available in the pinned
    ``aiogram==3.3.0`` (Bot API 7.0) typed wrapper.

    The dice carries no operator-provided content, so the chosen emoji, whether
    the delivery is silent and the sent message id are logged.
    """
    try:
        result = await bot.send_dice(
            chat_id=chat_id,
            emoji=emoji,
            message_thread_id=message_thread_id,
            disable_notification=disable_notification,
            protect_content=protect_content,
        )
    except TelegramAPIError as exc:
        logger.warning(
            "send_dice_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            chat_id=chat_id,
        )
        raise

    logger.info(
        "dice_sent",
        chat_id=chat_id,
        emoji=emoji,
        protect_content=bool(protect_content),
        sent_message_id=getattr(result, "message_id", None),
    )
    return result
