from datetime import datetime
from typing import Any, Optional

import structlog
from aiogram.exceptions import TelegramAPIError

logger = structlog.get_logger()


class SetUserEmojiStatusError(Exception):
    """Raised when the emoji status cannot be set due to a validation error."""


async def perform_set_user_emoji_status(
    bot: Any,
    *,
    user_id: int,
    emoji_status_custom_emoji_id: Optional[str] = None,
    emoji_status_expiration_date: Optional[datetime] = None,
) -> bool:
    """Set or remove the emoji status for a user via the typed aiogram API.

    Calls the typed aiogram ``Bot.set_user_emoji_status()`` wrapper for the
    Telegram ``setUserEmojiStatus`` method (Bot API 10.0, supported since
    ``aiogram==3.28``).

    The user must have previously granted the bot permission to manage their
    emoji status via the Mini App method ``requestEmojiStatusAccess``.  Without
    this grant Telegram returns a ``Bad Request`` error.

    Bot requirements and limitations:

    * The bot does **not** need to be an administrator.
    * The target user must have explicitly allowed the bot to manage their
      emoji status through a Mini App; without this, the bot cannot set or
      remove the status.
    * Passing an empty string ``""`` for ``emoji_status_custom_emoji_id``
      removes the current emoji status.
    * The ``emoji_status_expiration_date`` is optional; when omitted the
      status persists indefinitely (until the user or bot removes it).
    * The method is unrelated to Telegram Premium subscription of the bot
      itself; it requires the **user's** grant via Mini App.

    Parameters
    ----------
    user_id:
        Unique identifier of the target user whose emoji status should be
        changed.
    emoji_status_custom_emoji_id:
        Custom emoji identifier of the emoji status to set.  Pass an empty
        string ``""`` to remove the user's current emoji status. When
        ``None`` (default) the status is removed as well (Telegram treats
        ``None`` the same as an empty string for this parameter).
    emoji_status_expiration_date:
        Optional expiration date for the emoji status.  When not provided
        the status persists indefinitely.

    Returns
    -------
    bool
        ``True`` on success.

    Raises
    ------
    TelegramAPIError
        Re-raised without modification after logging, so callers can handle it.
    """
    try:
        result = await bot.set_user_emoji_status(
            user_id=user_id,
            emoji_status_custom_emoji_id=emoji_status_custom_emoji_id,
            emoji_status_expiration_date=emoji_status_expiration_date,
        )
    except TelegramAPIError as exc:
        logger.warning(
            "set_user_emoji_status_failed",
            user_id=user_id,
            has_custom_emoji=emoji_status_custom_emoji_id is not None,
            has_expiration=emoji_status_expiration_date is not None,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise

    logger.info(
        "user_emoji_status_set",
        user_id=user_id,
        has_custom_emoji=bool(emoji_status_custom_emoji_id),
        has_expiration=emoji_status_expiration_date is not None,
    )
    return result
