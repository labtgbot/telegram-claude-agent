from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import SendDice

from bot.handlers import commands
from bot.services.send_dice import perform_send_dice

DART_EMOJI = "🎯"
SLOT_EMOJI = "🎰"


async def test_perform_send_dice_uses_typed_aiogram_api():
    sent = SimpleNamespace(message_id=777)
    bot = SimpleNamespace(send_dice=AsyncMock(return_value=sent))

    result = await perform_send_dice(bot, chat_id=42)

    assert result is sent
    bot.send_dice.assert_awaited_once_with(
        chat_id=42,
        emoji=None,
        message_thread_id=None,
        disable_notification=None,
        protect_content=None,
    )


async def test_perform_send_dice_forwards_optional_fields():
    bot = SimpleNamespace(
        send_dice=AsyncMock(return_value=SimpleNamespace(message_id=1))
    )

    await perform_send_dice(
        bot,
        chat_id=42,
        emoji=DART_EMOJI,
        message_thread_id=5,
        disable_notification=True,
        protect_content=True,
    )

    _, kwargs = bot.send_dice.await_args
    assert kwargs["emoji"] == DART_EMOJI
    assert kwargs["message_thread_id"] == 5
    assert kwargs["disable_notification"] is True
    assert kwargs["protect_content"] is True


async def test_perform_send_dice_reraises_telegram_errors():
    error = TelegramBadRequest(
        method=SendDice(chat_id=1),
        message="Bad Request: DICE_EMOJI_INVALID",
    )
    bot = SimpleNamespace(send_dice=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_send_dice(bot, chat_id=1)


async def test_perform_send_dice_reraises_forbidden():
    error = TelegramForbiddenError(
        method=SendDice(chat_id=1),
        message="Forbidden: bot was blocked by the user",
    )
    bot = SimpleNamespace(send_dice=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_send_dice(bot, chat_id=1)


def _message(text: str = "/dice", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_dice_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_dice", AsyncMock())
    message = _message(text="/dice", chat_id=42)

    await commands.cmd_dice(message)

    commands.perform_send_dice.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_dice_sends_default_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_send_dice", AsyncMock(return_value=object())
    )
    message = _message(text="/dice", chat_id=42)

    await commands.cmd_dice(message)

    commands.perform_send_dice.assert_awaited_once_with(
        message.bot,
        chat_id=42,
        emoji=None,
    )
    args, _ = message.answer.await_args
    assert args[0] == "Sent dice."


async def test_cmd_dice_sends_with_emoji(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_send_dice", AsyncMock(return_value=object())
    )
    message = _message(text=f"/dice {SLOT_EMOJI}", chat_id=42)

    await commands.cmd_dice(message)

    commands.perform_send_dice.assert_awaited_once_with(
        message.bot,
        chat_id=42,
        emoji=SLOT_EMOJI,
    )
    args, _ = message.answer.await_args
    assert args[0] == "Sent dice."


async def test_cmd_dice_shows_usage_for_invalid_emoji(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_dice", AsyncMock())
    message = _message(text="/dice 🍕", chat_id=42)

    await commands.cmd_dice(message)

    commands.perform_send_dice.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "dice usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_dice_shows_usage_for_too_many_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_dice", AsyncMock())
    message = _message(text=f"/dice {DART_EMOJI} {SLOT_EMOJI}", chat_id=42)

    await commands.cmd_dice(message)

    commands.perform_send_dice.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "dice usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_dice_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(
        method=SendDice(chat_id=42),
        message="Bad Request: chat not found",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_send_dice", AsyncMock(side_effect=error)
    )
    message = _message(text="/dice", chat_id=42)

    await commands.cmd_dice(message)

    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Could not send the dice" in args[0]
