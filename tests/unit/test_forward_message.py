from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import ForwardMessage

from bot.handlers import commands
from bot.services.forward_message import perform_forward_message


async def test_perform_forward_message_uses_typed_aiogram_api():
    forwarded = SimpleNamespace(message_id=777)
    bot = SimpleNamespace(forward_message=AsyncMock(return_value=forwarded))

    result = await perform_forward_message(
        bot,
        chat_id=42,
        from_chat_id=-100123,
        message_id=55,
        protect_content=True,
    )

    assert result is forwarded
    bot.forward_message.assert_awaited_once_with(
        chat_id=42,
        from_chat_id=-100123,
        message_id=55,
        message_thread_id=None,
        disable_notification=None,
        protect_content=True,
    )


async def test_perform_forward_message_reraises_telegram_errors():
    error = TelegramBadRequest(
        method=ForwardMessage(chat_id=1, from_chat_id=2, message_id=3),
        message="Bad Request: message to forward not found",
    )
    bot = SimpleNamespace(forward_message=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_forward_message(
            bot, chat_id=1, from_chat_id=2, message_id=3
        )


async def test_perform_forward_message_reraises_forbidden():
    error = TelegramForbiddenError(
        method=ForwardMessage(chat_id=1, from_chat_id=2, message_id=3),
        message="Forbidden: bot is not a member of the chat",
    )
    bot = SimpleNamespace(forward_message=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_forward_message(
            bot, chat_id=1, from_chat_id=2, message_id=3
        )


def _message(text: str = "/forward", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_forward_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_forward_message", AsyncMock())
    message = _message(text="/forward 100 55", chat_id=42)

    await commands.cmd_forward(message)

    commands.perform_forward_message.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_forward_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_forward_message", AsyncMock())
    message = _message(text="/forward", chat_id=42)

    await commands.cmd_forward(message)

    commands.perform_forward_message.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "forward usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_forward_shows_usage_on_invalid_ids(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_forward_message", AsyncMock())
    message = _message(text="/forward abc 55", chat_id=42)

    await commands.cmd_forward(message)

    commands.perform_forward_message.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "forward usage" in args[0]


async def test_cmd_forward_protects_content_by_default(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_forward_message", AsyncMock(return_value=object())
    )
    message = _message(text="/forward -100123 55", chat_id=42)

    await commands.cmd_forward(message)

    commands.perform_forward_message.assert_awaited_once_with(
        message.bot,
        chat_id=42,
        from_chat_id=-100123,
        message_id=55,
        protect_content=True,
    )
    args, _ = message.answer.await_args
    assert "Forwarded message 55" in args[0]
    assert "protected" in args[0]


async def test_cmd_forward_share_keyword_disables_protection(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_forward_message", AsyncMock(return_value=object())
    )
    message = _message(text="/forward -100123 55 share", chat_id=42)

    await commands.cmd_forward(message)

    commands.perform_forward_message.assert_awaited_once_with(
        message.bot,
        chat_id=42,
        from_chat_id=-100123,
        message_id=55,
        protect_content=False,
    )
    args, _ = message.answer.await_args
    assert "shareable" in args[0]


async def test_cmd_forward_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(
        method=ForwardMessage(chat_id=1, from_chat_id=2, message_id=3),
        message="Bad Request: message to forward not found",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_forward_message", AsyncMock(side_effect=error)
    )
    message = _message(text="/forward -100123 55", chat_id=42)

    await commands.cmd_forward(message)

    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Could not forward the message" in args[0]
