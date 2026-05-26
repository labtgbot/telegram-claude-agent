from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import GetUserPersonalChatMessages

from bot.handlers import commands
from bot.services.get_user_personal_chat_messages import (
    GET_USER_PERSONAL_CHAT_MESSAGES_MAX_LIMIT,
    GET_USER_PERSONAL_CHAT_MESSAGES_MIN_LIMIT,
    format_get_user_personal_chat_messages_result,
    perform_get_user_personal_chat_messages,
)


def _message(text: str = "/userpersonalchatmessages", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_perform_get_user_personal_chat_messages_uses_typed_aiogram_api():
    messages = [SimpleNamespace(message_id=10), SimpleNamespace(message_id=11)]
    bot = SimpleNamespace(
        get_user_personal_chat_messages=AsyncMock(return_value=messages)
    )

    result = await perform_get_user_personal_chat_messages(
        bot,
        user_id=123,
        limit=2,
    )

    assert result is messages
    bot.get_user_personal_chat_messages.assert_awaited_once_with(
        user_id=123,
        limit=2,
    )


async def test_perform_get_user_personal_chat_messages_reraises_bad_request():
    error = TelegramBadRequest(
        method=GetUserPersonalChatMessages(user_id=123, limit=10),
        message="Bad Request: user not found",
    )
    bot = SimpleNamespace(
        get_user_personal_chat_messages=AsyncMock(side_effect=error)
    )

    with pytest.raises(TelegramBadRequest):
        await perform_get_user_personal_chat_messages(bot, user_id=123, limit=10)


async def test_perform_get_user_personal_chat_messages_reraises_forbidden():
    error = TelegramForbiddenError(
        method=GetUserPersonalChatMessages(user_id=123, limit=10),
        message="Forbidden: not enough rights",
    )
    bot = SimpleNamespace(
        get_user_personal_chat_messages=AsyncMock(side_effect=error)
    )

    with pytest.raises(TelegramForbiddenError):
        await perform_get_user_personal_chat_messages(bot, user_id=123, limit=10)


async def test_perform_get_user_personal_chat_messages_validates_limit():
    bot = SimpleNamespace(get_user_personal_chat_messages=AsyncMock())

    with pytest.raises(ValueError, match="limit"):
        await perform_get_user_personal_chat_messages(
            bot,
            user_id=123,
            limit=GET_USER_PERSONAL_CHAT_MESSAGES_MAX_LIMIT + 1,
        )

    bot.get_user_personal_chat_messages.assert_not_awaited()


def test_format_get_user_personal_chat_messages_result_escapes_values():
    messages = [
        SimpleNamespace(
            message_id=10,
            chat=SimpleNamespace(id="-100<&>", type="supergroup", title="Ops <team>"),
            date="2026-05-26T00:00:00+00:00",
        ),
        SimpleNamespace(message_id=11, chat=None, date=None),
    ]

    text = format_get_user_personal_chat_messages_result(
        user_id="123<&>",
        limit=2,
        messages=messages,
    )

    assert "getUserPersonalChatMessages" in text
    assert "123&lt;&amp;&gt;" in text
    assert "Requested limit: 2" in text
    assert "Messages: 2" in text
    assert "Ops &lt;team&gt;" in text
    assert "-100&lt;&amp;&gt;" in text
    assert "message_id: 10" in text


async def test_cmd_get_user_personal_chat_messages_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_get_user_personal_chat_messages", AsyncMock())
    message = _message(text="/userpersonalchatmessages 123 10", chat_id=42)

    await commands.cmd_get_user_personal_chat_messages(message)

    commands.perform_get_user_personal_chat_messages.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_get_user_personal_chat_messages_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_get_user_personal_chat_messages", AsyncMock())
    message = _message(text="/userpersonalchatmessages", chat_id=42)

    await commands.cmd_get_user_personal_chat_messages(message)

    commands.perform_get_user_personal_chat_messages.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "userpersonalchatmessages usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_get_user_personal_chat_messages_calls_service(monkeypatch):
    messages = [SimpleNamespace(message_id=10)]
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_get_user_personal_chat_messages",
        AsyncMock(return_value=messages),
    )
    monkeypatch.setattr(
        commands,
        "format_get_user_personal_chat_messages_result",
        lambda user_id, limit, messages: "ok",
    )
    message = _message(text="/userpersonalchatmessages 123 5", chat_id=42)

    await commands.cmd_get_user_personal_chat_messages(message)

    commands.perform_get_user_personal_chat_messages.assert_awaited_once_with(
        message.bot,
        user_id=123,
        limit=5,
    )
    args, kwargs = message.answer.await_args
    assert args[0] == "ok"
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_get_user_personal_chat_messages_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(
        method=GetUserPersonalChatMessages(user_id=123, limit=10),
        message="Bad Request: user not found",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_get_user_personal_chat_messages",
        AsyncMock(side_effect=error),
    )
    message = _message(text="/userpersonalchatmessages 123 10", chat_id=42)

    await commands.cmd_get_user_personal_chat_messages(message)

    args, _kwargs = message.answer.await_args
    assert "Could not get user personal chat messages" in args[0]


def test_parse_get_user_personal_chat_messages_args():
    assert commands._parse_get_user_personal_chat_messages_args(
        "/userpersonalchatmessages 123 5"
    ) == (123, 5)


def test_parse_get_user_personal_chat_messages_args_uses_default_limit():
    assert commands._parse_get_user_personal_chat_messages_args(
        "/userpersonalchatmessages 123"
    ) == (123, GET_USER_PERSONAL_CHAT_MESSAGES_MAX_LIMIT)


def test_parse_get_user_personal_chat_messages_args_rejects_invalid_input():
    assert commands._parse_get_user_personal_chat_messages_args(
        "/userpersonalchatmessages"
    ) is None
    assert commands._parse_get_user_personal_chat_messages_args(
        "/userpersonalchatmessages nope"
    ) is None
    assert commands._parse_get_user_personal_chat_messages_args(
        f"/userpersonalchatmessages 123 {GET_USER_PERSONAL_CHAT_MESSAGES_MIN_LIMIT - 1}"
    ) is None
    assert commands._parse_get_user_personal_chat_messages_args(
        f"/userpersonalchatmessages 123 {GET_USER_PERSONAL_CHAT_MESSAGES_MAX_LIMIT + 1}"
    ) is None
    assert commands._parse_get_user_personal_chat_messages_args(
        "/userpersonalchatmessages 123 10 extra"
    ) is None
