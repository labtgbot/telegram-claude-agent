from typing import Any, Optional

import structlog
from aiogram.exceptions import TelegramAPIError

logger = structlog.get_logger()


async def perform_send_contact(
    bot: Any,
    *,
    chat_id: int,
    phone_number: str,
    first_name: str,
    last_name: Optional[str] = None,
    vcard: Optional[str] = None,
    message_thread_id: Optional[int] = None,
    disable_notification: Optional[bool] = None,
    protect_content: Optional[bool] = None,
) -> Any:
    """Send a phone contact into a chat via the typed aiogram API.

    Calls the typed aiogram ``Bot.send_contact()`` wrapper for the Telegram
    ``sendContact`` method so the bot can deliver a real Telegram contact (a
    name with a phone number that the recipient can save to the address book)
    instead of only a textual interpretation. The Telegram method requires
    ``chat_id``, the ``phone_number`` and the contact's ``first_name`` and
    returns the sent ``Message`` on success. A contact can optionally carry a
    ``last_name`` and additional structured data as a ``vcard`` (0-2048 bytes).
    The parameters passed here are the ones available in the pinned
    ``aiogram==3.3.0`` (Bot API 7.0) typed wrapper.

    The phone number, the contact's name and the vCard are personal data the
    operator chose to share, so they are intentionally kept out of the
    structured logs; only whether a last name or a vCard is present and the sent
    message id are logged.
    """
    try:
        result = await bot.send_contact(
            chat_id=chat_id,
            phone_number=phone_number,
            first_name=first_name,
            last_name=last_name,
            vcard=vcard,
            message_thread_id=message_thread_id,
            disable_notification=disable_notification,
            protect_content=protect_content,
        )
    except TelegramAPIError as exc:
        logger.warning(
            "send_contact_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            chat_id=chat_id,
        )
        raise

    logger.info(
        "contact_sent",
        chat_id=chat_id,
        has_last_name=last_name is not None,
        has_vcard=vcard is not None,
        protect_content=bool(protect_content),
        sent_message_id=getattr(result, "message_id", None),
    )
    return result
