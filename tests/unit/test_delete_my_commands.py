from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import DeleteMyCommands
from aiogram.types import (
    BotCommandScopeAllGroupChats,
    BotCommandScopeChat,
    BotCommandScopeDefault,
)

from bot.handlers import commands
from bot.services.delete_my_commands import (
    format_delete_my_commands_result,
    perform_delete_my_commands,
)


def _message(text: str = "/deletemycommands", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_perform_delete_my_commands_uses_typed_aiogram_api():
    bot = SimpleNamespace(delete_my_commands=AsyncMock(return_value=True))
    scope = BotCommandScopeChat(chat_id=123)

    result = await perform_delete_my_commands(
        bot,
        scope=scope,
        language_code="en",
    )

    assert result is True
    bot.delete_my_commands.assert_awaited_once_with(
        scope=scope,
        language_code="en",
    )


async def test_perform_delete_my_commands_reraises_bad_request():
    error = TelegramBadRequest(
        method=DeleteMyCommands(),
        message="Bad Request: language code is invalid",
    )
    bot = SimpleNamespace(delete_my_commands=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_delete_my_commands(bot)


async def test_perform_delete_my_commands_reraises_forbidden():
    error = TelegramForbiddenError(
        method=DeleteMyCommands(),
        message="Forbidden: bot was blocked by the user",
    )
    bot = SimpleNamespace(delete_my_commands=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_delete_my_commands(bot)


def test_format_delete_my_commands_result_describes_scope_and_language():
    text = format_delete_my_commands_result(
        scope=BotCommandScopeChat(chat_id=-100123),
        language_code="en",
    )

    assert "deleteMyCommands" in text
    assert "Scope: chat -100123" in text
    assert "Language: en" in text


async def test_cmd_delete_my_commands_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_delete_my_commands", AsyncMock())
    message = _message(text="/deletemycommands", chat_id=42)

    await commands.cmd_delete_my_commands(message)

    commands.perform_delete_my_commands.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_delete_my_commands_calls_service_with_defaults(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_delete_my_commands", AsyncMock(return_value=True)
    )
    monkeypatch.setattr(commands, "format_delete_my_commands_result", lambda **_: "ok")
    message = _message(text="/deletemycommands", chat_id=42)

    await commands.cmd_delete_my_commands(message)

    commands.perform_delete_my_commands.assert_awaited_once_with(
        message.bot,
        scope=None,
        language_code=None,
    )
    message.answer.assert_awaited_once_with("ok", parse_mode="HTML")


async def test_cmd_delete_my_commands_calls_service_with_scope_and_language(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_delete_my_commands", AsyncMock(return_value=True)
    )
    monkeypatch.setattr(commands, "format_delete_my_commands_result", lambda **_: "ok")
    message = _message(
        text="/deletemycommands scope=chat chat_id=-100123 language=en",
        chat_id=42,
    )

    await commands.cmd_delete_my_commands(message)

    call_kwargs = commands.perform_delete_my_commands.await_args.kwargs
    assert call_kwargs["scope"] == BotCommandScopeChat(chat_id=-100123)
    assert call_kwargs["language_code"] == "en"
    message.answer.assert_awaited_once_with("ok", parse_mode="HTML")


async def test_cmd_delete_my_commands_shows_usage_for_invalid_scope(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_delete_my_commands", AsyncMock())
    message = _message(text="/deletemycommands scope=unknown", chat_id=42)

    await commands.cmd_delete_my_commands(message)

    commands.perform_delete_my_commands.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "deletemycommands usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_delete_my_commands_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(
        method=DeleteMyCommands(),
        message="Bad Request: language code is invalid",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_delete_my_commands", AsyncMock(side_effect=error)
    )
    message = _message(text="/deletemycommands", chat_id=42)

    await commands.cmd_delete_my_commands(message)

    args, _ = message.answer.await_args
    assert "Could not delete bot commands" in args[0]
    assert "language code is invalid" in args[0]


def test_parse_delete_my_commands_args_defaults():
    assert commands._parse_delete_my_commands_args("/deletemycommands") == (None, None)


def test_parse_delete_my_commands_args_supports_default_scope():
    assert commands._parse_delete_my_commands_args(
        "/deletemycommands scope=default language=uk"
    ) == (BotCommandScopeDefault(), "uk")


def test_parse_delete_my_commands_args_supports_group_scope():
    assert commands._parse_delete_my_commands_args(
        "/deletemycommands scope=all_group_chats"
    ) == (BotCommandScopeAllGroupChats(), None)


def test_parse_delete_my_commands_args_requires_chat_id_for_chat_scope():
    assert commands._parse_delete_my_commands_args("/deletemycommands scope=chat") is None


def test_parse_delete_my_commands_args_rejects_bad_language_code():
    assert commands._parse_delete_my_commands_args(
        "/deletemycommands language=english"
    ) is None
