from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import ExportChatInviteLink

from bot.handlers import commands
from bot.services.export_chat_invite_link import (
    format_export_chat_invite_link_result,
    perform_export_chat_invite_link,
)


def _message(text: str = "/exportchatinvitelink", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_perform_export_chat_invite_link_uses_typed_aiogram_api():
    bot = SimpleNamespace(
        export_chat_invite_link=AsyncMock(return_value="https://t.me/+abc123")
    )

    result = await perform_export_chat_invite_link(bot, chat_id=-100123)

    assert result == "https://t.me/+abc123"
    bot.export_chat_invite_link.assert_awaited_once_with(chat_id=-100123)


async def test_perform_export_chat_invite_link_reraises_bad_request():
    error = TelegramBadRequest(
        method=ExportChatInviteLink(chat_id=-100123),
        message="Bad Request: not enough rights",
    )
    bot = SimpleNamespace(export_chat_invite_link=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_export_chat_invite_link(bot, chat_id=-100123)


async def test_perform_export_chat_invite_link_reraises_forbidden():
    error = TelegramForbiddenError(
        method=ExportChatInviteLink(chat_id=-100123),
        message="Forbidden: bot is not an administrator",
    )
    bot = SimpleNamespace(export_chat_invite_link=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_export_chat_invite_link(bot, chat_id=-100123)


def test_format_export_chat_invite_link_result_escapes_values():
    text = format_export_chat_invite_link_result(
        chat_id=-100123,
        invite_link="https://t.me/+abc<&>",
    )

    assert "exportChatInviteLink" in text
    assert "-100123" in text
    assert "https://t.me/+abc&lt;&amp;&gt;" in text
    assert "previous primary invite link is revoked" in text


async def test_cmd_export_chat_invite_link_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_export_chat_invite_link", AsyncMock())
    message = _message(text="/exportchatinvitelink -100123", chat_id=42)

    await commands.cmd_export_chat_invite_link(message)

    commands.perform_export_chat_invite_link.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_export_chat_invite_link_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_export_chat_invite_link", AsyncMock())
    message = _message(text="/exportchatinvitelink", chat_id=42)

    await commands.cmd_export_chat_invite_link(message)

    commands.perform_export_chat_invite_link.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "exportchatinvitelink usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_export_chat_invite_link_calls_service(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_export_chat_invite_link",
        AsyncMock(return_value="https://t.me/+abc123"),
    )
    monkeypatch.setattr(
        commands,
        "format_export_chat_invite_link_result",
        lambda **kwargs: "ok",
    )
    message = _message(text="/exportchatinvitelink -100123", chat_id=42)

    await commands.cmd_export_chat_invite_link(message)

    commands.perform_export_chat_invite_link.assert_awaited_once_with(
        message.bot,
        chat_id=-100123,
    )
    args, kwargs = message.answer.await_args
    assert args[0] == "ok"
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_export_chat_invite_link_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(
        method=ExportChatInviteLink(chat_id=-100123),
        message="Bad Request: not enough rights",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_export_chat_invite_link",
        AsyncMock(side_effect=error),
    )
    message = _message(text="/exportchatinvitelink -100123", chat_id=42)

    await commands.cmd_export_chat_invite_link(message)

    args, _kwargs = message.answer.await_args
    assert "Could not export the chat invite link" in args[0]


def test_parse_export_chat_invite_link_args():
    assert commands._parse_export_chat_invite_link_args(
        "/exportchatinvitelink -100123"
    ) == -100123


def test_parse_export_chat_invite_link_args_rejects_invalid_input():
    assert commands._parse_export_chat_invite_link_args("/exportchatinvitelink") is None
    assert (
        commands._parse_export_chat_invite_link_args("/exportchatinvitelink nope")
        is None
    )
    assert (
        commands._parse_export_chat_invite_link_args(
            "/exportchatinvitelink -100123 extra"
        )
        is None
    )
