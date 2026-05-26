from html import escape
from typing import Any, Optional

import httpx
import structlog
from aiogram.exceptions import TelegramAPIError

from bot.services.send_message_draft import _build_api_url

logger = structlog.get_logger()

DEFAULT_REQUEST_TIMEOUT = 60.0


class DeclineChatJoinRequestError(Exception):
    """Raised when ``declineChatJoinRequest`` validation or raw fallback fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


async def perform_decline_chat_join_request(
    bot: Any,
    *,
    chat_id: int,
    user_id: int,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> bool:
    """Decline a pending chat join request.

    Telegram ``declineChatJoinRequest`` declines a user's pending request to
    join a group, supergroup or channel. The bot must be an administrator in the
    target chat with ``can_invite_users``. aiogram versions differ in typed
    wrapper coverage, so this helper uses the typed method when present and an
    isolated raw Bot API fallback otherwise.
    """
    _validate_decline_chat_join_request_args(chat_id=chat_id, user_id=user_id)

    decline_chat_join_request = getattr(bot, "decline_chat_join_request", None)
    if callable(decline_chat_join_request):
        try:
            result = await decline_chat_join_request(
                chat_id=chat_id,
                user_id=user_id,
            )
        except TelegramAPIError as exc:
            logger.warning(
                "decline_chat_join_request_failed",
                chat_id=chat_id,
                user_id=user_id,
                error_type=type(exc).__name__,
                error=str(exc),
            )
            raise

        logger.info(
            "decline_chat_join_request_succeeded",
            chat_id=chat_id,
            user_id=user_id,
        )
        return result

    return await _perform_decline_chat_join_request_raw(
        bot,
        chat_id=chat_id,
        user_id=user_id,
        request_timeout=request_timeout,
    )


def _validate_decline_chat_join_request_args(*, chat_id: int, user_id: int) -> None:
    if chat_id == 0:
        raise DeclineChatJoinRequestError("chat_id must be non-zero.")
    if user_id <= 0:
        raise DeclineChatJoinRequestError("user_id must be a positive integer.")


async def _perform_decline_chat_join_request_raw(
    bot: Any,
    *,
    chat_id: int,
    user_id: int,
    request_timeout: float,
) -> bool:
    payload = {"chat_id": chat_id, "user_id": user_id}
    url = _build_api_url(bot, "declineChatJoinRequest")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "decline_chat_join_request_failed",
            chat_id=chat_id,
            user_id=user_id,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise DeclineChatJoinRequestError(
            f"declineChatJoinRequest request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "decline_chat_join_request_failed",
            chat_id=chat_id,
            user_id=user_id,
            error_code=error_code,
            error=description,
        )
        raise DeclineChatJoinRequestError(description, error_code=error_code)

    logger.info(
        "decline_chat_join_request_succeeded",
        chat_id=chat_id,
        user_id=user_id,
    )
    return data.get("result", True)


def format_decline_chat_join_request_result(*, chat_id: int, user_id: int) -> str:
    """Format a successful ``declineChatJoinRequest`` result for HTML responses."""
    return "\n".join(
        [
            "<b>declineChatJoinRequest</b>",
            f"Chat ID: {escape(str(chat_id))}",
            f"User ID: {escape(str(user_id))}",
            "Status: join request declined successfully.",
        ]
    )
