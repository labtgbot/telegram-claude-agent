from html import escape
from typing import Any

import structlog
from aiogram.exceptions import TelegramAPIError
from aiogram.types import BotShortDescription

logger = structlog.get_logger()


async def perform_get_my_short_description(
    bot: Any,
    *,
    language_code: str | None = None,
) -> BotShortDescription:
    """Fetch the bot's localized short description via typed aiogram API.

    Calls Telegram ``getMyShortDescription`` through
    ``Bot.get_my_short_description()``. The method is read-only, does not
    require chat administrator rights and has no required update types. This
    project exposes it through startup audit and deny-by-default admin commands
    so BotFather profile state is reproducible.
    """
    normalized_language = language_code.strip() if language_code else None

    try:
        result = await bot.get_my_short_description(
            language_code=normalized_language
        )
    except TelegramAPIError as exc:
        logger.warning(
            "get_my_short_description_failed",
            has_language_code=normalized_language is not None,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise

    logger.info(
        "get_my_short_description_succeeded",
        short_description_length=len(result.short_description),
        has_language_code=normalized_language is not None,
    )
    return result


async def audit_configured_bot_short_description(
    bot: Any,
    *,
    language_code: str | None,
) -> BotShortDescription:
    """Read the configured bot short description during startup for audit logs."""
    result = await perform_get_my_short_description(
        bot,
        language_code=language_code,
    )
    logger.info(
        "get_my_short_description_startup_audit_succeeded",
        short_description_length=len(result.short_description),
        has_language_code=bool(language_code),
    )
    return result


def format_get_my_short_description_result(
    bot_short_description: BotShortDescription,
    *,
    language_code: str | None = None,
) -> str:
    """Format ``getMyShortDescription`` output for HTML responses."""
    rendered_short_description = (
        escape(bot_short_description.short_description)
        if bot_short_description.short_description
        else "<i>empty</i>"
    )
    lines = [
        "<b>getMyShortDescription</b>",
        f"Short description: {rendered_short_description}",
    ]
    if language_code:
        lines.append(f"Language: <code>{escape(language_code.strip())}</code>")
    else:
        lines.append("Language: default")
    lines.append("Status: bot short description fetched.")
    return "\n".join(lines)
