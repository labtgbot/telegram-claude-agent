from typing import Any, Optional

import structlog
from aiogram.exceptions import TelegramAPIError

logger = structlog.get_logger()


async def perform_send_venue(
    bot: Any,
    *,
    chat_id: int,
    latitude: float,
    longitude: float,
    title: str,
    address: str,
    foursquare_id: Optional[str] = None,
    foursquare_type: Optional[str] = None,
    google_place_id: Optional[str] = None,
    google_place_type: Optional[str] = None,
    message_thread_id: Optional[int] = None,
    disable_notification: Optional[bool] = None,
    protect_content: Optional[bool] = None,
) -> Any:
    """Send information about a venue into a chat via the typed aiogram API.

    Calls the typed aiogram ``Bot.send_venue()`` wrapper for the Telegram
    ``sendVenue`` method so the bot can deliver a named place (a point on the
    map with a title and an address) as a real Telegram venue instead of only a
    textual interpretation. The Telegram method requires ``chat_id``,
    ``latitude``, ``longitude``, ``title`` and ``address`` and returns the sent
    ``Message`` on success. A venue can optionally be linked to a Foursquare
    place via ``foursquare_id`` and ``foursquare_type`` (for example
    ``arts_entertainment/aquarium``) or to a Google Places location via
    ``google_place_id`` and ``google_place_type``. The parameters passed here
    are the ones available in the pinned ``aiogram==3.3.0`` (Bot API 7.0) typed
    wrapper.

    A venue exposes a precise place and address, so they are intentionally kept
    out of the structured logs; only whether the venue carries Foursquare or
    Google Places metadata and the sent message id are logged.
    """
    try:
        result = await bot.send_venue(
            chat_id=chat_id,
            latitude=latitude,
            longitude=longitude,
            title=title,
            address=address,
            foursquare_id=foursquare_id,
            foursquare_type=foursquare_type,
            google_place_id=google_place_id,
            google_place_type=google_place_type,
            message_thread_id=message_thread_id,
            disable_notification=disable_notification,
            protect_content=protect_content,
        )
    except TelegramAPIError as exc:
        logger.warning(
            "send_venue_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            chat_id=chat_id,
        )
        raise

    logger.info(
        "venue_sent",
        chat_id=chat_id,
        has_foursquare=foursquare_id is not None,
        has_google_place=google_place_id is not None,
        protect_content=bool(protect_content),
        sent_message_id=getattr(result, "message_id", None),
    )
    return result
