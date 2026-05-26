from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import GetChatMember

from bot.handlers import commands
from bot.services.get_chat_member import (
    format_get_chat_member_result,
    perform_get_chat_member,
)


def _message(text: str = "/getchatmember", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_perform_get_chat_member_uses_typed_aiogram_api():
    member = SimpleNamespace(
        status="member",
        user=SimpleNamespace(id=1, first_name="Alice"),
    )
    bot = SimpleNamespace(get_chat_member=AsyncMock(return_value=member))

    result = await perform_get_chat_member(bot, chat_id=-100123, user_id=1)

    assert result is member
    bot.get_chat_member.assert_awaited_once_with(chat_id=-100123, user_id=1)


async def test_perform_get_chat_member_reraises_bad_request():
    error = TelegramBadRequest(
        method=GetChatMember(chat_id=-100123, user_id=1),
        message="Bad Request: user not found",
    )
    bot = SimpleNamespace(get_chat_member=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_get_chat_member(bot, chat_id=-100123, user_id=1)


async def test_perform_get_chat_member_reraises_forbidden():
    error = TelegramForbiddenError(
        method=GetChatMember(chat_id=-100123, user_id=2),
        message="Forbidden: bot is not a member",
    )
    bot = SimpleNamespace(get_chat_member=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_get_chat_member(bot, chat_id=-100123, user_id=2)


def test_format_get_chat_member_result_escapes_values():
    member = SimpleNamespace(
        status="administrator",
        user=SimpleNamespace(
            id=1,
            first_name="Alice <Owner>",
            last_name="Root & Co",
            username="alice&root",
        ),
        custom_title="Lead <admin>",
        is_anonymous=True,
        can_manage_chat=True,
        can_delete_messages=True,
        can_restrict_members=None,
    )

    text = format_get_chat_member_result(
        chat_id="-100<&>",
        user_id="1<&>",
        member=member,
    )

    assert "getChatMember" in text
    assert "-100&lt;&amp;&gt;" in text
    assert "1&lt;&amp;&gt;" in text
    assert "administrator" in text
    assert "Alice &lt;Owner&gt; Root &amp; Co (@alice&amp;root)" in text
    assert "Lead &lt;admin&gt;" in text
    assert "anonymous" in text
    assert "can_delete_messages" in text


async def test_cmd_get_chat_member_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_get_chat_member", AsyncMock())
    message = _message(text="/getchatmember -100123 1", chat_id=42)

    await commands.cmd_get_chat_member(message)

    commands.perform_get_chat_member.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_get_chat_member_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_get_chat_member", AsyncMock())
    message = _message(text="/getchatmember", chat_id=42)

    await commands.cmd_get_chat_member(message)

    commands.perform_get_chat_member.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "getchatmember usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_get_chat_member_calls_service(monkeypatch):
    member = SimpleNamespace(status="member", user=SimpleNamespace(id=1))
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_get_chat_member",
        AsyncMock(return_value=member),
    )
    monkeypatch.setattr(
        commands,
        "format_get_chat_member_result",
        lambda chat_id, user_id, result: "ok",
    )
    message = _message(text="/getchatmember -100123 1", chat_id=42)

    await commands.cmd_get_chat_member(message)

    commands.perform_get_chat_member.assert_awaited_once_with(
        message.bot,
        chat_id=-100123,
        user_id=1,
    )
    args, kwargs = message.answer.await_args
    assert args[0] == "ok"
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_get_chat_member_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(
        method=GetChatMember(chat_id=-100123, user_id=1),
        message="Bad Request: user not found",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_get_chat_member",
        AsyncMock(side_effect=error),
    )
    message = _message(text="/getchatmember -100123 1", chat_id=42)

    await commands.cmd_get_chat_member(message)

    args, _kwargs = message.answer.await_args
    assert "Could not get chat member" in args[0]


def test_parse_get_chat_member_args():
    assert commands._parse_get_chat_member_args("/getchatmember -100123 1") == (
        -100123,
        1,
    )


def test_parse_get_chat_member_args_rejects_invalid_input():
    assert commands._parse_get_chat_member_args("/getchatmember") is None
    assert commands._parse_get_chat_member_args("/getchatmember nope 1") is None
    assert commands._parse_get_chat_member_args("/getchatmember -100123 nope") is None
    assert commands._parse_get_chat_member_args("/getchatmember -100123 1 extra") is None
