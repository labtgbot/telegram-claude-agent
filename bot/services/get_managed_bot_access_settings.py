from html import escape
from typing import Any, Optional

import httpx
import structlog

from bot.services.send_checklist import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()


class GetManagedBotAccessSettingsError(Exception):
    """Raised when ``getManagedBotAccessSettings`` validation or raw call fails.

    The pinned ``aiogram==3.3.0`` predates Telegram Bot API 10.0 and has no
    typed wrapper for managed-bot access settings, so this helper calls the raw
    HTTP endpoint directly. ``error_code`` holds Telegram's ``error_code`` when
    available.
    """

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


async def perform_get_managed_bot_access_settings(
    bot: Any,
    *,
    user_id: int,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> dict[str, Any]:
    """Fetch access settings of a Telegram managed bot.

    Telegram ``getManagedBotAccessSettings`` accepts the managed bot's user id
    and returns a ``BotAccessSettings`` object. The calling bot must be the
    manager/owner allowed by Telegram for that managed bot. The result may
    include user objects, so logs include only structural metadata.
    """
    if user_id <= 0:
        raise GetManagedBotAccessSettingsError(
            "user_id must be a positive integer."
        )

    url = _build_api_url(bot, "getManagedBotAccessSettings")
    payload = {"user_id": user_id}

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "get_managed_bot_access_settings_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            user_id=user_id,
        )
        raise GetManagedBotAccessSettingsError(
            f"getManagedBotAccessSettings request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "get_managed_bot_access_settings_failed",
            error_code=error_code,
            error=description,
            user_id=user_id,
        )
        raise GetManagedBotAccessSettingsError(
            description, error_code=error_code
        )

    settings = data.get("result")
    if not isinstance(settings, dict):
        logger.warning(
            "get_managed_bot_access_settings_failed",
            error="invalid settings result",
            user_id=user_id,
        )
        raise GetManagedBotAccessSettingsError(
            "Telegram returned an invalid access settings result."
        )

    is_access_restricted = settings.get("is_access_restricted")
    if not isinstance(is_access_restricted, bool):
        logger.warning(
            "get_managed_bot_access_settings_failed",
            error="missing is_access_restricted",
            user_id=user_id,
        )
        raise GetManagedBotAccessSettingsError(
            "Telegram returned access settings without is_access_restricted."
        )

    added_users = settings.get("added_users", [])
    added_users_count = len(added_users) if isinstance(added_users, list) else 0
    logger.info(
        "managed_bot_access_settings_fetched",
        user_id=user_id,
        is_access_restricted=is_access_restricted,
        added_users_count=added_users_count,
    )
    return settings


def format_managed_bot_access_settings(
    *, user_id: int, settings: dict[str, Any]
) -> str:
    """Render managed-bot access settings without leaking full user objects."""
    is_access_restricted = bool(settings.get("is_access_restricted"))
    added_users = settings.get("added_users")
    if not isinstance(added_users, list):
        added_users = []

    lines = [
        "<b>Managed bot access settings</b>",
        f"User id: <code>{user_id}</code>",
        f"Access restricted: <code>{str(is_access_restricted).lower()}</code>",
        f"Added users: <code>{len(added_users)}</code>",
    ]
    for user in added_users:
        if not isinstance(user, dict):
            continue
        user_id_value = user.get("id")
        display_name = _format_user_name(user)
        lines.append(
            f"- <code>{escape(str(user_id_value))}</code> {display_name}"
        )

    if is_access_restricted:
        lines.append("Only the owner and listed users can access this bot.")
    else:
        lines.append("The bot is available without an access allowlist.")
    return "\n".join(lines)


def _format_user_name(user: dict[str, Any]) -> str:
    parts = [
        str(user.get("first_name") or "").strip(),
        str(user.get("last_name") or "").strip(),
    ]
    name = " ".join(part for part in parts if part)
    username = str(user.get("username") or "").strip()
    if username:
        username = f"@{username}"
    rendered = " ".join(part for part in (name, username) if part)
    return escape(rendered) if rendered else ""
