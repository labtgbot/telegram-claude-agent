from html import escape
from typing import Any, Optional

import httpx
import structlog

from bot.services.send_checklist import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()


class ReplaceManagedBotTokenError(Exception):
    """Raised when ``replaceManagedBotToken`` validation or raw call fails.

    The pinned ``aiogram==3.3.0`` predates Telegram Bot API 9.6 and has no typed
    wrapper for managed-bot token lifecycle methods, so this helper calls the
    raw HTTP endpoint directly. ``error_code`` holds Telegram's ``error_code``
    when available.
    """

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


async def perform_replace_managed_bot_token(
    bot: Any,
    *,
    user_id: int,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> str:
    """Replace the token of a Telegram managed bot and return the new token.

    Telegram ``replaceManagedBotToken`` accepts the managed bot's user id and
    returns the newly issued token as a string. The calling bot must be the
    manager/owner allowed by Telegram for that managed bot. Because this rotates
    a credential, callers should require an explicit admin confirmation and logs
    include only structural metadata, never token values.
    """
    if user_id <= 0:
        raise ReplaceManagedBotTokenError("user_id must be a positive integer.")

    url = _build_api_url(bot, "replaceManagedBotToken")
    payload = {"user_id": user_id}

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "replace_managed_bot_token_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            user_id=user_id,
        )
        raise ReplaceManagedBotTokenError(
            f"replaceManagedBotToken request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "replace_managed_bot_token_failed",
            error_code=error_code,
            error=description,
            user_id=user_id,
        )
        raise ReplaceManagedBotTokenError(description, error_code=error_code)

    token = data.get("result")
    if not isinstance(token, str) or not token:
        logger.warning(
            "replace_managed_bot_token_failed",
            error="empty token result",
            user_id=user_id,
        )
        raise ReplaceManagedBotTokenError(
            "Telegram returned an empty token result."
        )

    logger.info(
        "managed_bot_token_replaced",
        user_id=user_id,
        token_length=len(token),
    )
    return token


def format_replaced_managed_bot_token(*, user_id: int, token: str) -> str:
    """Render the newly issued sensitive token for the requesting admin chat."""
    return "\n".join(
        [
            "<b>Managed bot token replaced</b>",
            f"User id: <code>{user_id}</code>",
            f"New token: <code>{escape(token)}</code>",
            "Store this credential securely and update any deployment that used "
            "the previous managed bot token. Rollback requires rotating again "
            "or using a separately preserved previous token where Telegram still "
            "accepts it.",
        ]
    )
