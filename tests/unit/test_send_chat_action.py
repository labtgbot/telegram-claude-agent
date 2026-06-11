import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramNetworkError,
)
from aiogram.methods import SendChatAction

from bot.handlers import chat as chat_handler
from bot.handlers import commands
from bot.services.send_chat_action import (
    SendChatActionError,
    keep_chat_action,
    perform_send_chat_action,
)


async def test_perform_send_chat_action_uses_typed_aiogram_api():
    bot = SimpleNamespace(send_chat_action=AsyncMock(return_value=True))

    result = await perform_send_chat_action(bot, chat_id=42)

    assert result is True
    bot.send_chat_action.assert_awaited_once_with(
        chat_id=42,
        action="typing",
        message_thread_id=None,
        business_connection_id=None,
    )


async def test_perform_send_chat_action_forwards_optional_fields():
    bot = SimpleNamespace(send_chat_action=AsyncMock(return_value=True))

    await perform_send_chat_action(
        bot,
        chat_id=42,
        action="upload_photo",
        message_thread_id=5,
        business_connection_id="bizconn",
    )

    _, kwargs = bot.send_chat_action.await_args
    assert kwargs["action"] == "upload_photo"
    assert kwargs["message_thread_id"] == 5
    assert kwargs["business_connection_id"] == "bizconn"


async def test_perform_send_chat_action_rejects_unsupported_action():
    bot = SimpleNamespace(send_chat_action=AsyncMock())

    with pytest.raises(SendChatActionError):
        await perform_send_chat_action(bot, chat_id=1, action="dancing")

    bot.send_chat_action.assert_not_awaited()


async def test_perform_send_chat_action_reraises_telegram_errors():
    error = TelegramBadRequest(
        method=SendChatAction(chat_id=1, action="typing"),
        message="Bad Request: chat not found",
    )
    bot = SimpleNamespace(send_chat_action=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_send_chat_action(bot, chat_id=1)


async def test_perform_send_chat_action_reraises_forbidden():
    error = TelegramForbiddenError(
        method=SendChatAction(chat_id=1, action="typing"),
        message="Forbidden: bot was blocked by the user",
    )
    bot = SimpleNamespace(send_chat_action=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_send_chat_action(bot, chat_id=1)


async def test_keep_chat_action_shows_and_cancels():
    bot = SimpleNamespace(send_chat_action=AsyncMock(return_value=True))

    async with keep_chat_action(bot, chat_id=42, refresh_seconds=0.01):
        # Yield control so the background runner gets to send at least once.
        await asyncio.sleep(0.05)

    assert bot.send_chat_action.await_count >= 1
    _, kwargs = bot.send_chat_action.await_args
    assert kwargs["action"] == "typing"


async def test_keep_chat_action_stops_after_permanent_telegram_errors():
    error = TelegramBadRequest(
        method=SendChatAction(chat_id=42, action="typing"),
        message="Bad Request: chat not found",
    )
    bot = SimpleNamespace(send_chat_action=AsyncMock(side_effect=error))

    # A failure to display the indicator must not break the wrapped block.
    async with keep_chat_action(bot, chat_id=42, refresh_seconds=0.01):
        await asyncio.sleep(0.05)

    assert bot.send_chat_action.await_count == 1


async def test_keep_chat_action_retries_transient_telegram_errors():
    error = TelegramNetworkError(
        method=SendChatAction(chat_id=42, action="typing"),
        message="Network error",
    )
    bot = SimpleNamespace(send_chat_action=AsyncMock(side_effect=error))

    # A transient failure to display the indicator must not break the block and
    # should keep retrying while the request is still running.
    async with keep_chat_action(bot, chat_id=42, refresh_seconds=0.01):
        await asyncio.sleep(0.05)

    assert bot.send_chat_action.await_count > 1


def _message(text: str = "/chataction", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_chat_action_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_chat_action", AsyncMock())
    message = _message(text="/chataction", chat_id=42)

    await commands.cmd_chat_action(message)

    commands.perform_send_chat_action.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_chat_action_sends_default_typing_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_send_chat_action", AsyncMock(return_value=True)
    )
    message = _message(text="/chataction", chat_id=42)

    await commands.cmd_chat_action(message)

    commands.perform_send_chat_action.assert_awaited_once_with(
        message.bot,
        chat_id=42,
        action="typing",
    )
    args, _ = message.answer.await_args
    assert args[0] == "Showed the typing chat action."


async def test_cmd_chat_action_sends_with_explicit_action(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_send_chat_action", AsyncMock(return_value=True)
    )
    message = _message(text="/chataction upload_document", chat_id=42)

    await commands.cmd_chat_action(message)

    commands.perform_send_chat_action.assert_awaited_once_with(
        message.bot,
        chat_id=42,
        action="upload_document",
    )
    args, _ = message.answer.await_args
    assert args[0] == "Showed the upload_document chat action."


async def test_cmd_chat_action_shows_usage_for_invalid_action(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_chat_action", AsyncMock())
    message = _message(text="/chataction dancing", chat_id=42)

    await commands.cmd_chat_action(message)

    commands.perform_send_chat_action.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "chataction usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_chat_action_shows_usage_for_too_many_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_chat_action", AsyncMock())
    message = _message(text="/chataction typing upload_photo", chat_id=42)

    await commands.cmd_chat_action(message)

    commands.perform_send_chat_action.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "chataction usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_chat_action_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(
        method=SendChatAction(chat_id=42, action="typing"),
        message="Bad Request: chat not found",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_send_chat_action", AsyncMock(side_effect=error)
    )
    message = _message(text="/chataction", chat_id=42)

    await commands.cmd_chat_action(message)

    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Could not show the chat action" in args[0]


def _chat_message(chat_id: int = 42):
    return SimpleNamespace(
        bot=SimpleNamespace(send_chat_action=AsyncMock(return_value=True)),
        chat=SimpleNamespace(id=chat_id),
    )


async def test_typing_indicator_active_when_enabled(monkeypatch):
    monkeypatch.setattr(
        chat_handler.settings, "telegram_chat_action_enabled", True
    )
    message = _chat_message()

    async with chat_handler._typing_indicator(message):
        await asyncio.sleep(0.05)

    assert message.bot.send_chat_action.await_count >= 1
    _, kwargs = message.bot.send_chat_action.await_args
    assert kwargs["action"] == "typing"
    assert kwargs["chat_id"] == 42


async def test_typing_indicator_skips_when_disabled(monkeypatch):
    monkeypatch.setattr(
        chat_handler.settings, "telegram_chat_action_enabled", False
    )
    message = _chat_message()

    async with chat_handler._typing_indicator(message):
        await asyncio.sleep(0.05)

    message.bot.send_chat_action.assert_not_awaited()
