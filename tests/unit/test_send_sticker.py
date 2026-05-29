from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import SendSticker

from bot.handlers import commands
from bot.services.send_sticker import perform_send_sticker

STICKER_FILE_ID = "CAACAgIAAxkBAAE"


async def test_perform_send_sticker_uses_typed_aiogram_api():
    sent = SimpleNamespace(message_id=777)
    bot = SimpleNamespace(send_sticker=AsyncMock(return_value=sent))

    result = await perform_send_sticker(
        bot,
        chat_id=42,
        sticker=STICKER_FILE_ID,
        emoji="🙂",
    )

    assert result is sent
    bot.send_sticker.assert_awaited_once_with(
        chat_id=42,
        sticker=STICKER_FILE_ID,
        message_thread_id=None,
        emoji="🙂",
        disable_notification=None,
        protect_content=None,
    )


async def test_perform_send_sticker_reraises_telegram_errors():
    error = TelegramBadRequest(
        method=SendSticker(chat_id=1, sticker=STICKER_FILE_ID),
        message="Bad Request: wrong file identifier/HTTP URL specified",
    )
    bot = SimpleNamespace(send_sticker=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_send_sticker(bot, chat_id=1, sticker=STICKER_FILE_ID)


async def test_perform_send_sticker_reraises_forbidden():
    error = TelegramForbiddenError(
        method=SendSticker(chat_id=1, sticker=STICKER_FILE_ID),
        message="Forbidden: bot was blocked by the user",
    )
    bot = SimpleNamespace(send_sticker=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_send_sticker(bot, chat_id=1, sticker=STICKER_FILE_ID)


def _message(text: str = "/sticker", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_sticker_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_sticker", AsyncMock())
    message = _message(text=f"/sticker {STICKER_FILE_ID}", chat_id=42)

    await commands.cmd_sticker(message)

    commands.perform_send_sticker.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_sticker_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_sticker", AsyncMock())
    message = _message(text="/sticker", chat_id=42)

    await commands.cmd_sticker(message)

    commands.perform_send_sticker.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "sticker usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_sticker_sends_with_emoji(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_send_sticker", AsyncMock(return_value=object())
    )
    message = _message(text=f"/sticker {STICKER_FILE_ID} 🙂", chat_id=42)

    await commands.cmd_sticker(message)

    commands.perform_send_sticker.assert_awaited_once_with(
        message.bot,
        chat_id=42,
        sticker=STICKER_FILE_ID,
        emoji="🙂",
    )
    args, _ = message.answer.await_args
    assert "Sent sticker with emoji hint." in args[0]


async def test_cmd_sticker_sends_without_emoji(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_send_sticker", AsyncMock(return_value=object())
    )
    message = _message(text=f"/sticker {STICKER_FILE_ID}", chat_id=42)

    await commands.cmd_sticker(message)

    commands.perform_send_sticker.assert_awaited_once_with(
        message.bot,
        chat_id=42,
        sticker=STICKER_FILE_ID,
        emoji=None,
    )
    args, _ = message.answer.await_args
    assert args[0] == "Sent sticker."


async def test_cmd_sticker_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(
        method=SendSticker(chat_id=42, sticker=STICKER_FILE_ID),
        message="Bad Request: wrong file identifier/HTTP URL specified",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_send_sticker", AsyncMock(side_effect=error)
    )
    message = _message(text=f"/sticker {STICKER_FILE_ID}", chat_id=42)

    await commands.cmd_sticker(message)

    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Could not send the sticker" in args[0]
