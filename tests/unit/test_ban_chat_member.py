from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import BanChatMember

from bot.handlers import commands
from bot.services.ban_chat_member import (
    format_ban_result,
    perform_ban_chat_member,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _message(text: str = "/banchatmember", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


# ---------------------------------------------------------------------------
# Service: perform_ban_chat_member
# ---------------------------------------------------------------------------


async def test_perform_ban_chat_member_uses_typed_aiogram_api():
    bot = SimpleNamespace(ban_chat_member=AsyncMock(return_value=True))

    result = await perform_ban_chat_member(bot, chat_id=-100123, user_id=456)

    assert result is True
    bot.ban_chat_member.assert_awaited_once_with(
        chat_id=-100123,
        user_id=456,
        until_date=None,
        revoke_messages=None,
    )


async def test_perform_ban_chat_member_passes_until_date():
    until = datetime(2030, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    bot = SimpleNamespace(ban_chat_member=AsyncMock(return_value=True))

    await perform_ban_chat_member(
        bot, chat_id=-100123, user_id=456, until_date=until
    )

    bot.ban_chat_member.assert_awaited_once_with(
        chat_id=-100123,
        user_id=456,
        until_date=until,
        revoke_messages=None,
    )


async def test_perform_ban_chat_member_passes_revoke_messages():
    bot = SimpleNamespace(ban_chat_member=AsyncMock(return_value=True))

    await perform_ban_chat_member(
        bot, chat_id=-100123, user_id=456, revoke_messages=True
    )

    bot.ban_chat_member.assert_awaited_once_with(
        chat_id=-100123,
        user_id=456,
        until_date=None,
        revoke_messages=True,
    )


async def test_perform_ban_chat_member_reraises_bad_request():
    error = TelegramBadRequest(
        method=BanChatMember(chat_id=-100123, user_id=1),
        message="Bad Request: USER_NOT_PARTICIPANT",
    )
    bot = SimpleNamespace(ban_chat_member=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_ban_chat_member(bot, chat_id=-100123, user_id=1)


async def test_perform_ban_chat_member_reraises_forbidden():
    error = TelegramForbiddenError(
        method=BanChatMember(chat_id=-100123, user_id=2),
        message="Forbidden: bot is not a member of the supergroup chat",
    )
    bot = SimpleNamespace(ban_chat_member=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_ban_chat_member(bot, chat_id=-100123, user_id=2)


# ---------------------------------------------------------------------------
# Service: format_ban_result
# ---------------------------------------------------------------------------


def test_format_ban_result_permanent_ban():
    text = format_ban_result(
        chat_id=-100123, user_id=456, until_date=None, revoke_messages=None
    )
    assert "banChatMember" in text
    assert "-100123" in text
    assert "456" in text
    assert "permanent" in text
    assert "banned successfully" in text


def test_format_ban_result_timed_ban():
    until = datetime(2030, 6, 15, 10, 0, 0, tzinfo=timezone.utc)
    text = format_ban_result(
        chat_id=-100123, user_id=789, until_date=until, revoke_messages=None
    )
    assert "2030-06-15" in text
    assert "10:00:00 UTC" in text
    assert "permanent" not in text


def test_format_ban_result_revoke_true():
    text = format_ban_result(
        chat_id=-100123, user_id=456, until_date=None, revoke_messages=True
    )
    assert "Messages revoked: yes" in text


def test_format_ban_result_revoke_false():
    text = format_ban_result(
        chat_id=-100123, user_id=456, until_date=None, revoke_messages=False
    )
    assert "Messages revoked: no" in text


def test_format_ban_result_revoke_none_omits_revoke_line():
    text = format_ban_result(
        chat_id=-100123, user_id=456, until_date=None, revoke_messages=None
    )
    assert "Messages revoked" not in text


def test_format_ban_result_escapes_ids():
    """chat_id and user_id values must be safely rendered in HTML."""
    text = format_ban_result(
        chat_id=-100123, user_id=456, until_date=None, revoke_messages=None
    )
    assert "-100123" in text
    assert "456" in text


# ---------------------------------------------------------------------------
# Handler: cmd_ban_chat_member — access control
# ---------------------------------------------------------------------------


async def test_cmd_ban_chat_member_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_ban_chat_member", AsyncMock())
    message = _message(text="/banchatmember -100123 456", chat_id=42)

    await commands.cmd_ban_chat_member(message)

    commands.perform_ban_chat_member.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


# ---------------------------------------------------------------------------
# Handler: cmd_ban_chat_member — validation
# ---------------------------------------------------------------------------


async def test_cmd_ban_chat_member_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_ban_chat_member", AsyncMock())
    message = _message(text="/banchatmember", chat_id=42)

    await commands.cmd_ban_chat_member(message)

    commands.perform_ban_chat_member.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "banchatmember usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_ban_chat_member_shows_usage_on_invalid_chat_id(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_ban_chat_member", AsyncMock())
    message = _message(text="/banchatmember notanumber 456", chat_id=42)

    await commands.cmd_ban_chat_member(message)

    commands.perform_ban_chat_member.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "banchatmember usage" in args[0]


async def test_cmd_ban_chat_member_shows_usage_on_invalid_user_id(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_ban_chat_member", AsyncMock())
    message = _message(text="/banchatmember -100123 notanumber", chat_id=42)

    await commands.cmd_ban_chat_member(message)

    commands.perform_ban_chat_member.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "banchatmember usage" in args[0]


async def test_cmd_ban_chat_member_shows_usage_on_invalid_revoke_flag(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_ban_chat_member", AsyncMock())
    message = _message(text="/banchatmember -100123 456 0 revoke=maybe", chat_id=42)

    await commands.cmd_ban_chat_member(message)

    commands.perform_ban_chat_member.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "banchatmember usage" in args[0]


# ---------------------------------------------------------------------------
# Handler: cmd_ban_chat_member — successful calls
# ---------------------------------------------------------------------------


async def test_cmd_ban_chat_member_calls_service_with_required_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_ban_chat_member", AsyncMock(return_value=True)
    )
    monkeypatch.setattr(
        commands,
        "format_ban_result",
        lambda chat_id, user_id, until_date, revoke_messages: "ok",
    )
    message = _message(text="/banchatmember -100123 456", chat_id=42)

    await commands.cmd_ban_chat_member(message)

    commands.perform_ban_chat_member.assert_awaited_once_with(
        message.bot,
        chat_id=-100123,
        user_id=456,
        until_date=None,
        revoke_messages=None,
    )
    args, kwargs = message.answer.await_args
    assert "ok" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_ban_chat_member_passes_until_date(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_ban_chat_member", AsyncMock(return_value=True)
    )
    monkeypatch.setattr(
        commands,
        "format_ban_result",
        lambda chat_id, user_id, until_date, revoke_messages: "ok",
    )
    # Unix timestamp 1893456000 = 2030-01-01 00:00:00 UTC
    message = _message(text="/banchatmember -100123 456 1893456000", chat_id=42)

    await commands.cmd_ban_chat_member(message)

    call_kwargs = commands.perform_ban_chat_member.await_args.kwargs
    assert call_kwargs["until_date"] is not None
    assert call_kwargs["until_date"].year == 2030


async def test_cmd_ban_chat_member_passes_revoke_true(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_ban_chat_member", AsyncMock(return_value=True)
    )
    monkeypatch.setattr(
        commands,
        "format_ban_result",
        lambda chat_id, user_id, until_date, revoke_messages: "ok",
    )
    message = _message(text="/banchatmember -100123 456 0 revoke=true", chat_id=42)

    await commands.cmd_ban_chat_member(message)

    call_kwargs = commands.perform_ban_chat_member.await_args.kwargs
    assert call_kwargs["revoke_messages"] is True


async def test_cmd_ban_chat_member_passes_revoke_false(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_ban_chat_member", AsyncMock(return_value=True)
    )
    monkeypatch.setattr(
        commands,
        "format_ban_result",
        lambda chat_id, user_id, until_date, revoke_messages: "ok",
    )
    message = _message(text="/banchatmember -100123 456 0 revoke=false", chat_id=42)

    await commands.cmd_ban_chat_member(message)

    call_kwargs = commands.perform_ban_chat_member.await_args.kwargs
    assert call_kwargs["revoke_messages"] is False


# ---------------------------------------------------------------------------
# Handler: cmd_ban_chat_member — error handling
# ---------------------------------------------------------------------------


async def test_cmd_ban_chat_member_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(
        method=BanChatMember(chat_id=-100123, user_id=1),
        message="Bad Request: USER_NOT_PARTICIPANT",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_ban_chat_member", AsyncMock(side_effect=error)
    )
    message = _message(text="/banchatmember -100123 1", chat_id=42)

    await commands.cmd_ban_chat_member(message)

    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Could not ban the user" in args[0]


# ---------------------------------------------------------------------------
# Parser: _parse_ban_chat_member_args
# ---------------------------------------------------------------------------


def test_parse_ban_chat_member_args_no_args():
    assert commands._parse_ban_chat_member_args("/banchatmember") is None


def test_parse_ban_chat_member_args_only_chat_id():
    assert commands._parse_ban_chat_member_args("/banchatmember -100123") is None


def test_parse_ban_chat_member_args_required_only():
    result = commands._parse_ban_chat_member_args("/banchatmember -100123 456")
    assert result == (-100123, 456, None, None)


def test_parse_ban_chat_member_args_with_zero_until_date():
    result = commands._parse_ban_chat_member_args("/banchatmember -100123 456 0")
    assert result == (-100123, 456, None, None)


def test_parse_ban_chat_member_args_with_nonzero_until_date():
    result = commands._parse_ban_chat_member_args(
        "/banchatmember -100123 456 1893456000"
    )
    assert result is not None
    chat_id, user_id, until_date, revoke = result
    assert chat_id == -100123
    assert user_id == 456
    assert until_date is not None
    assert until_date.year == 2030
    assert revoke is None


def test_parse_ban_chat_member_args_with_revoke_true():
    result = commands._parse_ban_chat_member_args(
        "/banchatmember -100123 456 0 revoke=true"
    )
    assert result == (-100123, 456, None, True)


def test_parse_ban_chat_member_args_with_revoke_false():
    result = commands._parse_ban_chat_member_args(
        "/banchatmember -100123 456 0 revoke=false"
    )
    assert result == (-100123, 456, None, False)


def test_parse_ban_chat_member_args_invalid_chat_id():
    assert commands._parse_ban_chat_member_args("/banchatmember bad 456") is None


def test_parse_ban_chat_member_args_invalid_user_id():
    assert commands._parse_ban_chat_member_args("/banchatmember -100123 bad") is None


def test_parse_ban_chat_member_args_invalid_until_date():
    assert (
        commands._parse_ban_chat_member_args("/banchatmember -100123 456 notadate")
        is None
    )


def test_parse_ban_chat_member_args_invalid_revoke_flag():
    assert (
        commands._parse_ban_chat_member_args("/banchatmember -100123 456 0 revoke=maybe")
        is None
    )
