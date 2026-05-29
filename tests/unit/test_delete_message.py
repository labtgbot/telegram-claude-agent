from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import DeleteMessage

from bot.handlers import commands
from bot.services.delete_message import (
    format_delete_message_result,
    perform_delete_message,
)


def _message(text: str = "/deletemessage", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_perform_delete_message_uses_typed_aiogram_api():
    bot = SimpleNamespace(delete_message=AsyncMock(return_value=True))

    result = await perform_delete_message(
        bot,
        chat_id=-100123,
        message_id=55,
    )

    assert result is True
    bot.delete_message.assert_awaited_once_with(
        chat_id=-100123,
        message_id=55,
    )


async def test_perform_delete_message_reraises_bad_request():
    error = TelegramBadRequest(
        method=DeleteMessage(chat_id=-100123, message_id=55),
        message="Bad Request: message can't be deleted",
    )
    bot = SimpleNamespace(delete_message=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_delete_message(
            bot,
            chat_id=-100123,
            message_id=55,
        )


async def test_perform_delete_message_reraises_forbidden():
    error = TelegramForbiddenError(
        method=DeleteMessage(chat_id=-100123, message_id=55),
        message="Forbidden: bot is not an administrator",
    )
    bot = SimpleNamespace(delete_message=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_delete_message(
            bot,
            chat_id=-100123,
            message_id=55,
        )


def test_format_delete_message_result():
    text = format_delete_message_result(chat_id=-100123, message_id=55)

    assert "deleteMessage" in text
    assert "-100123" in text
    assert "55" in text
    assert "message deleted" in text


def test_parse_delete_message_args():
    assert commands._parse_delete_message_args("/deletemessage -100123 55 confirm") == (
        -100123,
        55,
        True,
    )
    assert commands._parse_delete_message_args("/deletemessage -100123 55") == (
        -100123,
        55,
        False,
    )
    assert commands._parse_delete_message_args("/deletemessage") is None
    assert commands._parse_delete_message_args("/deletemessage -100123 not-int") is None
    assert commands._parse_delete_message_args("/deletemessage -100123 0 confirm") is None


async def test_cmd_delete_message_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_delete_message", AsyncMock())
    message = _message(text="/deletemessage -100123 55 confirm", chat_id=42)

    await commands.cmd_delete_message(message)

    commands.perform_delete_message.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_delete_message_requires_confirmation(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_delete_message", AsyncMock())
    message = _message(text="/deletemessage -100123 55", chat_id=42)

    await commands.cmd_delete_message(message)

    commands.perform_delete_message.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "deletemessage confirmation required" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_delete_message_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_delete_message", AsyncMock())
    message = _message(text="/deletemessage", chat_id=42)

    await commands.cmd_delete_message(message)

    commands.perform_delete_message.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "deletemessage usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_delete_message_calls_service(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_delete_message", AsyncMock(return_value=True))
    monkeypatch.setattr(commands, "format_delete_message_result", lambda **_: "ok")
    message = _message(text="/deletemessage -100123 55 confirm", chat_id=42)

    await commands.cmd_delete_message(message)

    commands.perform_delete_message.assert_awaited_once_with(
        message.bot,
        chat_id=-100123,
        message_id=55,
    )
    message.answer.assert_awaited_once_with("ok", parse_mode="HTML")


async def test_cmd_delete_message_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(
        method=DeleteMessage(chat_id=-100123, message_id=55),
        message="Bad Request: message can't be deleted",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_delete_message", AsyncMock(side_effect=error))
    message = _message(text="/deletemessage -100123 55 confirm", chat_id=42)

    await commands.cmd_delete_message(message)

    args, _ = message.answer.await_args
    assert "Could not delete the message" in args[0]
    assert "message can't be deleted" in args[0]
