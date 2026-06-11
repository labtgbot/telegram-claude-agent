from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import UnpinAllChatMessages

from bot.handlers import commands
from bot.services.unpin_all_chat_messages import (
    format_unpin_all_chat_messages_result,
    perform_unpin_all_chat_messages,
)


def _message(text: str = "/unpinallchatmessages", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_perform_unpin_all_chat_messages_uses_typed_aiogram_api():
    bot = SimpleNamespace(unpin_all_chat_messages=AsyncMock(return_value=True))

    result = await perform_unpin_all_chat_messages(bot, chat_id=-100123)

    assert result is True
    bot.unpin_all_chat_messages.assert_awaited_once_with(chat_id=-100123)


async def test_perform_unpin_all_chat_messages_reraises_bad_request():
    error = TelegramBadRequest(
        method=UnpinAllChatMessages(chat_id=-100123),
        message="Bad Request: chat not found",
    )
    bot = SimpleNamespace(unpin_all_chat_messages=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_unpin_all_chat_messages(bot, chat_id=-100123)


async def test_perform_unpin_all_chat_messages_reraises_forbidden():
    error = TelegramForbiddenError(
        method=UnpinAllChatMessages(chat_id=-100123),
        message="Forbidden: bot is not an administrator",
    )
    bot = SimpleNamespace(unpin_all_chat_messages=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_unpin_all_chat_messages(bot, chat_id=-100123)


def test_format_unpin_all_chat_messages_result():
    text = format_unpin_all_chat_messages_result(chat_id=-100123)

    assert "unpinAllChatMessages" in text
    assert "-100123" in text
    assert "all pinned chat messages unpinned" in text


async def test_cmd_unpin_all_chat_messages_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_unpin_all_chat_messages", AsyncMock())
    message = _message(text="/unpinallchatmessages -100123", chat_id=42)

    await commands.cmd_unpin_all_chat_messages(message)

    commands.perform_unpin_all_chat_messages.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_unpin_all_chat_messages_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_unpin_all_chat_messages", AsyncMock())
    message = _message(text="/unpinallchatmessages", chat_id=42)

    await commands.cmd_unpin_all_chat_messages(message)

    commands.perform_unpin_all_chat_messages.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "unpinallchatmessages usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_unpin_all_chat_messages_calls_service(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_unpin_all_chat_messages", AsyncMock(return_value=True)
    )
    monkeypatch.setattr(
        commands, "format_unpin_all_chat_messages_result", lambda **_: "ok"
    )
    message = _message(text="/unpinallchatmessages -100123", chat_id=42)

    await commands.cmd_unpin_all_chat_messages(message)

    commands.perform_unpin_all_chat_messages.assert_awaited_once_with(
        message.bot,
        chat_id=-100123,
    )
    message.answer.assert_awaited_once_with("ok", parse_mode="HTML")


async def test_cmd_unpin_all_chat_messages_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(
        method=UnpinAllChatMessages(chat_id=-100123),
        message="Bad Request: CHAT_ADMIN_REQUIRED",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_unpin_all_chat_messages", AsyncMock(side_effect=error)
    )
    message = _message(text="/unpinallchatmessages -100123", chat_id=42)

    await commands.cmd_unpin_all_chat_messages(message)

    args, _ = message.answer.await_args
    assert "Could not unpin all chat messages" in args[0]
    assert "CHAT_ADMIN_REQUIRED" not in args[0]
    assert "Please try again later" in args[0]


def test_parse_unpin_all_chat_messages_args():
    assert commands._parse_unpin_all_chat_messages_args(
        "/unpinallchatmessages -100123"
    ) == -100123


def test_parse_unpin_all_chat_messages_args_invalid_chat_id():
    assert commands._parse_unpin_all_chat_messages_args(
        "/unpinallchatmessages chat"
    ) is None


def test_parse_unpin_all_chat_messages_args_rejects_extra_args():
    assert commands._parse_unpin_all_chat_messages_args(
        "/unpinallchatmessages -100123 extra"
    ) is None
