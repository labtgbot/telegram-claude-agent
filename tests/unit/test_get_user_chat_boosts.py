from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import GetUserChatBoosts

from bot.handlers import commands
from bot.services.get_user_chat_boosts import (
    format_get_user_chat_boosts_result,
    perform_get_user_chat_boosts,
)


def _message(text: str = "/userchatboosts", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_perform_get_user_chat_boosts_uses_typed_aiogram_api():
    boosts = SimpleNamespace(boosts=[SimpleNamespace(boost_id="boost-1")])
    bot = SimpleNamespace(get_user_chat_boosts=AsyncMock(return_value=boosts))

    result = await perform_get_user_chat_boosts(
        bot,
        chat_id=-100123,
        user_id=456,
    )

    assert result is boosts
    bot.get_user_chat_boosts.assert_awaited_once_with(
        chat_id=-100123,
        user_id=456,
    )


async def test_perform_get_user_chat_boosts_reraises_bad_request():
    error = TelegramBadRequest(
        method=GetUserChatBoosts(chat_id=-100123, user_id=456),
        message="Bad Request: chat not found",
    )
    bot = SimpleNamespace(get_user_chat_boosts=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_get_user_chat_boosts(bot, chat_id=-100123, user_id=456)


async def test_perform_get_user_chat_boosts_reraises_forbidden():
    error = TelegramForbiddenError(
        method=GetUserChatBoosts(chat_id=-100123, user_id=456),
        message="Forbidden: not enough rights",
    )
    bot = SimpleNamespace(get_user_chat_boosts=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_get_user_chat_boosts(bot, chat_id=-100123, user_id=456)


def test_format_get_user_chat_boosts_result_escapes_values():
    boosts = SimpleNamespace(
        boosts=[
            SimpleNamespace(
                boost_id="boost<&>",
                add_date="2026-05-26T00:00:00+00:00",
                expiration_date="2026-06-26T00:00:00+00:00",
                source=SimpleNamespace(source="premium<&>"),
            )
        ]
    )

    text = format_get_user_chat_boosts_result(
        chat_id="@ops<&>",
        user_id="456<&>",
        boosts=boosts,
    )

    assert "getUserChatBoosts" in text
    assert "@ops&lt;&amp;&gt;" in text
    assert "456&lt;&amp;&gt;" in text
    assert "Boosts: 1" in text
    assert "boost&lt;&amp;&gt;" in text
    assert "premium&lt;&amp;&gt;" in text
    assert "expiration_date" in text


async def test_cmd_get_user_chat_boosts_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_get_user_chat_boosts", AsyncMock())
    message = _message(text="/userchatboosts -100123 456", chat_id=42)

    await commands.cmd_get_user_chat_boosts(message)

    commands.perform_get_user_chat_boosts.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_get_user_chat_boosts_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_get_user_chat_boosts", AsyncMock())
    message = _message(text="/userchatboosts", chat_id=42)

    await commands.cmd_get_user_chat_boosts(message)

    commands.perform_get_user_chat_boosts.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "userchatboosts usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_get_user_chat_boosts_calls_service(monkeypatch):
    boosts = SimpleNamespace(boosts=[])
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_get_user_chat_boosts",
        AsyncMock(return_value=boosts),
    )
    monkeypatch.setattr(
        commands,
        "format_get_user_chat_boosts_result",
        lambda chat_id, user_id, boosts: "ok",
    )
    message = _message(text="/userchatboosts -100123 456", chat_id=42)

    await commands.cmd_get_user_chat_boosts(message)

    commands.perform_get_user_chat_boosts.assert_awaited_once_with(
        message.bot,
        chat_id=-100123,
        user_id=456,
    )
    args, kwargs = message.answer.await_args
    assert args[0] == "ok"
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_get_user_chat_boosts_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(
        method=GetUserChatBoosts(chat_id=-100123, user_id=456),
        message="Bad Request: chat not found",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_get_user_chat_boosts",
        AsyncMock(side_effect=error),
    )
    message = _message(text="/userchatboosts -100123 456", chat_id=42)

    await commands.cmd_get_user_chat_boosts(message)

    args, _kwargs = message.answer.await_args
    assert "Could not get user chat boosts" in args[0]


def test_parse_get_user_chat_boosts_args():
    assert commands._parse_get_user_chat_boosts_args(
        "/userchatboosts -100123 456"
    ) == (-100123, 456)
    assert commands._parse_get_user_chat_boosts_args(
        "/userchatboosts @channel 456"
    ) == ("@channel", 456)


def test_parse_get_user_chat_boosts_args_rejects_invalid_input():
    assert commands._parse_get_user_chat_boosts_args("/userchatboosts") is None
    assert (
        commands._parse_get_user_chat_boosts_args("/userchatboosts nope 456")
        is None
    )
    assert (
        commands._parse_get_user_chat_boosts_args("/userchatboosts -100123 nope")
        is None
    )
    assert (
        commands._parse_get_user_chat_boosts_args(
            "/userchatboosts -100123 456 extra"
        )
        is None
    )
