from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import GetMyCommands
from aiogram.types import BotCommand, BotCommandScopeChat, BotCommandScopeDefault

from bot.handlers import commands
from bot.services.get_my_commands import (
    compare_bot_commands,
    format_get_my_commands_result,
    perform_get_my_commands,
)


def _message(text: str = "/getmycommands", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_perform_get_my_commands_uses_typed_aiogram_api():
    expected = [BotCommand(command="start", description="Start the bot")]
    bot = SimpleNamespace(get_my_commands=AsyncMock(return_value=expected))
    scope = BotCommandScopeChat(chat_id=-100123)

    result = await perform_get_my_commands(
        bot,
        scope=scope,
        language_code="en",
    )

    assert result == expected
    bot.get_my_commands.assert_awaited_once_with(scope=scope, language_code="en")


async def test_perform_get_my_commands_reraises_bad_request():
    error = TelegramBadRequest(
        method=GetMyCommands(),
        message="Bad Request: language code is invalid",
    )
    bot = SimpleNamespace(get_my_commands=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_get_my_commands(bot)


async def test_perform_get_my_commands_reraises_forbidden():
    error = TelegramForbiddenError(
        method=GetMyCommands(),
        message="Forbidden: bot was blocked by the user",
    )
    bot = SimpleNamespace(get_my_commands=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_get_my_commands(bot)


def test_compare_bot_commands_reports_match():
    actual = [BotCommand(command="start", description="Start the bot")]
    expected = [BotCommand(command="start", description="Start the bot")]

    result = compare_bot_commands(actual, expected)

    assert result.matches is True
    assert result.missing == []
    assert result.unexpected == []
    assert result.description_mismatches == []


def test_compare_bot_commands_reports_differences():
    actual = [
        BotCommand(command="start", description="Run"),
        BotCommand(command="extra", description="Extra command"),
    ]
    expected = [
        BotCommand(command="start", description="Start the bot"),
        BotCommand(command="help", description="Show help"),
    ]

    result = compare_bot_commands(actual, expected)

    assert result.matches is False
    assert result.missing == [BotCommand(command="help", description="Show help")]
    assert result.unexpected == [
        BotCommand(command="extra", description="Extra command")
    ]
    assert result.description_mismatches == [
        ("start", "Start the bot", "Run"),
    ]


def test_format_get_my_commands_result_includes_diagnostics():
    actual = [
        BotCommand(command="start", description="Run <bot>"),
        BotCommand(command="extra", description="Extra command"),
    ]
    expected = [BotCommand(command="start", description="Start the bot")]

    text = format_get_my_commands_result(
        actual,
        scope=BotCommandScopeChat(chat_id=-100123),
        language_code="en",
        expected=expected,
    )

    assert "getMyCommands" in text
    assert "Scope: chat -100123" in text
    assert "Language: en" in text
    assert "/start - Run &lt;bot&gt;" in text
    assert "Expected mismatch" in text
    assert "description differs for /start" in text
    assert "unexpected /extra" in text


async def test_cmd_get_my_commands_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_get_my_commands", AsyncMock())
    message = _message(chat_id=42)

    await commands.cmd_get_my_commands(message)

    commands.perform_get_my_commands.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_get_my_commands_calls_service_with_defaults(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_get_my_commands",
        AsyncMock(return_value=[BotCommand(command="start", description="Start")]),
    )
    monkeypatch.setattr(commands, "format_get_my_commands_result", lambda *_, **__: "ok")
    message = _message(text="/getmycommands", chat_id=42)

    await commands.cmd_get_my_commands(message)

    commands.perform_get_my_commands.assert_awaited_once_with(
        message.bot,
        scope=None,
        language_code=None,
    )
    message.answer.assert_awaited_once_with("ok", parse_mode="HTML")


async def test_cmd_get_my_commands_calls_service_with_scope_and_language(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_get_my_commands", AsyncMock(return_value=[]))
    monkeypatch.setattr(commands, "format_get_my_commands_result", lambda *_, **__: "ok")
    message = _message(
        text="/getmycommands scope=chat chat_id=-100123 language=en",
        chat_id=42,
    )

    await commands.cmd_get_my_commands(message)

    call_kwargs = commands.perform_get_my_commands.await_args.kwargs
    assert call_kwargs["scope"] == BotCommandScopeChat(chat_id=-100123)
    assert call_kwargs["language_code"] == "en"
    message.answer.assert_awaited_once_with("ok", parse_mode="HTML")


async def test_cmd_get_my_commands_shows_usage_for_invalid_scope(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_get_my_commands", AsyncMock())
    message = _message(text="/getmycommands scope=chat", chat_id=42)

    await commands.cmd_get_my_commands(message)

    commands.perform_get_my_commands.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "getmycommands usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_get_my_commands_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(
        method=GetMyCommands(),
        message="Bad Request: language code is invalid",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_get_my_commands", AsyncMock(side_effect=error))
    message = _message(text="/getmycommands", chat_id=42)

    await commands.cmd_get_my_commands(message)

    args, _ = message.answer.await_args
    assert "Could not get bot commands" in args[0]
    assert "language code is invalid" not in args[0]
    assert "Please try again later" in args[0]


def test_parse_get_my_commands_args_defaults():
    assert commands._parse_get_my_commands_args("/getmycommands") == (None, None)


def test_parse_get_my_commands_args_supports_default_scope():
    assert commands._parse_get_my_commands_args(
        "/getmycommands scope=default language=uk"
    ) == (BotCommandScopeDefault(), "uk")
