from html import escape
from typing import Any, Optional

import httpx
import structlog

from bot.services.send_checklist import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()


class SetManagedBotAccessSettingsError(Exception):
    """Raised when ``setManagedBotAccessSettings`` validation or raw call fails.

    The pinned ``aiogram==3.3.0`` predates Telegram Bot API 10.0 and has no
    typed wrapper for managed-bot access settings, so this helper calls the raw
    HTTP endpoint directly. ``error_code`` holds Telegram's ``error_code`` when
    available.
    """

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


async def perform_set_managed_bot_access_settings(
    bot: Any,
    *,
    user_id: int,
    is_access_restricted: bool,
    added_user_ids: list[int] | None = None,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> bool:
    """Set access settings of a Telegram managed bot.

    Telegram ``setManagedBotAccessSettings`` accepts the managed bot's user id
    and a ``BotAccessSettings`` object. The calling bot must be the
    manager/owner allowed by Telegram for that managed bot. Logs include only
    structural metadata, never returned user objects or unrelated chat data.
    """
    settings = _build_access_settings(
        is_access_restricted=is_access_restricted,
        added_user_ids=added_user_ids,
    )
    if user_id <= 0:
        raise SetManagedBotAccessSettingsError(
            "user_id must be a positive integer."
        )

    url = _build_api_url(bot, "setManagedBotAccessSettings")
    payload = {"user_id": user_id, "settings": settings}

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "set_managed_bot_access_settings_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            user_id=user_id,
            is_access_restricted=is_access_restricted,
            added_users_count=len(settings.get("added_users", [])),
        )
        raise SetManagedBotAccessSettingsError(
            f"setManagedBotAccessSettings request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "set_managed_bot_access_settings_failed",
            error_code=error_code,
            error=description,
            user_id=user_id,
            is_access_restricted=is_access_restricted,
            added_users_count=len(settings.get("added_users", [])),
        )
        raise SetManagedBotAccessSettingsError(
            description, error_code=error_code
        )

    if data.get("result") is not True:
        logger.warning(
            "set_managed_bot_access_settings_failed",
            error="unexpected result",
            user_id=user_id,
        )
        raise SetManagedBotAccessSettingsError(
            "Telegram returned an unexpected access settings result."
        )

    logger.info(
        "managed_bot_access_settings_set",
        user_id=user_id,
        is_access_restricted=is_access_restricted,
        added_users_count=len(settings.get("added_users", [])),
    )
    return True


def format_set_managed_bot_access_settings_result(
    *,
    user_id: int,
    is_access_restricted: bool,
    added_user_ids: list[int] | None = None,
) -> str:
    added_user_ids = added_user_ids or []
    lines = [
        "<b>Managed bot access settings updated</b>",
        f"User id: <code>{user_id}</code>",
        f"Access restricted: <code>{str(is_access_restricted).lower()}</code>",
        f"Added users: <code>{len(added_user_ids)}</code>",
    ]
    for added_user_id in added_user_ids:
        lines.append(f"- <code>{escape(str(added_user_id))}</code>")

    if is_access_restricted:
        lines.append("Only the owner and listed users can access this bot.")
    else:
        lines.append("The bot is available without an access allowlist.")
    return "\n".join(lines)


def _build_access_settings(
    *,
    is_access_restricted: bool,
    added_user_ids: list[int] | None,
) -> dict[str, Any]:
    if not isinstance(is_access_restricted, bool):
        raise SetManagedBotAccessSettingsError(
            "is_access_restricted must be a boolean."
        )

    settings: dict[str, Any] = {
        "is_access_restricted": is_access_restricted,
    }
    if added_user_ids is None:
        return settings

    if not isinstance(added_user_ids, list):
        raise SetManagedBotAccessSettingsError(
            "added_user_ids must be a list of positive integers."
        )

    normalized_user_ids: list[int] = []
    for added_user_id in added_user_ids:
        if not isinstance(added_user_id, int) or added_user_id <= 0:
            raise SetManagedBotAccessSettingsError(
                "added_user_ids must contain only positive integers."
            )
        normalized_user_ids.append(added_user_id)

    settings["added_users"] = normalized_user_ids
    return settings
