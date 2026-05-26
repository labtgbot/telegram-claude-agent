from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import GetChatMemberCount

from bot.handlers import commands
from bot.services.get_chat_member_count import (
    format_get_chat_member_count_result,
    perform_get_chat_member_count,
)


def _message(text: str = "/getchatmembercount", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_perform_get_chat_member_count_uses_typed_aiogram_api():
    bot = SimpleNamespace(get_chat_member_count=AsyncMock(return_value=128))

    result = await perform_get_chat_member_count(bot, chat_id=-100123)

    assert result == 128
    bot.get_chat_member_count.assert_awaited_once_with(chat_id=-100123)


async def test_perform_get_chat_member_count_reraises_bad_request():
    error = TelegramBadRequest(
        method=GetChatMemberCount(chat_id=-100123),
        message="Bad Request: chat not found",
    )
    bot = SimpleNamespace(get_chat_member_count=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_get_chat_member_count(bot, chat_id=-100123)


async def test_perform_get_chat_member_count_reraises_forbidden():
    error = TelegramForbiddenError(
        method=GetChatMemberCount(chat_id=-100123),
        message="Forbidden: bot is not a member",
    )
    bot = SimpleNamespace(get_chat_member_count=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_get_chat_member_count(bot, chat_id=-100123)


def test_format_get_chat_member_count_result_escapes_values():
    text = format_get_chat_member_count_result(chat_id="-100<&>", member_count=128)

    assert "getChatMemberCount" in text
    assert "-100&lt;&amp;&gt;" in text
    assert "128" in text


async def test_cmd_get_chat_member_count_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_get_chat_member_count", AsyncMock())
    message = _message(text="/getchatmembercount -100123", chat_id=42)

    await commands.cmd_get_chat_member_count(message)

    commands.perform_get_chat_member_count.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_get_chat_member_count_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_get_chat_member_count", AsyncMock())
    message = _message(text="/getchatmembercount", chat_id=42)

    await commands.cmd_get_chat_member_count(message)

    commands.perform_get_chat_member_count.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "getchatmembercount usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_get_chat_member_count_calls_service(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_get_chat_member_count", AsyncMock(return_value=128))
    monkeypatch.setattr(
        commands,
        "format_get_chat_member_count_result",
        lambda chat_id, count: "ok",
    )
    message = _message(text="/getchatmembercount -100123", chat_id=42)

    await commands.cmd_get_chat_member_count(message)

    commands.perform_get_chat_member_count.assert_awaited_once_with(
        message.bot,
        chat_id=-100123,
    )
    args, kwargs = message.answer.await_args
    assert args[0] == "ok"
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_get_chat_member_count_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(
        method=GetChatMemberCount(chat_id=-100123),
        message="Bad Request: chat not found",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_get_chat_member_count", AsyncMock(side_effect=error))
    message = _message(text="/getchatmembercount -100123", chat_id=42)

    await commands.cmd_get_chat_member_count(message)

    args, _kwargs = message.answer.await_args
    assert "Could not get chat member count" in args[0]


def test_parse_get_chat_member_count_args():
    assert commands._parse_get_chat_member_count_args("/getchatmembercount -100123") == -100123


def test_parse_get_chat_member_count_args_rejects_invalid_input():
    assert commands._parse_get_chat_member_count_args("/getchatmembercount") is None
    assert commands._parse_get_chat_member_count_args("/getchatmembercount nope") is None
    assert commands._parse_get_chat_member_count_args("/getchatmembercount -100123 extra") is None
