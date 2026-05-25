from typing import Any, Optional

import structlog
from aiogram.exceptions import TelegramAPIError

logger = structlog.get_logger()


async def perform_send_location(
    bot: Any,
    *,
    chat_id: int,
    latitude: float,
    longitude: float,
    horizontal_accuracy: Optional[float] = None,
    live_period: Optional[int] = None,
    heading: Optional[int] = None,
    proximity_alert_radius: Optional[int] = None,
    message_thread_id: Optional[int] = None,
    disable_notification: Optional[bool] = None,
    protect_content: Optional[bool] = None,
) -> Any:
    """Send a point on the map into a chat via the typed aiogram API.

    Calls the typed aiogram ``Bot.send_location()`` wrapper for the Telegram
    ``sendLocation`` method so the bot can deliver a geographic point as a real
    Telegram location instead of only a textual interpretation. The Telegram
    method requires ``chat_id``, ``latitude`` and ``longitude`` and returns the
    sent ``Message`` on success. ``horizontal_accuracy`` is the radius of
    uncertainty in meters (0-1500). A live location is started by passing
    ``live_period`` (60-86400 seconds); for live locations ``heading`` (1-360
    degrees) sets the direction of movement and ``proximity_alert_radius``
    (1-100000 meters) the distance for proximity alerts. The parameters passed
    here are the ones available in the pinned ``aiogram==3.3.0`` (Bot API 7.0)
    typed wrapper.

    Coordinates can identify a person's whereabouts, so they are intentionally
    kept out of the structured logs; only whether the location is live and the
    sent message id are logged.
    """
    try:
        result = await bot.send_location(
            chat_id=chat_id,
            latitude=latitude,
            longitude=longitude,
            horizontal_accuracy=horizontal_accuracy,
            live_period=live_period,
            heading=heading,
            proximity_alert_radius=proximity_alert_radius,
            message_thread_id=message_thread_id,
            disable_notification=disable_notification,
            protect_content=protect_content,
        )
    except TelegramAPIError as exc:
        logger.warning(
            "send_location_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            chat_id=chat_id,
        )
        raise

    logger.info(
        "location_sent",
        chat_id=chat_id,
        is_live=live_period is not None,
        has_horizontal_accuracy=horizontal_accuracy is not None,
        protect_content=bool(protect_content),
        sent_message_id=getattr(result, "message_id", None),
    )
    return result
