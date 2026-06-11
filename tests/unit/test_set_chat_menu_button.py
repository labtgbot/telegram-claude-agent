from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import SetChatMenuButton
from aiogram.types import MenuButtonCommands, MenuButtonDefault, MenuButtonWebApp, WebAppInfo

from bot.handlers import commands
from bot.services.set_chat_menu_button import (
    format_set_chat_menu_button_result,
    perform_set_chat_menu_button,
)


def _message(text: str = "/setchatmenubutton", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_perform_set_chat_menu_button_uses_typed_aiogram_api():
    button = MenuButtonCommands()
    bot = SimpleNamespace(set_chat_menu_button=AsyncMock(return_value=True))

    result = await perform_set_chat_menu_button(
        bot,
        chat_id=-100123,
        menu_button=button,
    )

    assert result is True
    bot.set_chat_menu_button.assert_awaited_once_with(
        chat_id=-100123,
        menu_button=button,
    )


async def test_perform_set_chat_menu_button_reraises_bad_request():
    button = MenuButtonDefault()
    error = TelegramBadRequest(
        method=SetChatMenuButton(chat_id=-100123, menu_button=button),
        message="Bad Request: chat not found",
    )
    bot = SimpleNamespace(set_chat_menu_button=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_set_chat_menu_button(
            bot,
            chat_id=-100123,
            menu_button=button,
        )


async def test_perform_set_chat_menu_button_reraises_forbidden():
    button = MenuButtonCommands()
    error = TelegramForbiddenError(
        method=SetChatMenuButton(chat_id=-100123, menu_button=button),
        message="Forbidden: bot was blocked by the user",
    )
    bot = SimpleNamespace(set_chat_menu_button=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_set_chat_menu_button(
            bot,
            chat_id=-100123,
            menu_button=button,
        )


def test_format_set_chat_menu_button_result_escapes_fields():
    text = format_set_chat_menu_button_result(
        chat_id=-100123,
        menu_button=MenuButtonWebApp(
            text="Support <&>",
            web_app=WebAppInfo(url="https://example.com/?x=<tag>"),
        ),
    )

    assert "setChatMenuButton" in text
    assert "-100123" in text
    assert "web_app" in text
    assert "Support &lt;&amp;&gt;" in text
    assert "https://example.com/?x=&lt;tag&gt;" in text
    assert "chat menu button updated" in text


async def test_cmd_set_chat_menu_button_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_set_chat_menu_button", AsyncMock())
    message = _message(text="/setchatmenubutton commands", chat_id=42)

    await commands.cmd_set_chat_menu_button(message)

    commands.perform_set_chat_menu_button.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_set_chat_menu_button_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_set_chat_menu_button", AsyncMock())
    message = _message(text="/setchatmenubutton", chat_id=42)

    await commands.cmd_set_chat_menu_button(message)

    commands.perform_set_chat_menu_button.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "setchatmenubutton usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_set_chat_menu_button_calls_service(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_set_chat_menu_button",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(commands, "format_set_chat_menu_button_result", lambda **_: "ok")
    message = _message(
        text="/setchatmenubutton chat_id=-100123 web_app Support https://example.com",
        chat_id=42,
    )

    await commands.cmd_set_chat_menu_button(message)

    commands.perform_set_chat_menu_button.assert_awaited_once()
    _, kwargs = commands.perform_set_chat_menu_button.await_args
    assert kwargs["chat_id"] == -100123
    assert kwargs["menu_button"].type == "web_app"
    assert kwargs["menu_button"].text == "Support"
    assert kwargs["menu_button"].web_app.url == "https://example.com"
    message.answer.assert_awaited_once_with("ok", parse_mode="HTML")


async def test_cmd_set_chat_menu_button_reports_telegram_errors(monkeypatch):
    button = MenuButtonCommands()
    error = TelegramBadRequest(
        method=SetChatMenuButton(chat_id=-100123, menu_button=button),
        message="Bad Request: chat not found",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_set_chat_menu_button",
        AsyncMock(side_effect=error),
    )
    message = _message(text="/setchatmenubutton chat_id=-100123 commands", chat_id=42)

    await commands.cmd_set_chat_menu_button(message)

    args, _ = message.answer.await_args
    assert "Could not set the chat menu button" in args[0]
    assert "chat not found" not in args[0]
    assert "Please try again later" in args[0]


def test_parse_set_chat_menu_button_args_default_button():
    chat_id, button = commands._parse_set_chat_menu_button_args("/setchatmenubutton default")

    assert chat_id is None
    assert isinstance(button, MenuButtonDefault)


def test_parse_set_chat_menu_button_args_commands_button_with_chat_id():
    chat_id, button = commands._parse_set_chat_menu_button_args(
        "/setchatmenubutton chat_id=-100123 commands"
    )

    assert chat_id == -100123
    assert isinstance(button, MenuButtonCommands)


def test_parse_set_chat_menu_button_args_web_app_button():
    chat_id, button = commands._parse_set_chat_menu_button_args(
        "/setchatmenubutton web_app Support https://example.com"
    )

    assert chat_id is None
    assert isinstance(button, MenuButtonWebApp)
    assert button.text == "Support"
    assert button.web_app.url == "https://example.com"


def test_parse_set_chat_menu_button_args_invalid_values():
    assert commands._parse_set_chat_menu_button_args("/setchatmenubutton") is None
    assert (
        commands._parse_set_chat_menu_button_args(
            "/setchatmenubutton chat_id=bad commands"
        )
        is None
    )
    assert (
        commands._parse_set_chat_menu_button_args(
            "/setchatmenubutton web_app Support ftp://example.com"
        )
        is None
    )
    assert commands._parse_set_chat_menu_button_args("/setchatmenubutton unknown") is None
