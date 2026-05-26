from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import UnpinChatMessage

from bot.handlers import commands
from bot.services.unpin_chat_message import (
    format_unpin_chat_message_result,
    perform_unpin_chat_message,
)


def _message(text: str = "/unpinchatmessage", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_perform_unpin_chat_message_uses_typed_aiogram_api():
    bot = SimpleNamespace(unpin_chat_message=AsyncMock(return_value=True))

    result = await perform_unpin_chat_message(
        bot,
        chat_id=-100123,
        message_id=55,
    )

    assert result is True
    bot.unpin_chat_message.assert_awaited_once_with(
        chat_id=-100123,
        message_id=55,
    )


async def test_perform_unpin_chat_message_allows_omitted_message_id():
    bot = SimpleNamespace(unpin_chat_message=AsyncMock(return_value=True))

    result = await perform_unpin_chat_message(bot, chat_id=-100123)

    assert result is True
    bot.unpin_chat_message.assert_awaited_once_with(
        chat_id=-100123,
        message_id=None,
    )


async def test_perform_unpin_chat_message_reraises_bad_request():
    error = TelegramBadRequest(
        method=UnpinChatMessage(chat_id=-100123, message_id=55),
        message="Bad Request: message to unpin not found",
    )
    bot = SimpleNamespace(unpin_chat_message=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_unpin_chat_message(
            bot,
            chat_id=-100123,
            message_id=55,
        )


async def test_perform_unpin_chat_message_reraises_forbidden():
    error = TelegramForbiddenError(
        method=UnpinChatMessage(chat_id=-100123, message_id=55),
        message="Forbidden: bot is not an administrator",
    )
    bot = SimpleNamespace(unpin_chat_message=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_unpin_chat_message(
            bot,
            chat_id=-100123,
            message_id=55,
        )


def test_format_unpin_chat_message_result_with_message_id():
    text = format_unpin_chat_message_result(chat_id=-100123, message_id=55)

    assert "unpinChatMessage" in text
    assert "-100123" in text
    assert "55" in text
    assert "chat message unpinned" in text


def test_format_unpin_chat_message_result_without_message_id():
    text = format_unpin_chat_message_result(chat_id=-100123)

    assert "unpinChatMessage" in text
    assert "most recent pinned message" in text


async def test_cmd_unpin_chat_message_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_unpin_chat_message", AsyncMock())
    message = _message(text="/unpinchatmessage -100123 55", chat_id=42)

    await commands.cmd_unpin_chat_message(message)

    commands.perform_unpin_chat_message.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_unpin_chat_message_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_unpin_chat_message", AsyncMock())
    message = _message(text="/unpinchatmessage", chat_id=42)

    await commands.cmd_unpin_chat_message(message)

    commands.perform_unpin_chat_message.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "unpinchatmessage usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_unpin_chat_message_calls_service(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_unpin_chat_message", AsyncMock(return_value=True)
    )
    monkeypatch.setattr(commands, "format_unpin_chat_message_result", lambda **_: "ok")
    message = _message(text="/unpinchatmessage -100123 55", chat_id=42)

    await commands.cmd_unpin_chat_message(message)

    commands.perform_unpin_chat_message.assert_awaited_once_with(
        message.bot,
        chat_id=-100123,
        message_id=55,
    )
    message.answer.assert_awaited_once_with("ok", parse_mode="HTML")


async def test_cmd_unpin_chat_message_calls_service_without_message_id(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_unpin_chat_message", AsyncMock(return_value=True)
    )
    monkeypatch.setattr(commands, "format_unpin_chat_message_result", lambda **_: "ok")
    message = _message(text="/unpinchatmessage -100123", chat_id=42)

    await commands.cmd_unpin_chat_message(message)

    commands.perform_unpin_chat_message.assert_awaited_once_with(
        message.bot,
        chat_id=-100123,
        message_id=None,
    )
    message.answer.assert_awaited_once_with("ok", parse_mode="HTML")


async def test_cmd_unpin_chat_message_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(
        method=UnpinChatMessage(chat_id=-100123, message_id=55),
        message="Bad Request: CHAT_ADMIN_REQUIRED",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_unpin_chat_message", AsyncMock(side_effect=error)
    )
    message = _message(text="/unpinchatmessage -100123 55", chat_id=42)

    await commands.cmd_unpin_chat_message(message)

    args, _ = message.answer.await_args
    assert "Could not unpin the chat message" in args[0]
    assert "CHAT_ADMIN_REQUIRED" in args[0]


def test_parse_unpin_chat_message_args_required_only():
    assert commands._parse_unpin_chat_message_args("/unpinchatmessage -100123") == (
        -100123,
        None,
    )


def test_parse_unpin_chat_message_args_with_message_id():
    assert commands._parse_unpin_chat_message_args("/unpinchatmessage -100123 55") == (
        -100123,
        55,
    )


def test_parse_unpin_chat_message_args_invalid_chat_id():
    assert commands._parse_unpin_chat_message_args("/unpinchatmessage chat 55") is None


def test_parse_unpin_chat_message_args_invalid_message_id():
    assert commands._parse_unpin_chat_message_args("/unpinchatmessage -100123 0") is None
