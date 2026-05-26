from dataclasses import dataclass
from html import escape
from typing import Any, Sequence

import structlog
from aiogram.exceptions import TelegramAPIError
from aiogram.types import BotCommand

from bot.services.delete_my_commands import BotCommandScope, _scope_label

logger = structlog.get_logger()


@dataclass(frozen=True)
class BotCommandComparison:
    missing: list[BotCommand]
    unexpected: list[BotCommand]
    description_mismatches: list[tuple[str, str, str]]

    @property
    def matches(self) -> bool:
        return (
            not self.missing
            and not self.unexpected
            and not self.description_mismatches
        )


async def perform_get_my_commands(
    bot: Any,
    *,
    scope: BotCommandScope | None = None,
    language_code: str | None = None,
) -> list[BotCommand]:
    """Fetch bot commands for a scope/language via the typed aiogram API."""
    try:
        result = await bot.get_my_commands(
            scope=scope,
            language_code=language_code,
        )
    except TelegramAPIError as exc:
        logger.warning(
            "get_my_commands_failed",
            scope=_scope_label(scope),
            language_code=language_code,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise

    logger.info(
        "get_my_commands_succeeded",
        scope=_scope_label(scope),
        language_code=language_code,
        command_count=len(result),
    )
    return list(result)


def compare_bot_commands(
    actual: Sequence[BotCommand],
    expected: Sequence[BotCommand],
) -> BotCommandComparison:
    actual_by_name = {command.command: command for command in actual}
    expected_by_name = {command.command: command for command in expected}

    missing = [
        command
        for command in expected
        if command.command not in actual_by_name
    ]
    unexpected = [
        command
        for command in actual
        if command.command not in expected_by_name
    ]
    description_mismatches = [
        (
            command.command,
            command.description,
            actual_by_name[command.command].description,
        )
        for command in expected
        if command.command in actual_by_name
        and actual_by_name[command.command].description != command.description
    ]
    return BotCommandComparison(
        missing=missing,
        unexpected=unexpected,
        description_mismatches=description_mismatches,
    )


def format_get_my_commands_result(
    commands: Sequence[BotCommand],
    *,
    scope: BotCommandScope | None = None,
    language_code: str | None = None,
    expected: Sequence[BotCommand] | None = None,
) -> str:
    """Format ``getMyCommands`` output and optional mismatch diagnostics."""
    lines = [
        "<b>getMyCommands</b>",
        f"Scope: {escape(_scope_label(scope))}",
        f"Language: {escape(language_code or 'default')}",
        f"Status: fetched {len(commands)} bot command(s).",
    ]

    if commands:
        lines.extend(
            f"/{escape(command.command)} - {escape(command.description)}"
            for command in commands
        )
    else:
        lines.append("No commands are configured for this scope/language.")

    if expected is not None:
        comparison = compare_bot_commands(commands, expected)
        lines.append("")
        if comparison.matches:
            lines.append("Expected match: actual command menu matches expected configuration.")
        else:
            lines.append("Expected mismatch:")
            lines.extend(
                f"missing /{escape(command.command)} - {escape(command.description)}"
                for command in comparison.missing
            )
            lines.extend(
                f"unexpected /{escape(command.command)} - {escape(command.description)}"
                for command in comparison.unexpected
            )
            lines.extend(
                "description differs for "
                f"/{escape(command)}: expected {escape(expected_description)}, "
                f"actual {escape(actual_description)}"
                for command, expected_description, actual_description
                in comparison.description_mismatches
            )

    return "\n".join(lines)
