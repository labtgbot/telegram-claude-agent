from html import escape
from typing import Any, Sequence

import structlog
from aiogram.exceptions import TelegramAPIError
from aiogram.types import BotCommand

logger = structlog.get_logger()


async def perform_set_my_commands(
    bot: Any,
    *,
    commands: Sequence[BotCommand],
) -> bool:
    """Set the bot command list via the typed aiogram API.

    Calls Telegram ``setMyCommands`` through ``Bot.set_my_commands()``. The
    method updates the default command list visible in Telegram clients. It
    does not require chat administrator rights, but this project exposes it as
    a deny-by-default admin command because it changes the bot's public UI.
    """
    try:
        result = await bot.set_my_commands(commands=commands)
    except TelegramAPIError as exc:
        logger.warning(
            "set_my_commands_failed",
            command_count=len(commands),
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise

    logger.info("set_my_commands_succeeded", command_count=len(commands))
    return result


def format_set_my_commands_result(commands: Sequence[BotCommand]) -> str:
    """Format a successful ``setMyCommands`` result for HTML responses."""
    lines = [
        "<b>setMyCommands</b>",
        f"Status: updated {len(commands)} bot command(s).",
    ]
    lines.extend(
        f"/{escape(command.command)} - {escape(command.description)}"
        for command in commands
    )
    return "\n".join(lines)
