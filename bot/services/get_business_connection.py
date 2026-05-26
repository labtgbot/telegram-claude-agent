from html import escape
from typing import Any, Optional

import httpx
import structlog

from bot.services.send_checklist import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()


class GetBusinessConnectionError(Exception):
    """Raised when the raw ``getBusinessConnection`` Bot API call fails.

    The pinned ``aiogram==3.3.0`` predates the Bot API method and has no typed
    wrapper for it, so this helper calls the raw HTTP endpoint directly.
    ``error_code`` holds Telegram's ``error_code`` when available.
    """

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


async def perform_get_business_connection(
    bot: Any,
    *,
    business_connection_id: str,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> dict[str, Any]:
    """Fetch details about a connected Telegram business account.

    Telegram ``getBusinessConnection`` requires a live
    ``business_connection_id`` and returns a ``BusinessConnection`` object with
    owner and lifecycle metadata. This admin-only helper intentionally logs only
    structural state, not owner names or tokens.
    """
    business_connection_id = business_connection_id.strip()
    if not business_connection_id:
        raise GetBusinessConnectionError("business_connection_id is required.")

    url = _build_api_url(bot, "getBusinessConnection")
    payload = {"business_connection_id": business_connection_id}

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "get_business_connection_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            business_connection_id=business_connection_id,
        )
        raise GetBusinessConnectionError(
            f"getBusinessConnection request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "get_business_connection_failed",
            error_code=error_code,
            error=description,
            business_connection_id=business_connection_id,
        )
        raise GetBusinessConnectionError(description, error_code=error_code)

    result = data.get("result") or {}
    logger.info(
        "business_connection_fetched",
        business_connection_id=business_connection_id,
        can_reply=bool(result.get("can_reply")),
        is_enabled=bool(result.get("is_enabled")),
        has_user_chat_id=result.get("user_chat_id") is not None,
    )
    return result


def format_business_connection(connection: dict[str, Any]) -> str:
    user = connection.get("user") or {}
    owner = _format_user(user)
    lines = [
        "<b>Business connection</b>",
        f"ID: <code>{escape(str(connection.get('id', 'unknown')))}</code>",
        f"Owner: {owner}",
    ]

    if connection.get("user_chat_id") is not None:
        lines.append(
            f"User chat id: <code>{escape(str(connection['user_chat_id']))}</code>"
        )
    if connection.get("date") is not None:
        lines.append(f"Date: <code>{escape(str(connection['date']))}</code>")

    lines.extend(
        [
            f"Can reply: {_yes_no(bool(connection.get('can_reply')))}",
            f"Enabled: {_yes_no(bool(connection.get('is_enabled')))}",
        ]
    )
    return "\n".join(lines)


def _format_user(user: dict[str, Any]) -> str:
    user_id = user.get("id", "unknown")
    name = user.get("first_name") or user.get("username") or "unknown"
    username = user.get("username")
    if username:
        return f"{escape(str(name))} (@{escape(str(username))}, id {escape(str(user_id))})"
    return f"{escape(str(name))} (id {escape(str(user_id))})"


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"
