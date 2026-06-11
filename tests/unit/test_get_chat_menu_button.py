from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import GetChatMenuButton
from aiogram.types import MenuButtonCommands, MenuButtonWebApp, WebAppInfo

from bot.handlers import commands
from bot.services.get_chat_menu_button import (
    format_get_chat_menu_button_result,
    perform_get_chat_menu_button,
)


def _message(text: str = "/getchatmenubutton", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_perform_get_chat_menu_button_uses_typed_aiogram_api():
    button = MenuButtonCommands()
    bot = SimpleNamespace(get_chat_menu_button=AsyncMock(return_value=button))

    result = await perform_get_chat_menu_button(bot, chat_id=-100123)

    assert result == button
    bot.get_chat_menu_button.assert_awaited_once_with(chat_id=-100123)


async def test_perform_get_chat_menu_button_reraises_bad_request():
    error = TelegramBadRequest(
        method=GetChatMenuButton(chat_id=-100123),
        message="Bad Request: chat not found",
    )
    bot = SimpleNamespace(get_chat_menu_button=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_get_chat_menu_button(bot, chat_id=-100123)


async def test_perform_get_chat_menu_button_reraises_forbidden():
    error = TelegramForbiddenError(
        method=GetChatMenuButton(chat_id=-100123),
        message="Forbidden: bot was blocked by the user",
    )
    bot = SimpleNamespace(get_chat_menu_button=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_get_chat_menu_button(bot, chat_id=-100123)


def test_format_get_chat_menu_button_result_escapes_fields():
    text = format_get_chat_menu_button_result(
        MenuButtonWebApp(
            text="Support <&>",
            web_app=WebAppInfo(url="https://example.com/?x=<tag>"),
        ),
        chat_id=-100123,
    )

    assert "getChatMenuButton" in text
    assert "-100123" in text
    assert "web_app" in text
    assert "Support &lt;&amp;&gt;" in text
    assert "https://example.com/?x=&lt;tag&gt;" in text
    assert "chat menu button fetched" in text


async def test_cmd_get_chat_menu_button_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_get_chat_menu_button", AsyncMock())
    message = _message(text="/getchatmenubutton", chat_id=42)

    await commands.cmd_get_chat_menu_button(message)

    commands.perform_get_chat_menu_button.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_get_chat_menu_button_calls_service_with_defaults(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_get_chat_menu_button",
        AsyncMock(return_value=MenuButtonCommands()),
    )
    monkeypatch.setattr(commands, "format_get_chat_menu_button_result", lambda *_, **__: "ok")
    message = _message(text="/getchatmenubutton", chat_id=42)

    await commands.cmd_get_chat_menu_button(message)

    commands.perform_get_chat_menu_button.assert_awaited_once_with(
        message.bot,
        chat_id=None,
    )
    message.answer.assert_awaited_once_with("ok", parse_mode="HTML")


async def test_cmd_get_chat_menu_button_calls_service_with_chat_id(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_get_chat_menu_button",
        AsyncMock(return_value=MenuButtonCommands()),
    )
    monkeypatch.setattr(commands, "format_get_chat_menu_button_result", lambda *_, **__: "ok")
    message = _message(text="/getchatmenubutton chat_id=-100123", chat_id=42)

    await commands.cmd_get_chat_menu_button(message)

    commands.perform_get_chat_menu_button.assert_awaited_once_with(
        message.bot,
        chat_id=-100123,
    )
    message.answer.assert_awaited_once_with("ok", parse_mode="HTML")


async def test_cmd_get_chat_menu_button_shows_usage_for_invalid_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_get_chat_menu_button", AsyncMock())
    message = _message(text="/getchatmenubutton chat_id=bad", chat_id=42)

    await commands.cmd_get_chat_menu_button(message)

    commands.perform_get_chat_menu_button.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "getchatmenubutton usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_get_chat_menu_button_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(
        method=GetChatMenuButton(chat_id=-100123),
        message="Bad Request: chat not found",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_get_chat_menu_button",
        AsyncMock(side_effect=error),
    )
    message = _message(text="/getchatmenubutton chat_id=-100123", chat_id=42)

    await commands.cmd_get_chat_menu_button(message)

    args, _ = message.answer.await_args
    assert "Could not get the chat menu button" in args[0]
    assert "chat not found" not in args[0]
    assert "Please try again later" in args[0]


def test_parse_get_chat_menu_button_args_defaults():
    assert commands._parse_get_chat_menu_button_args("/getchatmenubutton") is None


def test_parse_get_chat_menu_button_args_chat_id():
    assert (
        commands._parse_get_chat_menu_button_args(
            "/getchatmenubutton chat_id=-100123"
        )
        == -100123
    )


def test_parse_get_chat_menu_button_args_invalid_values():
    assert commands._parse_get_chat_menu_button_args("") is False
    assert commands._parse_get_chat_menu_button_args("/getchatmenubutton extra") is False
    assert (
        commands._parse_get_chat_menu_button_args("/getchatmenubutton chat_id=bad")
        is False
    )
