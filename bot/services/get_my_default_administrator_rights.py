from html import escape
from typing import Any

import structlog
from aiogram.exceptions import TelegramAPIError
from aiogram.types import ChatAdministratorRights

logger = structlog.get_logger()


async def perform_get_my_default_administrator_rights(
    bot: Any,
    *,
    for_channels: bool | None = None,
) -> ChatAdministratorRights:
    """Fetch default administrator rights via typed aiogram API or raw fallback."""
    try:
        if hasattr(bot, "get_my_default_administrator_rights"):
            result = await bot.get_my_default_administrator_rights(
                for_channels=for_channels,
            )
        else:
            response = await bot.session.make_request(
                bot,
                "getMyDefaultAdministratorRights",
                {"for_channels": for_channels},
            )
            result = ChatAdministratorRights.model_validate(response)
    except TelegramAPIError as exc:
        logger.warning(
            "get_my_default_administrator_rights_failed",
            for_channels=for_channels,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise

    logger.info(
        "get_my_default_administrator_rights_succeeded",
        for_channels=for_channels,
        enabled_rights=_enabled_rights(result),
    )
    return result


async def audit_configured_my_default_administrator_rights(
    bot: Any,
    *,
    for_channels: bool | None,
) -> ChatAdministratorRights:
    """Read default administrator rights during startup for audit logs."""
    result = await perform_get_my_default_administrator_rights(
        bot,
        for_channels=for_channels,
    )
    logger.info(
        "get_my_default_administrator_rights_startup_audit_succeeded",
        for_channels=for_channels,
        enabled_rights=_enabled_rights(result),
    )
    return result


def format_get_my_default_administrator_rights_result(
    rights: ChatAdministratorRights,
    *,
    for_channels: bool | None = None,
) -> str:
    """Format ``getMyDefaultAdministratorRights`` output for HTML responses."""
    lines = ["<b>getMyDefaultAdministratorRights</b>"]
    if for_channels is True:
        lines.append("Target: channels")
    elif for_channels is False:
        lines.append("Target: groups and supergroups")
    else:
        lines.append("Target: Telegram default")

    enabled = _enabled_rights(rights)
    if enabled:
        lines.append(f"Enabled rights: {escape(', '.join(enabled))}")
    else:
        lines.append("Enabled rights: none")

    lines.append("Status: default administrator rights fetched.")
    return "\n".join(lines)


def _enabled_rights(rights: ChatAdministratorRights) -> list[str]:
    dumped = rights.model_dump(exclude_none=True)
    return [name for name, value in dumped.items() if value is True]
