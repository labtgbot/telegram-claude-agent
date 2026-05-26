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


class RevokeChatInviteLinkError(Exception):
    """Raised when ``revokeChatInviteLink`` validation or raw fallback fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


async def perform_revoke_chat_invite_link(
    bot: Any,
    *,
    chat_id: int,
    invite_link: str,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> ChatInviteLink:
    """Revoke an invite link through typed aiogram API or raw fallback.

    Telegram ``revokeChatInviteLink`` revokes an invite link created by the bot
    for a group, supergroup or channel. If the primary link is revoked, Telegram
    automatically generates a new one. The bot must be an administrator in the
    target chat with ``can_invite_users``. No special update subscription is
    required for the command-driven scenario.
    """
    _validate_revoke_chat_invite_link_options(invite_link=invite_link)

    revoke_chat_invite_link = getattr(bot, "revoke_chat_invite_link", None)
    if callable(revoke_chat_invite_link):
        try:
            result = await revoke_chat_invite_link(
                chat_id=chat_id,
                invite_link=invite_link,
            )
        except TelegramAPIError as exc:
            logger.warning(
                "revoke_chat_invite_link_failed",
                chat_id=chat_id,
                error_type=type(exc).__name__,
                error=str(exc),
            )
            raise

        logger.info("revoke_chat_invite_link_succeeded", chat_id=chat_id)
        return result

    return await _perform_revoke_chat_invite_link_raw(
        bot,
        chat_id=chat_id,
        invite_link=invite_link,
        request_timeout=request_timeout,
    )


def _validate_revoke_chat_invite_link_options(*, invite_link: str) -> None:
    if not invite_link:
        raise RevokeChatInviteLinkError("invite_link is required.")


async def _perform_revoke_chat_invite_link_raw(
    bot: Any,
    *,
    chat_id: int,
    invite_link: str,
    request_timeout: float,
) -> ChatInviteLink:
    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "invite_link": invite_link,
    }
    url = _build_api_url(bot, "revokeChatInviteLink")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "revoke_chat_invite_link_failed",
            chat_id=chat_id,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise RevokeChatInviteLinkError(
            f"revokeChatInviteLink request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "revoke_chat_invite_link_failed",
            chat_id=chat_id,
            error_code=error_code,
            error=description,
        )
        raise RevokeChatInviteLinkError(description, error_code=error_code)

    logger.info("revoke_chat_invite_link_succeeded", chat_id=chat_id)
    return ChatInviteLink.model_validate(data["result"])


def format_revoke_chat_invite_link_result(*, chat_id: int, link: ChatInviteLink) -> str:
    """Format a successful ``revokeChatInviteLink`` result for HTML responses."""
    lines = [
        "<b>revokeChatInviteLink</b>",
        f"Chat ID: {escape(str(chat_id))}",
        f"Invite link: {escape(link.invite_link)}",
        "Status: invite link revoked successfully.",
        f"Is primary: {escape(str(link.is_primary))}",
        f"Is revoked: {escape(str(link.is_revoked))}",
        f"Creates join request: {escape(str(link.creates_join_request))}",
    ]
    if link.name:
        lines.append(f"Name: {escape(link.name)}")
    if link.expire_date:
        expire_date = link.expire_date
        if isinstance(expire_date, datetime):
            expire_value = int(expire_date.timestamp())
        else:
            expire_value = expire_date
        lines.append(f"Expire date: {escape(str(expire_value))}")
    if link.member_limit:
        lines.append(f"Member limit: {escape(str(link.member_limit))}")
    return "\n".join(lines)
