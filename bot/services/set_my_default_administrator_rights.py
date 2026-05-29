from html import escape
from typing import Any, Optional

import structlog
from aiogram.exceptions import TelegramAPIError
from aiogram.types import ChatAdministratorRights

logger = structlog.get_logger()


async def perform_set_my_default_administrator_rights(
    bot: Any,
    *,
    rights: Optional[ChatAdministratorRights] = None,
    for_channels: Optional[bool] = None,
) -> bool:
    """Set or clear default administrator rights via typed aiogram API."""
    dumped_rights = rights.model_dump(exclude_none=True) if rights else None

    try:
        result = await bot.set_my_default_administrator_rights(
            rights=rights,
            for_channels=for_channels,
        )
    except TelegramAPIError as exc:
        logger.warning(
            "set_my_default_administrator_rights_failed",
            rights=dumped_rights,
            for_channels=for_channels,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise

    logger.info(
        "set_my_default_administrator_rights_succeeded",
        rights=dumped_rights,
        for_channels=for_channels,
    )
    return result


async def sync_configured_my_default_administrator_rights(
    bot: Any,
    *,
    rights: Optional[ChatAdministratorRights],
    for_channels: Optional[bool],
    configured: bool,
) -> bool:
    """Apply configured default administrator rights when startup sync is enabled."""
    if not configured:
        logger.info(
            "set_my_default_administrator_rights_sync_skipped",
            reason="rights_not_configured",
        )
        return False

    await perform_set_my_default_administrator_rights(
        bot,
        rights=rights,
        for_channels=for_channels,
    )
    return True


def parse_default_administrator_rights_configured(value: Optional[str]) -> bool:
    """Return whether the startup sync variable was intentionally configured."""
    return value is not None


def format_set_my_default_administrator_rights_result(
    *,
    preset: str,
    rights: Optional[ChatAdministratorRights],
    for_channels: Optional[bool],
) -> str:
    """Format a successful setMyDefaultAdministratorRights result."""
    lines = [
        "<b>setMyDefaultAdministratorRights</b>",
        f"Preset: {escape(preset)}",
    ]

    if for_channels is True:
        lines.append("Target: channels")
    elif for_channels is False:
        lines.append("Target: groups and supergroups")
    else:
        lines.append("Target: Telegram default")

    if rights is None:
        lines.append("Rights: cleared")
    else:
        dumped = rights.model_dump(exclude_none=True)
        enabled = [name for name, value in dumped.items() if value is True]
        disabled = [name for name, value in dumped.items() if value is False]
        if enabled:
            lines.append(f"Enabled rights: {escape(', '.join(enabled))}")
        if disabled:
            lines.append(f"Disabled rights: {escape(', '.join(disabled))}")

    lines.append("Status: default administrator rights updated.")
    return "\n".join(lines)
