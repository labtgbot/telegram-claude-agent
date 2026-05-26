from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import PinChatMessage

from bot.handlers import commands
from bot.services.pin_chat_message import (
    format_pin_chat_message_result,
    perform_pin_chat_message,
)


def _message(text: str = "/pinchatmessage", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_perform_pin_chat_message_uses_typed_aiogram_api():
    bot = SimpleNamespace(pin_chat_message=AsyncMock(return_value=True))

    result = await perform_pin_chat_message(
        bot,
        chat_id=-100123,
        message_id=55,
        disable_notification=True,
    )

    assert result is True
    bot.pin_chat_message.assert_awaited_once_with(
        chat_id=-100123,
        message_id=55,
        disable_notification=True,
    )


async def test_perform_pin_chat_message_defaults_disable_notification_to_none():
    bot = SimpleNamespace(pin_chat_message=AsyncMock(return_value=True))

    result = await perform_pin_chat_message(bot, chat_id=-100123, message_id=55)

    assert result is True
    bot.pin_chat_message.assert_awaited_once_with(
        chat_id=-100123,
        message_id=55,
        disable_notification=None,
    )


async def test_perform_pin_chat_message_reraises_bad_request():
    error = TelegramBadRequest(
        method=PinChatMessage(chat_id=-100123, message_id=55),
        message="Bad Request: message to pin not found",
    )
    bot = SimpleNamespace(pin_chat_message=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_pin_chat_message(
            bot,
            chat_id=-100123,
            message_id=55,
        )


async def test_perform_pin_chat_message_reraises_forbidden():
    error = TelegramForbiddenError(
        method=PinChatMessage(chat_id=-100123, message_id=55),
        message="Forbidden: bot is not an administrator",
    )
    bot = SimpleNamespace(pin_chat_message=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_pin_chat_message(
            bot,
            chat_id=-100123,
            message_id=55,
        )


def test_format_pin_chat_message_result():
    text = format_pin_chat_message_result(
        chat_id=-100123,
        message_id=55,
        disable_notification=True,
    )

    assert "pinChatMessage" in text
    assert "-100123" in text
    assert "55" in text
    assert "disabled" in text
    assert "chat message pinned" in text


async def test_cmd_pin_chat_message_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_pin_chat_message", AsyncMock())
    message = _message(text="/pinchatmessage -100123 55", chat_id=42)

    await commands.cmd_pin_chat_message(message)

    commands.perform_pin_chat_message.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_pin_chat_message_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_pin_chat_message", AsyncMock())
    message = _message(text="/pinchatmessage", chat_id=42)

    await commands.cmd_pin_chat_message(message)

    commands.perform_pin_chat_message.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "pinchatmessage usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_pin_chat_message_calls_service(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_pin_chat_message", AsyncMock(return_value=True)
    )
    monkeypatch.setattr(commands, "format_pin_chat_message_result", lambda **_: "ok")
    message = _message(text="/pinchatmessage -100123 55 silent", chat_id=42)

    await commands.cmd_pin_chat_message(message)

    commands.perform_pin_chat_message.assert_awaited_once_with(
        message.bot,
        chat_id=-100123,
        message_id=55,
        disable_notification=True,
    )
    message.answer.assert_awaited_once_with("ok", parse_mode="HTML")


async def test_cmd_pin_chat_message_calls_service_with_loud_notification(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_pin_chat_message", AsyncMock(return_value=True)
    )
    monkeypatch.setattr(commands, "format_pin_chat_message_result", lambda **_: "ok")
    message = _message(text="/pinchatmessage -100123 55 loud", chat_id=42)

    await commands.cmd_pin_chat_message(message)

    commands.perform_pin_chat_message.assert_awaited_once_with(
        message.bot,
        chat_id=-100123,
        message_id=55,
        disable_notification=False,
    )
    message.answer.assert_awaited_once_with("ok", parse_mode="HTML")


async def test_cmd_pin_chat_message_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(
        method=PinChatMessage(chat_id=-100123, message_id=55),
        message="Bad Request: CHAT_ADMIN_REQUIRED",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_pin_chat_message", AsyncMock(side_effect=error)
    )
    message = _message(text="/pinchatmessage -100123 55", chat_id=42)

    await commands.cmd_pin_chat_message(message)

    args, _ = message.answer.await_args
    assert "Could not pin the chat message" in args[0]
    assert "CHAT_ADMIN_REQUIRED" in args[0]


def test_parse_pin_chat_message_args_required_only():
    assert commands._parse_pin_chat_message_args("/pinchatmessage -100123 55") == (
        -100123,
        55,
        None,
    )


def test_parse_pin_chat_message_args_silent_aliases():
    for flag in ("silent", "silent=true", "disable_notification=true"):
        assert commands._parse_pin_chat_message_args(
            f"/pinchatmessage -100123 55 {flag}"
        ) == (-100123, 55, True)


def test_parse_pin_chat_message_args_loud_aliases():
    for flag in ("loud", "silent=false", "disable_notification=false"):
        assert commands._parse_pin_chat_message_args(
            f"/pinchatmessage -100123 55 {flag}"
        ) == (-100123, 55, False)


def test_parse_pin_chat_message_args_invalid_chat_id():
    assert commands._parse_pin_chat_message_args("/pinchatmessage chat 55") is None


def test_parse_pin_chat_message_args_invalid_message_id():
    assert commands._parse_pin_chat_message_args("/pinchatmessage -100123 0") is None


def test_parse_pin_chat_message_args_invalid_notification_flag():
    assert (
        commands._parse_pin_chat_message_args("/pinchatmessage -100123 55 maybe")
        is None
    )
