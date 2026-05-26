from datetime import datetime
from html import escape
from typing import Any, Optional

import httpx
import structlog
from aiogram.exceptions import TelegramAPIError
from aiogram.types import ChatInviteLink

from bot.services.send_message_draft import _build_api_url

logger = structlog.get_logger()

DEFAULT_REQUEST_TIMEOUT = 60.0
SUBSCRIPTION_INVITE_LINK_NAME_LIMIT = 32


class EditChatSubscriptionInviteLinkError(Exception):
    """Raised when the raw ``editChatSubscriptionInviteLink`` fallback fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


async def perform_edit_chat_subscription_invite_link(
    bot: Any,
    *,
    chat_id: int,
    invite_link: str,
    name: Optional[str] = None,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> ChatInviteLink:
    """Edit a subscription invite link through typed aiogram API or raw fallback.

    Telegram ``editChatSubscriptionInviteLink`` edits a subscription invite link
    created by the bot. The bot must be an administrator in the target chat
    with ``can_invite_users``. Telegram allows changing only the link ``name``.

    The project pins ``aiogram==3.3.0`` in ``requirements.txt``. Some deployed
    environments may have a newer aiogram with
    ``Bot.edit_chat_subscription_invite_link``; when it is absent this helper
    uses the isolated raw Bot API fallback.
    """
    _validate_edit_chat_subscription_invite_link_options(
        invite_link=invite_link,
        name=name,
    )

    edit_chat_subscription_invite_link = getattr(
        bot,
        "edit_chat_subscription_invite_link",
        None,
    )
    if callable(edit_chat_subscription_invite_link):
        try:
            result = await edit_chat_subscription_invite_link(
                chat_id=chat_id,
                invite_link=invite_link,
                name=name,
            )
        except TelegramAPIError as exc:
            logger.warning(
                "edit_chat_subscription_invite_link_failed",
                chat_id=chat_id,
                error_type=type(exc).__name__,
                error=str(exc),
            )
            raise

        logger.info("edit_chat_subscription_invite_link_succeeded", chat_id=chat_id)
        return result

    return await _perform_edit_chat_subscription_invite_link_raw(
        bot,
        chat_id=chat_id,
        invite_link=invite_link,
        name=name,
        request_timeout=request_timeout,
    )


def _validate_edit_chat_subscription_invite_link_options(
    *,
    invite_link: str,
    name: Optional[str],
) -> None:
    if not invite_link:
        raise EditChatSubscriptionInviteLinkError("invite_link is required.")
    if name is not None and len(name) > SUBSCRIPTION_INVITE_LINK_NAME_LIMIT:
        raise EditChatSubscriptionInviteLinkError("name must be 0-32 characters.")


async def _perform_edit_chat_subscription_invite_link_raw(
    bot: Any,
    *,
    chat_id: int,
    invite_link: str,
    name: Optional[str],
    request_timeout: float,
) -> ChatInviteLink:
    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "invite_link": invite_link,
    }
    if name is not None:
        payload["name"] = name
    url = _build_api_url(bot, "editChatSubscriptionInviteLink")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "edit_chat_subscription_invite_link_failed",
            chat_id=chat_id,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise EditChatSubscriptionInviteLinkError(
            f"editChatSubscriptionInviteLink request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "edit_chat_subscription_invite_link_failed",
            chat_id=chat_id,
            error_code=error_code,
            error=description,
        )
        raise EditChatSubscriptionInviteLinkError(description, error_code=error_code)

    logger.info("edit_chat_subscription_invite_link_succeeded", chat_id=chat_id)
    return ChatInviteLink.model_validate(data["result"])


def format_edit_chat_subscription_invite_link_result(
    *,
    chat_id: int,
    link: ChatInviteLink,
) -> str:
    """Format a successful ``editChatSubscriptionInviteLink`` result."""
    lines = [
        "<b>editChatSubscriptionInviteLink</b>",
        f"Chat ID: {escape(str(chat_id))}",
        f"Invite link: {escape(link.invite_link)}",
        "Status: subscription invite link edited successfully.",
    ]
    if link.name:
        lines.append(f"Name: {escape(link.name)}")
    if link.subscription_period:
        lines.append(f"Subscription period: {escape(str(link.subscription_period))}")
    if link.subscription_price:
        lines.append(f"Subscription price: {escape(str(link.subscription_price))}")
    if link.expire_date:
        expire_date = link.expire_date
        if isinstance(expire_date, datetime):
            expire_value = int(expire_date.timestamp())
        else:
            expire_value = expire_date
        lines.append(f"Expire date: {escape(str(expire_value))}")
    return "\n".join(lines)
