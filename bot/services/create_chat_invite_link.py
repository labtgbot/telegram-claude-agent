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


class CreateChatInviteLinkError(Exception):
    """Raised when ``createChatInviteLink`` validation or raw fallback fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


async def perform_create_chat_invite_link(
    bot: Any,
    *,
    chat_id: int,
    name: Optional[str] = None,
    expire_date: Optional[int] = None,
    member_limit: Optional[int] = None,
    creates_join_request: Optional[bool] = None,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> ChatInviteLink:
    """Create an additional invite link through typed aiogram API or raw fallback.

    Telegram ``createChatInviteLink`` creates an additional invite link for a
    group, supergroup or channel. The bot must be an administrator in the
    target chat with ``can_invite_users``. Telegram allows setting ``name``,
    ``expire_date``, ``member_limit`` and ``creates_join_request``; join-request
    links cannot also have a member limit.
    """
    _validate_create_chat_invite_link_options(
        member_limit=member_limit,
        creates_join_request=creates_join_request,
    )

    create_chat_invite_link = getattr(bot, "create_chat_invite_link", None)
    if callable(create_chat_invite_link):
        try:
            result = await create_chat_invite_link(
                chat_id=chat_id,
                name=name,
                expire_date=expire_date,
                member_limit=member_limit,
                creates_join_request=creates_join_request,
            )
        except TelegramAPIError as exc:
            logger.warning(
                "create_chat_invite_link_failed",
                chat_id=chat_id,
                error_type=type(exc).__name__,
                error=str(exc),
            )
            raise

        logger.info("create_chat_invite_link_succeeded", chat_id=chat_id)
        return result

    return await _perform_create_chat_invite_link_raw(
        bot,
        chat_id=chat_id,
        name=name,
        expire_date=expire_date,
        member_limit=member_limit,
        creates_join_request=creates_join_request,
        request_timeout=request_timeout,
    )


def _validate_create_chat_invite_link_options(
    *,
    member_limit: Optional[int],
    creates_join_request: Optional[bool],
) -> None:
    if member_limit is not None and not 1 <= member_limit <= 99999:
        raise CreateChatInviteLinkError("member_limit must be between 1 and 99999.")
    if creates_join_request and member_limit is not None:
        raise CreateChatInviteLinkError(
            "creates_join_request cannot be used with member_limit."
        )


async def _perform_create_chat_invite_link_raw(
    bot: Any,
    *,
    chat_id: int,
    name: Optional[str],
    expire_date: Optional[int],
    member_limit: Optional[int],
    creates_join_request: Optional[bool],
    request_timeout: float,
) -> ChatInviteLink:
    payload: dict[str, Any] = {"chat_id": chat_id}
    optional = {
        "name": name,
        "expire_date": expire_date,
        "member_limit": member_limit,
        "creates_join_request": creates_join_request,
    }
    payload.update({key: value for key, value in optional.items() if value is not None})
    url = _build_api_url(bot, "createChatInviteLink")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "create_chat_invite_link_failed",
            chat_id=chat_id,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise CreateChatInviteLinkError(
            f"createChatInviteLink request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "create_chat_invite_link_failed",
            chat_id=chat_id,
            error_code=error_code,
            error=description,
        )
        raise CreateChatInviteLinkError(description, error_code=error_code)

    logger.info("create_chat_invite_link_succeeded", chat_id=chat_id)
    return ChatInviteLink.model_validate(data["result"])


def format_create_chat_invite_link_result(*, chat_id: int, link: ChatInviteLink) -> str:
    """Format a successful ``createChatInviteLink`` result for HTML responses."""
    lines = [
        "<b>createChatInviteLink</b>",
        f"Chat ID: {escape(str(chat_id))}",
        f"Invite link: {escape(link.invite_link)}",
        "Status: additional invite link created successfully.",
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
