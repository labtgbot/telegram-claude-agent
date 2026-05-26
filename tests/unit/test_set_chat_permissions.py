from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import SetChatPermissions
from aiogram.types import ChatPermissions

from bot.handlers import commands
from bot.services.set_chat_permissions import (
    format_set_chat_permissions_result,
    perform_set_chat_permissions,
)


def _message(text: str = "/setchatpermissions", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_perform_set_chat_permissions_uses_typed_aiogram_api():
    bot = SimpleNamespace(set_chat_permissions=AsyncMock(return_value=True))
    permissions = ChatPermissions(can_send_messages=False)

    result = await perform_set_chat_permissions(
        bot, chat_id=-100123, permissions=permissions
    )

    assert result is True
    bot.set_chat_permissions.assert_awaited_once_with(
        chat_id=-100123,
        permissions=permissions,
        use_independent_chat_permissions=None,
    )


async def test_perform_set_chat_permissions_passes_independent_flag():
    bot = SimpleNamespace(set_chat_permissions=AsyncMock(return_value=True))
    permissions = ChatPermissions(can_send_messages=True)

    await perform_set_chat_permissions(
        bot,
        chat_id=-100123,
        permissions=permissions,
        use_independent_chat_permissions=True,
    )

    bot.set_chat_permissions.assert_awaited_once_with(
        chat_id=-100123,
        permissions=permissions,
        use_independent_chat_permissions=True,
    )


async def test_perform_set_chat_permissions_reraises_bad_request():
    permissions = ChatPermissions(can_send_messages=False)
    error = TelegramBadRequest(
        method=SetChatPermissions(chat_id=-100123, permissions=permissions),
        message="Bad Request: not enough rights",
    )
    bot = SimpleNamespace(set_chat_permissions=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_set_chat_permissions(
            bot, chat_id=-100123, permissions=permissions
        )


async def test_perform_set_chat_permissions_reraises_forbidden():
    permissions = ChatPermissions(can_send_messages=False)
    error = TelegramForbiddenError(
        method=SetChatPermissions(chat_id=-100123, permissions=permissions),
        message="Forbidden: bot is not a member of the supergroup chat",
    )
    bot = SimpleNamespace(set_chat_permissions=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_set_chat_permissions(
            bot, chat_id=-100123, permissions=permissions
        )


def test_format_set_chat_permissions_result():
    text = format_set_chat_permissions_result(
        chat_id=-100123,
        preset="closed",
        permissions=ChatPermissions(can_send_messages=False),
        use_independent_chat_permissions=False,
    )

    assert "setChatPermissions" in text
    assert "-100123" in text
    assert "closed" in text
    assert "Independent permissions: no" in text
    assert "default chat permissions updated" in text


async def test_cmd_set_chat_permissions_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_set_chat_permissions", AsyncMock())
    message = _message(text="/setchatpermissions -100123 closed", chat_id=42)

    await commands.cmd_set_chat_permissions(message)

    commands.perform_set_chat_permissions.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_set_chat_permissions_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_set_chat_permissions", AsyncMock())
    message = _message(text="/setchatpermissions", chat_id=42)

    await commands.cmd_set_chat_permissions(message)

    commands.perform_set_chat_permissions.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "setchatpermissions usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_set_chat_permissions_calls_service(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_set_chat_permissions", AsyncMock(return_value=True)
    )
    monkeypatch.setattr(
        commands, "format_set_chat_permissions_result", lambda **kwargs: "ok"
    )
    message = _message(text="/setchatpermissions -100123 open", chat_id=42)

    await commands.cmd_set_chat_permissions(message)

    call_kwargs = commands.perform_set_chat_permissions.await_args.kwargs
    assert call_kwargs["chat_id"] == -100123
    assert call_kwargs["permissions"].can_send_messages is True
    assert call_kwargs["use_independent_chat_permissions"] is None
    args, kwargs = message.answer.await_args
    assert args[0] == "ok"
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_set_chat_permissions_passes_independent(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_set_chat_permissions", AsyncMock(return_value=True)
    )
    monkeypatch.setattr(
        commands, "format_set_chat_permissions_result", lambda **kwargs: "ok"
    )
    message = _message(
        text="/setchatpermissions -100123 media independent=true", chat_id=42
    )

    await commands.cmd_set_chat_permissions(message)

    call_kwargs = commands.perform_set_chat_permissions.await_args.kwargs
    assert call_kwargs["permissions"].can_send_photos is True
    assert call_kwargs["use_independent_chat_permissions"] is True


async def test_cmd_set_chat_permissions_reports_telegram_errors(monkeypatch):
    permissions = ChatPermissions(can_send_messages=False)
    error = TelegramBadRequest(
        method=SetChatPermissions(chat_id=-100123, permissions=permissions),
        message="Bad Request: not enough rights",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_set_chat_permissions", AsyncMock(side_effect=error)
    )
    message = _message(text="/setchatpermissions -100123 closed", chat_id=42)

    await commands.cmd_set_chat_permissions(message)

    args, _kwargs = message.answer.await_args
    assert "Could not set chat permissions" in args[0]


def test_parse_set_chat_permissions_args_required_only():
    result = commands._parse_set_chat_permissions_args(
        "/setchatpermissions -100123 closed"
    )

    chat_id, preset, permissions, independent = result
    assert chat_id == -100123
    assert preset == "closed"
    assert permissions.can_send_messages is False
    assert independent is None


def test_parse_set_chat_permissions_args_open_preset():
    result = commands._parse_set_chat_permissions_args(
        "/setchatpermissions -100123 open"
    )

    assert result[2].can_send_messages is True
    assert result[2].can_invite_users is True
    assert result[2].can_manage_topics is True


def test_parse_set_chat_permissions_args_invalid_preset():
    assert (
        commands._parse_set_chat_permissions_args(
            "/setchatpermissions -100123 unknown"
        )
        is None
    )


def test_parse_set_chat_permissions_args_invalid_independent_flag():
    assert (
        commands._parse_set_chat_permissions_args(
            "/setchatpermissions -100123 open independent=maybe"
        )
        is None
    )
