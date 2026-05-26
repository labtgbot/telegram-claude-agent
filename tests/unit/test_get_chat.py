from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import GetChat

from bot.handlers import commands
from bot.services.get_chat import format_get_chat_result, perform_get_chat


def _message(text: str = "/getchat", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_perform_get_chat_uses_typed_aiogram_api():
    chat = SimpleNamespace(
        id=-100123,
        type="supergroup",
        title="Support",
        username="support_chat",
    )
    bot = SimpleNamespace(get_chat=AsyncMock(return_value=chat))

    result = await perform_get_chat(bot, chat_id=-100123)

    assert result is chat
    bot.get_chat.assert_awaited_once_with(chat_id=-100123)


async def test_perform_get_chat_reraises_bad_request():
    error = TelegramBadRequest(
        method=GetChat(chat_id=-100123),
        message="Bad Request: chat not found",
    )
    bot = SimpleNamespace(get_chat=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_get_chat(bot, chat_id=-100123)


async def test_perform_get_chat_reraises_forbidden():
    error = TelegramForbiddenError(
        method=GetChat(chat_id=-100123),
        message="Forbidden: bot is not a member",
    )
    bot = SimpleNamespace(get_chat=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_get_chat(bot, chat_id=-100123)


def test_format_get_chat_result_escapes_known_fields():
    chat = SimpleNamespace(
        id=-100123,
        type="supergroup",
        title="Support <ops>",
        username="support&ops",
        first_name=None,
        last_name=None,
        bio="Hello <team>",
        description="Description & rules",
        invite_link="https://t.me/+abc<&>",
    )

    text = format_get_chat_result(chat)

    assert "getChat" in text
    assert "-100123" in text
    assert "Support &lt;ops&gt;" in text
    assert "@support&amp;ops" in text
    assert "Hello &lt;team&gt;" in text
    assert "Description &amp; rules" in text
    assert "https://t.me/+abc&lt;&amp;&gt;" in text


async def test_cmd_get_chat_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_get_chat", AsyncMock())
    message = _message(text="/getchat -100123", chat_id=42)

    await commands.cmd_get_chat(message)

    commands.perform_get_chat.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_get_chat_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_get_chat", AsyncMock())
    message = _message(text="/getchat", chat_id=42)

    await commands.cmd_get_chat(message)

    commands.perform_get_chat.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "getchat usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_get_chat_calls_service(monkeypatch):
    chat = SimpleNamespace(id=-100123, type="supergroup")
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_get_chat", AsyncMock(return_value=chat))
    monkeypatch.setattr(commands, "format_get_chat_result", lambda result: "ok")
    message = _message(text="/getchat -100123", chat_id=42)

    await commands.cmd_get_chat(message)

    commands.perform_get_chat.assert_awaited_once_with(
        message.bot,
        chat_id=-100123,
    )
    args, kwargs = message.answer.await_args
    assert args[0] == "ok"
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_get_chat_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(
        method=GetChat(chat_id=-100123),
        message="Bad Request: chat not found",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_get_chat", AsyncMock(side_effect=error))
    message = _message(text="/getchat -100123", chat_id=42)

    await commands.cmd_get_chat(message)

    args, _kwargs = message.answer.await_args
    assert "Could not get chat information" in args[0]


def test_parse_get_chat_args():
    assert commands._parse_get_chat_args("/getchat -100123") == -100123


def test_parse_get_chat_args_rejects_invalid_input():
    assert commands._parse_get_chat_args("/getchat") is None
    assert commands._parse_get_chat_args("/getchat nope") is None
    assert commands._parse_get_chat_args("/getchat -100123 extra") is None
