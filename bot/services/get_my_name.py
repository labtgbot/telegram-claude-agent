from html import escape
from typing import Any

import structlog
from aiogram.exceptions import TelegramAPIError
from aiogram.types import BotName

logger = structlog.get_logger()


async def perform_get_my_name(
    bot: Any,
    *,
    language_code: str | None = None,
) -> BotName:
    """Fetch the bot's localized display name via typed aiogram API.

    Calls Telegram ``getMyName`` through ``Bot.get_my_name()``. The method is
    read-only, does not require chat administrator rights and has no required
    update types. This project exposes it through startup sync/audit and
    deny-by-default admin commands so BotFather profile state is reproducible.
    """
    normalized_language = language_code.strip() if language_code else None

    try:
        result = await bot.get_my_name(language_code=normalized_language)
    except TelegramAPIError as exc:
        logger.warning(
            "get_my_name_failed",
            has_language_code=normalized_language is not None,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise

    logger.info(
        "get_my_name_succeeded",
        name_length=len(result.name),
        has_language_code=normalized_language is not None,
    )
    return result


async def audit_configured_bot_name(
    bot: Any,
    *,
    language_code: str | None,
) -> BotName:
    """Read the configured bot name during startup for operational audit logs."""
    result = await perform_get_my_name(bot, language_code=language_code)
    logger.info(
        "get_my_name_startup_audit_succeeded",
        name_length=len(result.name),
        has_language_code=bool(language_code),
    )
    return result


def format_get_my_name_result(
    bot_name: BotName,
    *,
    language_code: str | None = None,
) -> str:
    """Format ``getMyName`` output for HTML responses."""
    lines = [
        "<b>getMyName</b>",
        f"Name: {escape(bot_name.name) if bot_name.name else '<i>empty</i>'}",
    ]
    if language_code:
        lines.append(f"Language: <code>{escape(language_code.strip())}</code>")
    else:
        lines.append("Language: default")
    lines.append("Status: bot name fetched.")
    return "\n".join(lines)
