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
SUBSCRIPTION_PERIOD_SECONDS = 2592000


class CreateChatSubscriptionInviteLinkError(Exception):
    """Raised when ``createChatSubscriptionInviteLink`` validation or fallback fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


async def perform_create_chat_subscription_invite_link(
    bot: Any,
    *,
    chat_id: int,
    subscription_price: int,
    name: Optional[str] = None,
    subscription_period: int = SUBSCRIPTION_PERIOD_SECONDS,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> ChatInviteLink:
    """Create a paid subscription invite link through typed API or raw fallback.

    Telegram ``createChatSubscriptionInviteLink`` creates a subscription invite
    link for a supergroup or channel. The bot must be an administrator in the
    target chat with ``can_invite_users``. Telegram currently requires a
    30-day ``subscription_period`` and a ``subscription_price`` from 1 to 10000
    Telegram Stars.

    The project pins ``aiogram==3.3.0`` in ``requirements.txt``. Some deployed
    environments may have a newer aiogram with
    ``Bot.create_chat_subscription_invite_link``; when it is absent this helper
    uses the isolated raw Bot API fallback.
    """
    _validate_create_chat_subscription_invite_link_options(
        name=name,
        subscription_period=subscription_period,
        subscription_price=subscription_price,
    )

    create_chat_subscription_invite_link = getattr(
        bot,
        "create_chat_subscription_invite_link",
        None,
    )
    if callable(create_chat_subscription_invite_link):
        try:
            result = await create_chat_subscription_invite_link(
                chat_id=chat_id,
                name=name,
                subscription_period=subscription_period,
                subscription_price=subscription_price,
            )
        except TelegramAPIError as exc:
            logger.warning(
                "create_chat_subscription_invite_link_failed",
                chat_id=chat_id,
                error_type=type(exc).__name__,
                error=str(exc),
            )
            raise

        logger.info("create_chat_subscription_invite_link_succeeded", chat_id=chat_id)
        return result

    return await _perform_create_chat_subscription_invite_link_raw(
        bot,
        chat_id=chat_id,
        name=name,
        subscription_period=subscription_period,
        subscription_price=subscription_price,
        request_timeout=request_timeout,
    )


def _validate_create_chat_subscription_invite_link_options(
    *,
    name: Optional[str],
    subscription_period: int,
    subscription_price: int,
) -> None:
    if name is not None and len(name) > SUBSCRIPTION_INVITE_LINK_NAME_LIMIT:
        raise CreateChatSubscriptionInviteLinkError("name must be 0-32 characters.")
    if subscription_period != SUBSCRIPTION_PERIOD_SECONDS:
        raise CreateChatSubscriptionInviteLinkError(
            "subscription_period must be 2592000 seconds."
        )
    if not 1 <= subscription_price <= 10000:
        raise CreateChatSubscriptionInviteLinkError(
            "subscription_price must be between 1 and 10000 Telegram Stars."
        )


async def _perform_create_chat_subscription_invite_link_raw(
    bot: Any,
    *,
    chat_id: int,
    name: Optional[str],
    subscription_period: int,
    subscription_price: int,
    request_timeout: float,
) -> ChatInviteLink:
    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "subscription_period": subscription_period,
        "subscription_price": subscription_price,
    }
    if name is not None:
        payload["name"] = name
    url = _build_api_url(bot, "createChatSubscriptionInviteLink")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "create_chat_subscription_invite_link_failed",
            chat_id=chat_id,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise CreateChatSubscriptionInviteLinkError(
            f"createChatSubscriptionInviteLink request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "create_chat_subscription_invite_link_failed",
            chat_id=chat_id,
            error_code=error_code,
            error=description,
        )
        raise CreateChatSubscriptionInviteLinkError(
            description,
            error_code=error_code,
        )

    logger.info("create_chat_subscription_invite_link_succeeded", chat_id=chat_id)
    return ChatInviteLink.model_validate(data["result"])


def format_create_chat_subscription_invite_link_result(
    *,
    chat_id: int,
    link: ChatInviteLink,
) -> str:
    """Format a successful ``createChatSubscriptionInviteLink`` result."""
    lines = [
        "<b>createChatSubscriptionInviteLink</b>",
        f"Chat ID: {escape(str(chat_id))}",
        f"Invite link: {escape(link.invite_link)}",
        "Status: subscription invite link created successfully.",
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
