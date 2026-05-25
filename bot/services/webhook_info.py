from datetime import datetime, timezone
from html import escape
from typing import Any

import structlog
from aiogram.exceptions import TelegramAPIError
from aiogram.types import WebhookInfo

logger = structlog.get_logger()

DEFAULT_ALLOWED_UPDATES = (
    "Telegram default (all update types except chat_member, "
    "message_reaction, and message_reaction_count)"
)


async def fetch_webhook_info(bot: Any) -> WebhookInfo:
    try:
        info = await bot.get_webhook_info()
    except TelegramAPIError as exc:
        logger.warning(
            "webhook_info_fetch_failed",
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise

    logger.info(
        "webhook_info_fetched",
        webhook_enabled=bool(info.url),
        pending_update_count=info.pending_update_count,
        allowed_updates=info.allowed_updates or [],
        has_last_delivery_error=bool(info.last_error_message),
        has_last_synchronization_error=bool(info.last_synchronization_error_date),
    )
    return info


def format_webhook_info(info: WebhookInfo) -> str:
    status = "enabled" if info.url else "disabled"
    allowed_updates = _format_allowed_updates(info.allowed_updates)
    delivery_error = _format_error(info.last_error_date, info.last_error_message)
    sync_error = _format_error(info.last_synchronization_error_date, None)

    lines = [
        "<b>Webhook diagnostics</b>",
        f"Status: {status}",
        f"URL: {escape(info.url) if info.url else 'not set'}",
        f"Pending updates: {info.pending_update_count}",
        f"Allowed updates: {allowed_updates}",
        f"Custom certificate: {_yes_no(info.has_custom_certificate)}",
    ]

    if info.ip_address:
        lines.append(f"IP address: {escape(info.ip_address)}")
    if info.max_connections is not None:
        lines.append(f"Max connections: {info.max_connections}")

    lines.append(f"Last delivery error: {delivery_error}")
    if sync_error != "none":
        lines.append(f"Last synchronization error: {sync_error}")

    return "\n".join(lines)


def _format_allowed_updates(allowed_updates: list[str] | None) -> str:
    if allowed_updates is None:
        return DEFAULT_ALLOWED_UPDATES
    if not allowed_updates:
        return "all update types"
    return escape(", ".join(allowed_updates))


def _format_error(error_date: datetime | int | None, message: str | None) -> str:
    if error_date is None and not message:
        return "none"

    parts = []
    if error_date is not None:
        parts.append(_format_datetime(error_date))
    if message:
        parts.append(escape(message))
    return " - ".join(parts)


def _format_datetime(value: datetime | int) -> str:
    if isinstance(value, int):
        value = datetime.fromtimestamp(value, tz=timezone.utc)
    elif value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"
