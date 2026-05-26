from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import GetChatAdministrators

from bot.handlers import commands
from bot.services.get_chat_administrators import (
    format_get_chat_administrators_result,
    perform_get_chat_administrators,
)


def _message(text: str = "/getchatadministrators", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_perform_get_chat_administrators_uses_typed_aiogram_api():
    administrators = [
        SimpleNamespace(
            status="creator",
            user=SimpleNamespace(id=1, first_name="Owner", username="owner"),
            is_anonymous=False,
        )
    ]
    bot = SimpleNamespace(get_chat_administrators=AsyncMock(return_value=administrators))

    result = await perform_get_chat_administrators(bot, chat_id=-100123)

    assert result is administrators
    bot.get_chat_administrators.assert_awaited_once_with(chat_id=-100123)


async def test_perform_get_chat_administrators_reraises_bad_request():
    error = TelegramBadRequest(
        method=GetChatAdministrators(chat_id=-100123),
        message="Bad Request: chat not found",
    )
    bot = SimpleNamespace(get_chat_administrators=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_get_chat_administrators(bot, chat_id=-100123)


async def test_perform_get_chat_administrators_reraises_forbidden():
    error = TelegramForbiddenError(
        method=GetChatAdministrators(chat_id=-100123),
        message="Forbidden: bot is not an administrator",
    )
    bot = SimpleNamespace(get_chat_administrators=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_get_chat_administrators(bot, chat_id=-100123)


def test_format_get_chat_administrators_result_escapes_values():
    administrators = [
        SimpleNamespace(
            status="creator",
            user=SimpleNamespace(
                id=1,
                first_name="Alice <Owner>",
                last_name="Root & Co",
                username="alice&root",
            ),
            custom_title="Lead <admin>",
            is_anonymous=False,
            can_manage_chat=True,
            can_delete_messages=True,
            can_restrict_members=None,
        ),
        SimpleNamespace(
            status="administrator",
            user=SimpleNamespace(id=2, first_name="Hidden", username=None),
            is_anonymous=True,
        ),
    ]

    text = format_get_chat_administrators_result(
        chat_id="-100<&>",
        administrators=administrators,
    )

    assert "getChatAdministrators" in text
    assert "-100&lt;&amp;&gt;" in text
    assert "Administrators: 2" in text
    assert "Alice &lt;Owner&gt; Root &amp; Co (@alice&amp;root)" in text
    assert "Lead &lt;admin&gt;" in text
    assert "can_delete_messages" in text
    assert "anonymous" in text


async def test_cmd_get_chat_administrators_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_get_chat_administrators", AsyncMock())
    message = _message(text="/getchatadministrators -100123", chat_id=42)

    await commands.cmd_get_chat_administrators(message)

    commands.perform_get_chat_administrators.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_get_chat_administrators_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_get_chat_administrators", AsyncMock())
    message = _message(text="/getchatadministrators", chat_id=42)

    await commands.cmd_get_chat_administrators(message)

    commands.perform_get_chat_administrators.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "getchatadministrators usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_get_chat_administrators_calls_service(monkeypatch):
    administrators = [SimpleNamespace(status="creator", user=SimpleNamespace(id=1))]
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_get_chat_administrators",
        AsyncMock(return_value=administrators),
    )
    monkeypatch.setattr(
        commands,
        "format_get_chat_administrators_result",
        lambda chat_id, result: "ok",
    )
    message = _message(text="/getchatadministrators -100123", chat_id=42)

    await commands.cmd_get_chat_administrators(message)

    commands.perform_get_chat_administrators.assert_awaited_once_with(
        message.bot,
        chat_id=-100123,
    )
    args, kwargs = message.answer.await_args
    assert args[0] == "ok"
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_get_chat_administrators_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(
        method=GetChatAdministrators(chat_id=-100123),
        message="Bad Request: chat not found",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_get_chat_administrators",
        AsyncMock(side_effect=error),
    )
    message = _message(text="/getchatadministrators -100123", chat_id=42)

    await commands.cmd_get_chat_administrators(message)

    args, _kwargs = message.answer.await_args
    assert "Could not get chat administrators" in args[0]


def test_parse_get_chat_administrators_args():
    assert commands._parse_get_chat_administrators_args(
        "/getchatadministrators -100123"
    ) == -100123


def test_parse_get_chat_administrators_args_rejects_invalid_input():
    assert commands._parse_get_chat_administrators_args("/getchatadministrators") is None
    assert (
        commands._parse_get_chat_administrators_args("/getchatadministrators nope")
        is None
    )
    assert (
        commands._parse_get_chat_administrators_args(
            "/getchatadministrators -100123 extra"
        )
        is None
    )
