from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import LeaveChat

from bot.handlers import commands
from bot.services.leave_chat import format_leave_chat_result, perform_leave_chat


def _message(text: str = "/leavechat", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_perform_leave_chat_uses_typed_aiogram_api():
    bot = SimpleNamespace(leave_chat=AsyncMock(return_value=True))

    result = await perform_leave_chat(bot, chat_id=-100123)

    assert result is True
    bot.leave_chat.assert_awaited_once_with(chat_id=-100123)


async def test_perform_leave_chat_reraises_bad_request():
    error = TelegramBadRequest(
        method=LeaveChat(chat_id=-100123),
        message="Bad Request: chat not found",
    )
    bot = SimpleNamespace(leave_chat=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_leave_chat(bot, chat_id=-100123)


async def test_perform_leave_chat_reraises_forbidden():
    error = TelegramForbiddenError(
        method=LeaveChat(chat_id=-100123),
        message="Forbidden: bot was kicked from the chat",
    )
    bot = SimpleNamespace(leave_chat=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_leave_chat(bot, chat_id=-100123)


def test_format_leave_chat_result_escapes_values():
    text = format_leave_chat_result(chat_id=-100123)

    assert "leaveChat" in text
    assert "-100123" in text
    assert "left the chat successfully" in text
    assert "Rollback" in text


async def test_cmd_leave_chat_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_leave_chat", AsyncMock())
    message = _message(text="/leavechat -100123 confirm", chat_id=42)

    await commands.cmd_leave_chat(message)

    commands.perform_leave_chat.assert_not_awaited()
    message.answer.assert_awaited_once_with("This command is restricted to admin chats.")


async def test_cmd_leave_chat_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_leave_chat", AsyncMock())
    message = _message(text="/leavechat", chat_id=42)

    await commands.cmd_leave_chat(message)

    commands.perform_leave_chat.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "leavechat usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_leave_chat_requires_confirmation(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_leave_chat", AsyncMock())
    message = _message(text="/leavechat -100123", chat_id=42)

    await commands.cmd_leave_chat(message)

    commands.perform_leave_chat.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "leavechat confirmation required" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_leave_chat_calls_service_after_confirmation(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_leave_chat", AsyncMock(return_value=True))
    monkeypatch.setattr(commands, "format_leave_chat_result", lambda **kwargs: "ok")
    message = _message(text="/leavechat -100123 confirm", chat_id=42)

    await commands.cmd_leave_chat(message)

    commands.perform_leave_chat.assert_awaited_once_with(message.bot, chat_id=-100123)
    args, kwargs = message.answer.await_args
    assert args[0] == "ok"
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_leave_chat_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(
        method=LeaveChat(chat_id=-100123),
        message="Bad Request: chat not found",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_leave_chat", AsyncMock(side_effect=error))
    message = _message(text="/leavechat -100123 confirm", chat_id=42)

    await commands.cmd_leave_chat(message)

    args, _kwargs = message.answer.await_args
    assert "Could not leave the chat" in args[0]


def test_parse_leave_chat_args():
    assert commands._parse_leave_chat_args("/leavechat -100123 confirm") == (
        -100123,
        True,
    )
    assert commands._parse_leave_chat_args("/leavechat -100123") == (-100123, False)


def test_parse_leave_chat_args_rejects_invalid_input():
    assert commands._parse_leave_chat_args("/leavechat") is None
    assert commands._parse_leave_chat_args("/leavechat 0 confirm") is None
    assert commands._parse_leave_chat_args("/leavechat nope confirm") is None
    assert commands._parse_leave_chat_args("/leavechat -100123 yes") is None
    assert commands._parse_leave_chat_args("/leavechat -100123 confirm extra") is None
