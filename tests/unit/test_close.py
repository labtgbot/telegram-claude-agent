from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
from aiogram.methods import Close

from bot.handlers import commands
from bot.services.close import perform_close


async def test_perform_close_uses_typed_aiogram_api():
    bot = SimpleNamespace(close=AsyncMock(return_value=True))

    result = await perform_close(bot)

    assert result is True
    bot.close.assert_awaited_once_with()


async def test_perform_close_reraises_telegram_errors():
    error = TelegramBadRequest(method=Close(), message="Bad Request: failed")
    bot = SimpleNamespace(close=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_close(bot)


async def test_perform_close_reraises_retry_after():
    error = TelegramRetryAfter(
        method=Close(),
        message="Too Many Requests: retry after 600",
        retry_after=600,
    )
    bot = SimpleNamespace(close=AsyncMock(side_effect=error))

    with pytest.raises(TelegramRetryAfter):
        await perform_close(bot)


def _message(text: str = "/close", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_close_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_close", AsyncMock())
    message = _message(text="/close confirm")

    await commands.cmd_close(message)

    commands.perform_close.assert_not_awaited()
    message.answer.assert_awaited_once_with("This command is restricted to admin chats.")


async def test_cmd_close_requires_confirmation(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_close", AsyncMock(return_value=True))
    message = _message(text="/close", chat_id=42)

    await commands.cmd_close(message)

    commands.perform_close.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "confirmation required" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_close_performs_close_after_confirmation(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_close", AsyncMock(return_value=True))
    message = _message(text="/close confirm", chat_id=42)

    await commands.cmd_close(message)

    commands.perform_close.assert_awaited_once_with(message.bot)
    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Closed the bot instance" in args[0]


async def test_cmd_close_reports_telegram_errors(monkeypatch):
    error = TelegramRetryAfter(
        method=Close(),
        message="Too Many Requests: retry after 600",
        retry_after=600,
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_close", AsyncMock(side_effect=error))
    message = _message(text="/close confirm", chat_id=42)

    await commands.cmd_close(message)

    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Could not close the bot instance" in args[0]
