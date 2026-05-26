from html import escape
from typing import Any, Optional

import structlog
from aiogram.exceptions import TelegramAPIError
from aiogram.types import UserProfileAudios

logger = structlog.get_logger()

# Telegram limits: 1-100 audios per page, default is 100.
GET_USER_PROFILE_AUDIOS_MAX_LIMIT = 100
GET_USER_PROFILE_AUDIOS_MIN_LIMIT = 1


async def fetch_user_profile_audios(
    bot: Any,
    *,
    user_id: int,
    offset: Optional[int] = None,
    limit: Optional[int] = None,
) -> UserProfileAudios:
    """Fetch profile audios of a user via the typed aiogram API.

    Calls the typed aiogram ``Bot.get_user_profile_audios()`` wrapper for the
    Telegram ``getUserProfileAudios`` method (Bot API 9.4). The bot does not
    require any special permissions to call this method — it is available in
    any context where the bot can interact with the user (private chat, shared
    group, etc.).

    Parameters
    ----------
    user_id:
        Unique identifier of the target user. Telegram returns an error when
        the user has restricted their privacy settings so that their profile
        audios are not visible.
    offset:
        Sequential number of the first audio to be returned. By default, all
        audios are returned from the beginning (offset 0).
    limit:
        Limits the number of audios to be retrieved. Values outside the
        1-100 range are rejected by Telegram. Defaults to 100.

    Returns
    -------
    UserProfileAudios
        Object containing ``total_count`` (total number of profile audios) and
        ``audios`` (a list of ``Audio`` objects).

    Raises
    ------
    TelegramAPIError
        Re-raised without modification after logging, so callers can handle it.
    """
    try:
        result = await bot.get_user_profile_audios(
            user_id=user_id,
            offset=offset,
            limit=limit,
        )
    except TelegramAPIError as exc:
        logger.warning(
            "get_user_profile_audios_failed",
            user_id=user_id,
            offset=offset,
            limit=limit,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise

    logger.info(
        "user_profile_audios_fetched",
        user_id=user_id,
        total_count=result.total_count,
        returned_count=len(result.audios),
        offset=offset,
        limit=limit,
    )
    return result


def format_user_profile_audios(result: UserProfileAudios, user_id: int) -> str:
    """Format ``UserProfileAudios`` into a human-readable HTML string.

    The result is safe for ``parse_mode="HTML"`` because all user-controlled
    values are escaped through ``html.escape``.
    """
    total = result.total_count
    audios = result.audios

    if total == 0 or not audios:
        return (
            f"<b>User profile audios</b>\n"
            f"User ID: {escape(str(user_id))}\n"
            "No profile audios found."
        )

    lines = [
        "<b>User profile audios</b>",
        f"User ID: {escape(str(user_id))}",
        f"Total audios: {total}",
        f"Returned in this batch: {len(audios)}",
    ]

    for i, audio in enumerate(audios, start=1):
        parts = [f"Audio {i}: file_id={escape(audio.file_id)}"]
        parts.append(f"duration={audio.duration}s")
        if audio.performer is not None:
            parts.append(f"performer={escape(audio.performer)}")
        if audio.title is not None:
            parts.append(f"title={escape(audio.title)}")
        if audio.file_name is not None:
            parts.append(f"file_name={escape(audio.file_name)}")
        lines.append(" ".join(parts))

    return "\n".join(lines)
