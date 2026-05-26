from html import escape
from typing import Any, Optional

import httpx
import structlog

from bot.services.send_checklist import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()


class GetManagedBotTokenError(Exception):
    """Raised when ``getManagedBotToken`` validation or raw call fails.

    The pinned ``aiogram==3.3.0`` predates Telegram Bot API 9.6 and has no typed
    wrapper for managed-bot token lifecycle methods, so this helper calls the
    raw HTTP endpoint directly. ``error_code`` holds Telegram's ``error_code``
    when available.
    """

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


async def perform_get_managed_bot_token(
    bot: Any,
    *,
    user_id: int,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> str:
    """Fetch the token of a Telegram managed bot.

    Telegram ``getManagedBotToken`` accepts the managed bot's user id and
    returns its token as a string. The calling bot must be the manager/owner
    allowed by Telegram for that managed bot. Because this returns a credential,
    logs include only structural metadata and never the token itself.
    """
    if user_id <= 0:
        raise GetManagedBotTokenError("user_id must be a positive integer.")

    url = _build_api_url(bot, "getManagedBotToken")
    payload = {"user_id": user_id}

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "get_managed_bot_token_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            user_id=user_id,
        )
        raise GetManagedBotTokenError(
            f"getManagedBotToken request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "get_managed_bot_token_failed",
            error_code=error_code,
            error=description,
            user_id=user_id,
        )
        raise GetManagedBotTokenError(description, error_code=error_code)

    token = data.get("result")
    if not isinstance(token, str) or not token:
        logger.warning(
            "get_managed_bot_token_failed",
            error="empty token result",
            user_id=user_id,
        )
        raise GetManagedBotTokenError("Telegram returned an empty token result.")

    logger.info(
        "managed_bot_token_fetched",
        user_id=user_id,
        token_length=len(token),
    )
    return token


def format_managed_bot_token(*, user_id: int, token: str) -> str:
    """Render the sensitive token for the requesting admin chat only."""
    return "\n".join(
        [
            "<b>Managed bot token</b>",
            f"User id: <code>{user_id}</code>",
            f"Token: <code>{escape(token)}</code>",
            "Store this credential securely. It can be revoked with Telegram "
            "<code>replaceManagedBotToken</code> or via BotFather flows.",
        ]
    )
