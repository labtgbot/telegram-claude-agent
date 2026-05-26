from html import escape
from typing import Any, Optional

import structlog
from aiogram.exceptions import TelegramAPIError

logger = structlog.get_logger()

SET_MY_NAME_LIMIT = 64


class SetMyNameValidationError(ValueError):
    """Raised when a local ``setMyName`` request is invalid."""


def validate_bot_name(name: Optional[str]) -> Optional[str]:
    """Normalize and validate a Telegram bot display name."""
    if name is None:
        return None

    normalized = name.strip()
    if len(normalized) > SET_MY_NAME_LIMIT:
        raise SetMyNameValidationError(
            f"Bot name is too long: {len(normalized)} characters "
            f"(max {SET_MY_NAME_LIMIT})."
        )

    return normalized


async def perform_set_my_name(
    bot: Any,
    *,
    name: Optional[str] = None,
    language_code: Optional[str] = None,
) -> bool:
    """Set or clear the bot's localized display name via typed aiogram API.

    Calls Telegram ``setMyName`` through ``Bot.set_my_name()``. Telegram uses
    the default name when ``language_code`` is omitted and a localized name when
    it is present. Passing an empty name clears the selected name. The method
    changes the bot's public profile and does not require chat administrator
    rights, so this project exposes it only through configuration sync and
    deny-by-default admin commands.
    """
    normalized_name = validate_bot_name(name)
    normalized_language = language_code.strip() if language_code else None

    try:
        result = await bot.set_my_name(
            name=normalized_name,
            language_code=normalized_language,
        )
    except TelegramAPIError as exc:
        logger.warning(
            "set_my_name_failed",
            name_length=len(normalized_name or ""),
            has_language_code=normalized_language is not None,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise

    logger.info(
        "set_my_name_succeeded",
        name_length=len(normalized_name or ""),
        has_language_code=normalized_language is not None,
    )
    return result


async def sync_configured_bot_name(
    bot: Any,
    *,
    name: Optional[str],
    language_code: Optional[str],
) -> bool:
    """Apply configured bot name when ``TELEGRAM_BOT_NAME`` is set."""
    if name is None:
        logger.info("set_my_name_sync_skipped", reason="name_not_configured")
        return False

    await perform_set_my_name(bot, name=name, language_code=language_code)
    return True


def format_set_my_name_result(*, name: Optional[str], language_code: Optional[str] = None) -> str:
    """Format a successful ``setMyName`` result for HTML responses."""
    normalized_name = validate_bot_name(name)
    rendered_name = escape(normalized_name) if normalized_name else "<i>empty</i>"
    lines = [
        "<b>setMyName</b>",
        f"Name: {rendered_name}",
    ]
    if language_code:
        lines.append(f"Language: <code>{escape(language_code.strip())}</code>")
    else:
        lines.append("Language: default")
    lines.append("Status: bot name updated.")
    return "\n".join(lines)
