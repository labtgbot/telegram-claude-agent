from html import escape
from typing import Any, Optional

import structlog
from aiogram.exceptions import TelegramAPIError
from aiogram.types import UserProfilePhotos

logger = structlog.get_logger()

# Telegram limits: 1-100 photos per page, default is 100.
GET_USER_PROFILE_PHOTOS_MAX_LIMIT = 100
GET_USER_PROFILE_PHOTOS_MIN_LIMIT = 1


async def fetch_user_profile_photos(
    bot: Any,
    *,
    user_id: int,
    offset: Optional[int] = None,
    limit: Optional[int] = None,
) -> UserProfilePhotos:
    """Fetch profile photos of a user via the typed aiogram API.

    Calls the typed aiogram ``Bot.get_user_profile_photos()`` wrapper for the
    Telegram ``getUserProfilePhotos`` method. The bot does not require any
    special permissions to call this method — it is available in any context
    where the bot can interact with the user (private chat, shared group, etc.).

    Parameters
    ----------
    user_id:
        Unique identifier of the target user. There is no restriction on whose
        photos can be fetched; however, Telegram returns an error when the user
        has restricted their privacy settings so that their profile photos are
        not visible.
    offset:
        Sequential number of the first photo to be returned.  By default, all
        photos are returned from the beginning (offset 0).
    limit:
        Limits the number of photos to be retrieved. Values outside the
        1-100 range are rejected by Telegram. Defaults to 100.

    Returns
    -------
    UserProfilePhotos
        Object containing ``total_count`` (total number of profile photos) and
        ``photos`` (a list of photo sets, each being a list of ``PhotoSize``
        objects in different resolutions).

    Raises
    ------
    TelegramAPIError
        Re-raised without modification after logging, so callers can handle it.
    """
    try:
        result = await bot.get_user_profile_photos(
            user_id=user_id,
            offset=offset,
            limit=limit,
        )
    except TelegramAPIError as exc:
        logger.warning(
            "get_user_profile_photos_failed",
            user_id=user_id,
            offset=offset,
            limit=limit,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise

    logger.info(
        "user_profile_photos_fetched",
        user_id=user_id,
        total_count=result.total_count,
        returned_count=len(result.photos),
        offset=offset,
        limit=limit,
    )
    return result


def format_user_profile_photos(result: UserProfilePhotos, user_id: int) -> str:
    """Format ``UserProfilePhotos`` into a human-readable HTML string.

    The result is safe for ``parse_mode="HTML"`` because all user-controlled
    values are escaped through ``html.escape``.
    """
    total = result.total_count
    photos = result.photos

    if total == 0 or not photos:
        return (
            f"<b>User profile photos</b>\n"
            f"User ID: {escape(str(user_id))}\n"
            "No profile photos found."
        )

    lines = [
        "<b>User profile photos</b>",
        f"User ID: {escape(str(user_id))}",
        f"Total photos: {total}",
        f"Returned in this batch: {len(photos)}",
    ]

    for i, photo_sizes in enumerate(photos, start=1):
        # Each element of photos is a list of PhotoSize in increasing
        # resolution order; the last element has the highest resolution.
        best = photo_sizes[-1] if photo_sizes else None
        if best is not None:
            lines.append(
                f"Photo {i}: file_id={escape(best.file_id)} "
                f"({best.width}×{best.height}px)"
            )

    return "\n".join(lines)
