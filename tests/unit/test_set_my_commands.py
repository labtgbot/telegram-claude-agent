from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import SetMyCommands
from aiogram.types import BotCommand

from bot.handlers import commands
from bot.services.set_my_commands import (
    format_set_my_commands_result,
    perform_set_my_commands,
)


def _message(text: str = "/setmycommands", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_perform_set_my_commands_uses_typed_aiogram_api():
    bot = SimpleNamespace(set_my_commands=AsyncMock(return_value=True))
    bot_commands = [
        BotCommand(command="start", description="Start the bot"),
        BotCommand(command="help", description="Show help"),
    ]

    result = await perform_set_my_commands(bot, commands=bot_commands)

    assert result is True
    bot.set_my_commands.assert_awaited_once_with(commands=bot_commands)


async def test_perform_set_my_commands_reraises_bad_request():
    bot_commands = [BotCommand(command="start", description="Start the bot")]
    error = TelegramBadRequest(
        method=SetMyCommands(commands=bot_commands),
        message="Bad Request: BOT_COMMAND_INVALID",
    )
    bot = SimpleNamespace(set_my_commands=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_set_my_commands(bot, commands=bot_commands)


async def test_perform_set_my_commands_reraises_forbidden():
    bot_commands = [BotCommand(command="start", description="Start the bot")]
    error = TelegramForbiddenError(
        method=SetMyCommands(commands=bot_commands),
        message="Forbidden: bot was blocked by the user",
    )
    bot = SimpleNamespace(set_my_commands=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_set_my_commands(bot, commands=bot_commands)


def test_format_set_my_commands_result_escapes_fields():
    text = format_set_my_commands_result(
        [
            BotCommand(command="start", description="Start <bot>"),
            BotCommand(command="help", description="Show & help"),
        ]
    )

    assert "setMyCommands" in text
    assert "/start - Start &lt;bot&gt;" in text
    assert "/help - Show &amp; help" in text


async def test_cmd_set_my_commands_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_set_my_commands", AsyncMock())
    message = _message(text="/setmycommands start:Start the bot", chat_id=42)

    await commands.cmd_set_my_commands(message)

    commands.perform_set_my_commands.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_set_my_commands_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_set_my_commands", AsyncMock())
    message = _message(text="/setmycommands", chat_id=42)

    await commands.cmd_set_my_commands(message)

    commands.perform_set_my_commands.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "setmycommands usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_set_my_commands_calls_service(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_set_my_commands", AsyncMock(return_value=True))
    monkeypatch.setattr(commands, "format_set_my_commands_result", lambda _: "ok")
    message = _message(
        text="/setmycommands start:Start the bot | help:Show help",
        chat_id=42,
    )

    await commands.cmd_set_my_commands(message)

    call_commands = commands.perform_set_my_commands.await_args.kwargs["commands"]
    assert call_commands == [
        BotCommand(command="start", description="Start the bot"),
        BotCommand(command="help", description="Show help"),
    ]
    message.answer.assert_awaited_once_with("ok", parse_mode="HTML")


async def test_cmd_set_my_commands_reports_telegram_errors(monkeypatch):
    bot_commands = [BotCommand(command="start", description="Start the bot")]
    error = TelegramBadRequest(
        method=SetMyCommands(commands=bot_commands),
        message="Bad Request: BOT_COMMAND_INVALID",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_set_my_commands", AsyncMock(side_effect=error))
    message = _message(text="/setmycommands start:Start the bot", chat_id=42)

    await commands.cmd_set_my_commands(message)

    args, _ = message.answer.await_args
    assert "Could not set bot commands" in args[0]
    assert "BOT_COMMAND_INVALID" not in args[0]
    assert "Please try again later" in args[0]


def test_parse_set_my_commands_args_required_only():
    result = commands._parse_set_my_commands_args(
        "/setmycommands start:Start the bot | help:Show help"
    )

    assert result == [
        BotCommand(command="start", description="Start the bot"),
        BotCommand(command="help", description="Show help"),
    ]


def test_parse_set_my_commands_args_rejects_missing_description():
    assert commands._parse_set_my_commands_args("/setmycommands start") is None


def test_parse_set_my_commands_args_rejects_invalid_command_name():
    assert (
        commands._parse_set_my_commands_args("/setmycommands Start:Start the bot")
        is None
    )


def test_parse_set_my_commands_args_rejects_too_many_commands():
    items = [f"cmd{i}:Description {i}" for i in range(101)]

    assert commands._parse_set_my_commands_args("/setmycommands " + " | ".join(items)) is None
