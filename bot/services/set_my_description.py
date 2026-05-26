from html import escape
from typing import Any, Optional

import structlog
from aiogram.exceptions import TelegramAPIError

logger = structlog.get_logger()

SET_MY_DESCRIPTION_LIMIT = 512


class SetMyDescriptionValidationError(ValueError):
    """Raised when a local ``setMyDescription`` request is invalid."""


def validate_bot_description(description: Optional[str]) -> Optional[str]:
    """Normalize and validate a Telegram bot description."""
    if description is None:
        return None

    normalized = description.strip()
    if len(normalized) > SET_MY_DESCRIPTION_LIMIT:
        raise SetMyDescriptionValidationError(
            f"Bot description is too long: {len(normalized)} characters "
            f"(max {SET_MY_DESCRIPTION_LIMIT})."
        )

    return normalized


async def perform_set_my_description(
    bot: Any,
    *,
    description: Optional[str] = None,
    language_code: Optional[str] = None,
) -> bool:
    """Set or clear the bot's localized description via typed aiogram API.

    Calls Telegram ``setMyDescription`` through ``Bot.set_my_description()``.
    Telegram uses the default description when ``language_code`` is omitted and
    a localized description when it is present. Passing an empty description
    clears the selected description. The method changes the bot's public
    profile and does not require chat administrator rights, so this project
    exposes it only through configuration sync and deny-by-default admin
    commands.
    """
    normalized_description = validate_bot_description(description)
    normalized_language = language_code.strip() if language_code else None

    try:
        result = await bot.set_my_description(
            description=normalized_description,
            language_code=normalized_language,
        )
    except TelegramAPIError as exc:
        logger.warning(
            "set_my_description_failed",
            description_length=len(normalized_description or ""),
            has_language_code=normalized_language is not None,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise

    logger.info(
        "set_my_description_succeeded",
        description_length=len(normalized_description or ""),
        has_language_code=normalized_language is not None,
    )
    return result


async def sync_configured_bot_description(
    bot: Any,
    *,
    description: Optional[str],
    language_code: Optional[str],
) -> bool:
    """Apply configured bot description when ``TELEGRAM_BOT_DESCRIPTION`` is set."""
    if description is None:
        logger.info("set_my_description_sync_skipped", reason="description_not_configured")
        return False

    await perform_set_my_description(
        bot,
        description=description,
        language_code=language_code,
    )
    return True


def format_set_my_description_result(
    *,
    description: Optional[str],
    language_code: Optional[str] = None,
) -> str:
    """Format a successful ``setMyDescription`` result for HTML responses."""
    normalized_description = validate_bot_description(description)
    rendered_description = (
        escape(normalized_description) if normalized_description else "<i>empty</i>"
    )
    lines = [
        "<b>setMyDescription</b>",
        f"Description: {rendered_description}",
    ]
    if language_code:
        lines.append(f"Language: <code>{escape(language_code.strip())}</code>")
    else:
        lines.append("Language: default")
    lines.append("Status: bot description updated.")
    return "\n".join(lines)
