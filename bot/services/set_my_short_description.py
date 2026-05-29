from html import escape
from typing import Any, Optional

import structlog
from aiogram.exceptions import TelegramAPIError

logger = structlog.get_logger()

SET_MY_SHORT_DESCRIPTION_LIMIT = 120


class SetMyShortDescriptionValidationError(ValueError):
    """Raised when a local ``setMyShortDescription`` request is invalid."""


def validate_bot_short_description(short_description: Optional[str]) -> Optional[str]:
    """Normalize and validate a Telegram bot short description."""
    if short_description is None:
        return None

    normalized = short_description.strip()
    if len(normalized) > SET_MY_SHORT_DESCRIPTION_LIMIT:
        raise SetMyShortDescriptionValidationError(
            f"Bot short description is too long: {len(normalized)} characters "
            f"(max {SET_MY_SHORT_DESCRIPTION_LIMIT})."
        )

    return normalized


async def perform_set_my_short_description(
    bot: Any,
    *,
    short_description: Optional[str] = None,
    language_code: Optional[str] = None,
) -> bool:
    """Set or clear the bot's localized short description via typed aiogram API."""
    normalized_short_description = validate_bot_short_description(short_description)
    normalized_language = language_code.strip() if language_code else None

    try:
        result = await bot.set_my_short_description(
            short_description=normalized_short_description,
            language_code=normalized_language,
        )
    except TelegramAPIError as exc:
        logger.warning(
            "set_my_short_description_failed",
            short_description_length=len(normalized_short_description or ""),
            has_language_code=normalized_language is not None,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise

    logger.info(
        "set_my_short_description_succeeded",
        short_description_length=len(normalized_short_description or ""),
        has_language_code=normalized_language is not None,
    )
    return result


async def sync_configured_bot_short_description(
    bot: Any,
    *,
    short_description: Optional[str],
    language_code: Optional[str],
) -> bool:
    """Apply configured bot short description when set."""
    if short_description is None:
        logger.info(
            "set_my_short_description_sync_skipped",
            reason="short_description_not_configured",
        )
        return False

    await perform_set_my_short_description(
        bot,
        short_description=short_description,
        language_code=language_code,
    )
    return True


def format_set_my_short_description_result(
    *,
    short_description: Optional[str],
    language_code: Optional[str] = None,
) -> str:
    """Format a successful ``setMyShortDescription`` result for HTML responses."""
    normalized_short_description = validate_bot_short_description(short_description)
    rendered_short_description = (
        escape(normalized_short_description)
        if normalized_short_description
        else "<i>empty</i>"
    )
    lines = [
        "<b>setMyShortDescription</b>",
        f"Short description: {rendered_short_description}",
    ]
    if language_code:
        lines.append(f"Language: <code>{escape(language_code.strip())}</code>")
    else:
        lines.append("Language: default")
    lines.append("Status: bot short description updated.")
    return "\n".join(lines)
