from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import UnbanChatSenderChat

from bot.handlers import commands
from bot.services.unban_chat_sender_chat import (
    format_unban_sender_chat_result,
    perform_unban_chat_sender_chat,
)


def _message(text: str = "/unbanchatsenderchat", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_perform_unban_chat_sender_chat_uses_typed_aiogram_api():
    bot = SimpleNamespace(unban_chat_sender_chat=AsyncMock(return_value=True))

    result = await perform_unban_chat_sender_chat(
        bot, chat_id=-100123, sender_chat_id=-100456
    )

    assert result is True
    bot.unban_chat_sender_chat.assert_awaited_once_with(
        chat_id=-100123,
        sender_chat_id=-100456,
    )


async def test_perform_unban_chat_sender_chat_reraises_bad_request():
    error = TelegramBadRequest(
        method=UnbanChatSenderChat(chat_id=-100123, sender_chat_id=-100456),
        message="Bad Request: CHAT_ADMIN_REQUIRED",
    )
    bot = SimpleNamespace(unban_chat_sender_chat=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_unban_chat_sender_chat(
            bot, chat_id=-100123, sender_chat_id=-100456
        )


async def test_perform_unban_chat_sender_chat_reraises_forbidden():
    error = TelegramForbiddenError(
        method=UnbanChatSenderChat(chat_id=-100123, sender_chat_id=-100456),
        message="Forbidden: bot is not a member of the supergroup chat",
    )
    bot = SimpleNamespace(unban_chat_sender_chat=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_unban_chat_sender_chat(
            bot, chat_id=-100123, sender_chat_id=-100456
        )


def test_format_unban_sender_chat_result():
    text = format_unban_sender_chat_result(chat_id=-100123, sender_chat_id=-100456)

    assert "unbanChatSenderChat" in text
    assert "-100123" in text
    assert "-100456" in text
    assert "unbanned successfully" in text


async def test_cmd_unban_chat_sender_chat_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_unban_chat_sender_chat", AsyncMock())
    message = _message(text="/unbanchatsenderchat -100123 -100456", chat_id=42)

    await commands.cmd_unban_chat_sender_chat(message)

    commands.perform_unban_chat_sender_chat.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_unban_chat_sender_chat_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_unban_chat_sender_chat", AsyncMock())
    message = _message(text="/unbanchatsenderchat", chat_id=42)

    await commands.cmd_unban_chat_sender_chat(message)

    commands.perform_unban_chat_sender_chat.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "unbanchatsenderchat usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_unban_chat_sender_chat_shows_usage_on_invalid_chat_id(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_unban_chat_sender_chat", AsyncMock())
    message = _message(text="/unbanchatsenderchat notanumber -100456", chat_id=42)

    await commands.cmd_unban_chat_sender_chat(message)

    commands.perform_unban_chat_sender_chat.assert_not_awaited()
    args, _ = message.answer.await_args
    assert "unbanchatsenderchat usage" in args[0]


async def test_cmd_unban_chat_sender_chat_shows_usage_on_invalid_sender_chat_id(
    monkeypatch,
):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_unban_chat_sender_chat", AsyncMock())
    message = _message(text="/unbanchatsenderchat -100123 bad", chat_id=42)

    await commands.cmd_unban_chat_sender_chat(message)

    commands.perform_unban_chat_sender_chat.assert_not_awaited()
    args, _ = message.answer.await_args
    assert "unbanchatsenderchat usage" in args[0]


async def test_cmd_unban_chat_sender_chat_calls_service(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_unban_chat_sender_chat", AsyncMock(return_value=True)
    )
    monkeypatch.setattr(
        commands,
        "format_unban_sender_chat_result",
        lambda chat_id, sender_chat_id: "ok",
    )
    message = _message(text="/unbanchatsenderchat -100123 -100456", chat_id=42)

    await commands.cmd_unban_chat_sender_chat(message)

    commands.perform_unban_chat_sender_chat.assert_awaited_once_with(
        message.bot,
        chat_id=-100123,
        sender_chat_id=-100456,
    )
    args, kwargs = message.answer.await_args
    assert "ok" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_unban_chat_sender_chat_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(
        method=UnbanChatSenderChat(chat_id=-100123, sender_chat_id=-100456),
        message="Bad Request: CHAT_ADMIN_REQUIRED",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_unban_chat_sender_chat", AsyncMock(side_effect=error)
    )
    message = _message(text="/unbanchatsenderchat -100123 -100456", chat_id=42)

    await commands.cmd_unban_chat_sender_chat(message)

    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Could not unban the sender chat" in args[0]


def test_parse_unban_chat_sender_chat_args_no_args():
    assert commands._parse_unban_chat_sender_chat_args("/unbanchatsenderchat") is None


def test_parse_unban_chat_sender_chat_args_only_chat_id():
    assert (
        commands._parse_unban_chat_sender_chat_args("/unbanchatsenderchat -100123")
        is None
    )


def test_parse_unban_chat_sender_chat_args_required_only():
    result = commands._parse_unban_chat_sender_chat_args(
        "/unbanchatsenderchat -100123 -100456"
    )

    assert result == (-100123, -100456)


def test_parse_unban_chat_sender_chat_args_invalid_chat_id():
    assert (
        commands._parse_unban_chat_sender_chat_args(
            "/unbanchatsenderchat bad -100456"
        )
        is None
    )


def test_parse_unban_chat_sender_chat_args_invalid_sender_chat_id():
    assert (
        commands._parse_unban_chat_sender_chat_args(
            "/unbanchatsenderchat -100123 bad"
        )
        is None
    )
