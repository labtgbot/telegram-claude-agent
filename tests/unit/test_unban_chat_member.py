from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import UnbanChatMember

from bot.handlers import commands
from bot.services.unban_chat_member import (
    format_unban_result,
    perform_unban_chat_member,
)


def _message(text: str = "/unbanchatmember", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_perform_unban_chat_member_uses_typed_aiogram_api():
    bot = SimpleNamespace(unban_chat_member=AsyncMock(return_value=True))

    result = await perform_unban_chat_member(bot, chat_id=-100123, user_id=456)

    assert result is True
    bot.unban_chat_member.assert_awaited_once_with(
        chat_id=-100123,
        user_id=456,
        only_if_banned=None,
    )


async def test_perform_unban_chat_member_passes_only_if_banned():
    bot = SimpleNamespace(unban_chat_member=AsyncMock(return_value=True))

    await perform_unban_chat_member(
        bot, chat_id=-100123, user_id=456, only_if_banned=True
    )

    bot.unban_chat_member.assert_awaited_once_with(
        chat_id=-100123,
        user_id=456,
        only_if_banned=True,
    )


async def test_perform_unban_chat_member_reraises_bad_request():
    error = TelegramBadRequest(
        method=UnbanChatMember(chat_id=-100123, user_id=1),
        message="Bad Request: USER_NOT_PARTICIPANT",
    )
    bot = SimpleNamespace(unban_chat_member=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_unban_chat_member(bot, chat_id=-100123, user_id=1)


async def test_perform_unban_chat_member_reraises_forbidden():
    error = TelegramForbiddenError(
        method=UnbanChatMember(chat_id=-100123, user_id=2),
        message="Forbidden: bot is not an administrator",
    )
    bot = SimpleNamespace(unban_chat_member=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_unban_chat_member(bot, chat_id=-100123, user_id=2)


def test_format_unban_result_default():
    text = format_unban_result(chat_id=-100123, user_id=456, only_if_banned=None)
    assert "unbanChatMember" in text
    assert "-100123" in text
    assert "456" in text
    assert "unbanned successfully" in text
    assert "Only if banned" not in text


def test_format_unban_result_only_if_banned_true():
    text = format_unban_result(chat_id=-100123, user_id=456, only_if_banned=True)
    assert "Only if banned: yes" in text


def test_format_unban_result_only_if_banned_false():
    text = format_unban_result(chat_id=-100123, user_id=456, only_if_banned=False)
    assert "Only if banned: no" in text


async def test_cmd_unban_chat_member_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_unban_chat_member", AsyncMock())
    message = _message(text="/unbanchatmember -100123 456", chat_id=42)

    await commands.cmd_unban_chat_member(message)

    commands.perform_unban_chat_member.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_unban_chat_member_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_unban_chat_member", AsyncMock())
    message = _message(text="/unbanchatmember", chat_id=42)

    await commands.cmd_unban_chat_member(message)

    commands.perform_unban_chat_member.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "unbanchatmember usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_unban_chat_member_shows_usage_on_invalid_chat_id(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_unban_chat_member", AsyncMock())
    message = _message(text="/unbanchatmember notanumber 456", chat_id=42)

    await commands.cmd_unban_chat_member(message)

    commands.perform_unban_chat_member.assert_not_awaited()
    args, _ = message.answer.await_args
    assert "unbanchatmember usage" in args[0]


async def test_cmd_unban_chat_member_shows_usage_on_invalid_user_id(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_unban_chat_member", AsyncMock())
    message = _message(text="/unbanchatmember -100123 notanumber", chat_id=42)

    await commands.cmd_unban_chat_member(message)

    commands.perform_unban_chat_member.assert_not_awaited()
    args, _ = message.answer.await_args
    assert "unbanchatmember usage" in args[0]


async def test_cmd_unban_chat_member_shows_usage_on_invalid_only_flag(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_unban_chat_member", AsyncMock())
    message = _message(text="/unbanchatmember -100123 456 only_if_banned=maybe", chat_id=42)

    await commands.cmd_unban_chat_member(message)

    commands.perform_unban_chat_member.assert_not_awaited()
    args, _ = message.answer.await_args
    assert "unbanchatmember usage" in args[0]


async def test_cmd_unban_chat_member_calls_service_with_required_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_unban_chat_member", AsyncMock(return_value=True)
    )
    monkeypatch.setattr(
        commands,
        "format_unban_result",
        lambda chat_id, user_id, only_if_banned: "ok",
    )
    message = _message(text="/unbanchatmember -100123 456", chat_id=42)

    await commands.cmd_unban_chat_member(message)

    commands.perform_unban_chat_member.assert_awaited_once_with(
        message.bot,
        chat_id=-100123,
        user_id=456,
        only_if_banned=None,
    )
    args, kwargs = message.answer.await_args
    assert "ok" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_unban_chat_member_passes_only_if_banned_true(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_unban_chat_member", AsyncMock(return_value=True)
    )
    monkeypatch.setattr(
        commands,
        "format_unban_result",
        lambda chat_id, user_id, only_if_banned: "ok",
    )
    message = _message(text="/unbanchatmember -100123 456 only_if_banned=true", chat_id=42)

    await commands.cmd_unban_chat_member(message)

    call_kwargs = commands.perform_unban_chat_member.await_args.kwargs
    assert call_kwargs["only_if_banned"] is True


async def test_cmd_unban_chat_member_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(
        method=UnbanChatMember(chat_id=-100123, user_id=1),
        message="Bad Request: USER_NOT_PARTICIPANT",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_unban_chat_member", AsyncMock(side_effect=error)
    )
    message = _message(text="/unbanchatmember -100123 1", chat_id=42)

    await commands.cmd_unban_chat_member(message)

    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Could not unban the user" in args[0]


def test_parse_unban_chat_member_args_no_args():
    assert commands._parse_unban_chat_member_args("/unbanchatmember") is None


def test_parse_unban_chat_member_args_only_chat_id():
    assert commands._parse_unban_chat_member_args("/unbanchatmember -100123") is None


def test_parse_unban_chat_member_args_required_only():
    result = commands._parse_unban_chat_member_args("/unbanchatmember -100123 456")
    assert result == (-100123, 456, None)


def test_parse_unban_chat_member_args_with_only_if_banned_true():
    result = commands._parse_unban_chat_member_args(
        "/unbanchatmember -100123 456 only_if_banned=true"
    )
    assert result == (-100123, 456, True)


def test_parse_unban_chat_member_args_with_only_if_banned_false():
    result = commands._parse_unban_chat_member_args(
        "/unbanchatmember -100123 456 only_if_banned=false"
    )
    assert result == (-100123, 456, False)


def test_parse_unban_chat_member_args_invalid_chat_id():
    assert commands._parse_unban_chat_member_args("/unbanchatmember bad 456") is None


def test_parse_unban_chat_member_args_invalid_user_id():
    assert commands._parse_unban_chat_member_args("/unbanchatmember -100123 bad") is None


def test_parse_unban_chat_member_args_invalid_only_if_banned_flag():
    assert (
        commands._parse_unban_chat_member_args(
            "/unbanchatmember -100123 456 only_if_banned=maybe"
        )
        is None
    )
