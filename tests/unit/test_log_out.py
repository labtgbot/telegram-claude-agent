from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import LogOut

from bot.handlers import commands
from bot.services.log_out import perform_log_out


async def test_perform_log_out_uses_typed_aiogram_api():
    bot = SimpleNamespace(log_out=AsyncMock(return_value=True))

    result = await perform_log_out(bot)

    assert result is True
    bot.log_out.assert_awaited_once_with()


async def test_perform_log_out_reraises_telegram_errors():
    error = TelegramBadRequest(method=LogOut(), message="Bad Request: failed")
    bot = SimpleNamespace(log_out=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_log_out(bot)


def _message(text: str = "/logout", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_log_out_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_log_out", AsyncMock())
    message = _message(text="/logout confirm")

    await commands.cmd_log_out(message)

    commands.perform_log_out.assert_not_awaited()
    message.answer.assert_awaited_once_with("This command is restricted to admin chats.")


async def test_cmd_log_out_requires_confirmation(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_log_out", AsyncMock(return_value=True))
    message = _message(text="/logout", chat_id=42)

    await commands.cmd_log_out(message)

    commands.perform_log_out.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "confirmation required" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_log_out_performs_log_out_after_confirmation(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_log_out", AsyncMock(return_value=True))
    message = _message(text="/logout confirm", chat_id=42)

    await commands.cmd_log_out(message)

    commands.perform_log_out.assert_awaited_once_with(message.bot)
    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Logged out from the cloud Bot API server" in args[0]


async def test_cmd_log_out_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(method=LogOut(), message="Bad Request: failed")
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_log_out", AsyncMock(side_effect=error))
    message = _message(text="/logout confirm", chat_id=42)

    await commands.cmd_log_out(message)

    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Could not log out from the cloud Bot API" in args[0]
