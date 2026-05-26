from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import RestrictChatMember
from aiogram.types import ChatPermissions

from bot.handlers import commands
from bot.services.restrict_chat_member import (
    format_restrict_result,
    perform_restrict_chat_member,
)


def _message(text: str = "/restrictchatmember", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_perform_restrict_chat_member_uses_typed_aiogram_api():
    bot = SimpleNamespace(restrict_chat_member=AsyncMock(return_value=True))
    permissions = ChatPermissions(can_send_messages=False)

    result = await perform_restrict_chat_member(
        bot, chat_id=-100123, user_id=456, permissions=permissions
    )

    assert result is True
    bot.restrict_chat_member.assert_awaited_once_with(
        chat_id=-100123,
        user_id=456,
        permissions=permissions,
        until_date=None,
        use_independent_chat_permissions=None,
    )


async def test_perform_restrict_chat_member_passes_optional_args():
    bot = SimpleNamespace(restrict_chat_member=AsyncMock(return_value=True))
    permissions = ChatPermissions(can_send_messages=True)
    until = datetime(2030, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    await perform_restrict_chat_member(
        bot,
        chat_id=-100123,
        user_id=456,
        permissions=permissions,
        until_date=until,
        use_independent_chat_permissions=True,
    )

    bot.restrict_chat_member.assert_awaited_once_with(
        chat_id=-100123,
        user_id=456,
        permissions=permissions,
        until_date=until,
        use_independent_chat_permissions=True,
    )


async def test_perform_restrict_chat_member_reraises_bad_request():
    permissions = ChatPermissions(can_send_messages=False)
    error = TelegramBadRequest(
        method=RestrictChatMember(
            chat_id=-100123, user_id=1, permissions=permissions
        ),
        message="Bad Request: USER_NOT_PARTICIPANT",
    )
    bot = SimpleNamespace(restrict_chat_member=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_restrict_chat_member(
            bot, chat_id=-100123, user_id=1, permissions=permissions
        )


async def test_perform_restrict_chat_member_reraises_forbidden():
    permissions = ChatPermissions(can_send_messages=False)
    error = TelegramForbiddenError(
        method=RestrictChatMember(
            chat_id=-100123, user_id=2, permissions=permissions
        ),
        message="Forbidden: bot is not a member of the supergroup chat",
    )
    bot = SimpleNamespace(restrict_chat_member=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_restrict_chat_member(
            bot, chat_id=-100123, user_id=2, permissions=permissions
        )


def test_format_restrict_result_mute():
    text = format_restrict_result(
        chat_id=-100123,
        user_id=456,
        preset="mute",
        permissions=ChatPermissions(can_send_messages=False),
        until_date=None,
        use_independent_chat_permissions=None,
    )

    assert "restrictChatMember" in text
    assert "-100123" in text
    assert "456" in text
    assert "mute" in text
    assert "restricted successfully" in text


async def test_cmd_restrict_chat_member_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_restrict_chat_member", AsyncMock())
    message = _message(text="/restrictchatmember -100123 456 mute", chat_id=42)

    await commands.cmd_restrict_chat_member(message)

    commands.perform_restrict_chat_member.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_restrict_chat_member_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_restrict_chat_member", AsyncMock())
    message = _message(text="/restrictchatmember", chat_id=42)

    await commands.cmd_restrict_chat_member(message)

    commands.perform_restrict_chat_member.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "restrictchatmember usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_restrict_chat_member_calls_service(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_restrict_chat_member", AsyncMock(return_value=True)
    )
    monkeypatch.setattr(commands, "format_restrict_result", lambda **kwargs: "ok")
    message = _message(text="/restrictchatmember -100123 456 mute", chat_id=42)

    await commands.cmd_restrict_chat_member(message)

    call_kwargs = commands.perform_restrict_chat_member.await_args.kwargs
    assert call_kwargs["chat_id"] == -100123
    assert call_kwargs["user_id"] == 456
    assert call_kwargs["permissions"].can_send_messages is False
    assert call_kwargs["until_date"] is None
    assert call_kwargs["use_independent_chat_permissions"] is None
    args, kwargs = message.answer.await_args
    assert args[0] == "ok"
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_restrict_chat_member_passes_until_and_independent(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_restrict_chat_member", AsyncMock(return_value=True)
    )
    monkeypatch.setattr(commands, "format_restrict_result", lambda **kwargs: "ok")
    message = _message(
        text="/restrictchatmember -100123 456 readonly 1893456000 independent=true",
        chat_id=42,
    )

    await commands.cmd_restrict_chat_member(message)

    call_kwargs = commands.perform_restrict_chat_member.await_args.kwargs
    assert call_kwargs["until_date"] == datetime(
        2030, 1, 1, 0, 0, 0, tzinfo=timezone.utc
    )
    assert call_kwargs["use_independent_chat_permissions"] is True


async def test_cmd_restrict_chat_member_reports_telegram_errors(monkeypatch):
    permissions = ChatPermissions(can_send_messages=False)
    error = TelegramBadRequest(
        method=RestrictChatMember(
            chat_id=-100123, user_id=1, permissions=permissions
        ),
        message="Bad Request: not enough rights",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_restrict_chat_member", AsyncMock(side_effect=error)
    )
    message = _message(text="/restrictchatmember -100123 1 mute", chat_id=42)

    await commands.cmd_restrict_chat_member(message)

    args, _kwargs = message.answer.await_args
    assert "Could not restrict the user" in args[0]


def test_parse_restrict_chat_member_args_required_only():
    result = commands._parse_restrict_chat_member_args(
        "/restrictchatmember -100123 456 mute"
    )

    chat_id, user_id, preset, permissions, until_date, independent = result
    assert chat_id == -100123
    assert user_id == 456
    assert preset == "mute"
    assert permissions.can_send_messages is False
    assert until_date is None
    assert independent is None


def test_parse_restrict_chat_member_args_readonly_preset():
    result = commands._parse_restrict_chat_member_args(
        "/restrictchatmember -100123 456 readonly"
    )

    assert result[3].can_send_messages is True
    assert result[3].can_send_polls is False
    assert result[3].can_add_web_page_previews is False


def test_parse_restrict_chat_member_args_invalid_preset():
    assert (
        commands._parse_restrict_chat_member_args(
            "/restrictchatmember -100123 456 unknown"
        )
        is None
    )


def test_parse_restrict_chat_member_args_invalid_independent_flag():
    assert (
        commands._parse_restrict_chat_member_args(
            "/restrictchatmember -100123 456 mute 0 independent=maybe"
        )
        is None
    )
