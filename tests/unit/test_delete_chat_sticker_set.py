from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import DeleteChatStickerSet

from bot.handlers import commands
from bot.services.delete_chat_sticker_set import (
    format_delete_chat_sticker_set_result,
    perform_delete_chat_sticker_set,
)


def _message(text: str = "/deletechatstickerset", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_perform_delete_chat_sticker_set_uses_typed_aiogram_api():
    bot = SimpleNamespace(delete_chat_sticker_set=AsyncMock(return_value=True))

    result = await perform_delete_chat_sticker_set(bot, chat_id=-100123)

    assert result is True
    bot.delete_chat_sticker_set.assert_awaited_once_with(chat_id=-100123)


async def test_perform_delete_chat_sticker_set_reraises_bad_request():
    error = TelegramBadRequest(
        method=DeleteChatStickerSet(chat_id=-100123),
        message="Bad Request: CHAT_ADMIN_REQUIRED",
    )
    bot = SimpleNamespace(delete_chat_sticker_set=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_delete_chat_sticker_set(bot, chat_id=-100123)


async def test_perform_delete_chat_sticker_set_reraises_forbidden():
    error = TelegramForbiddenError(
        method=DeleteChatStickerSet(chat_id=-100123),
        message="Forbidden: bot is not an administrator",
    )
    bot = SimpleNamespace(delete_chat_sticker_set=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_delete_chat_sticker_set(bot, chat_id=-100123)


def test_format_delete_chat_sticker_set_result_escapes_fields():
    text = format_delete_chat_sticker_set_result(chat_id=-100123)

    assert "deleteChatStickerSet" in text
    assert "-100123" in text
    assert "chat sticker set deleted" in text


async def test_cmd_delete_chat_sticker_set_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_delete_chat_sticker_set", AsyncMock())
    message = _message(text="/deletechatstickerset -100123", chat_id=42)

    await commands.cmd_delete_chat_sticker_set(message)

    commands.perform_delete_chat_sticker_set.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_delete_chat_sticker_set_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_delete_chat_sticker_set", AsyncMock())
    message = _message(text="/deletechatstickerset", chat_id=42)

    await commands.cmd_delete_chat_sticker_set(message)

    commands.perform_delete_chat_sticker_set.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "deletechatstickerset usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_delete_chat_sticker_set_calls_service(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_delete_chat_sticker_set", AsyncMock(return_value=True)
    )
    monkeypatch.setattr(
        commands, "format_delete_chat_sticker_set_result", lambda **_: "ok"
    )
    message = _message(text="/deletechatstickerset -100123", chat_id=42)

    await commands.cmd_delete_chat_sticker_set(message)

    commands.perform_delete_chat_sticker_set.assert_awaited_once_with(
        message.bot,
        chat_id=-100123,
    )
    message.answer.assert_awaited_once_with("ok", parse_mode="HTML")


async def test_cmd_delete_chat_sticker_set_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(
        method=DeleteChatStickerSet(chat_id=-100123),
        message="Bad Request: CHAT_ADMIN_REQUIRED",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_delete_chat_sticker_set", AsyncMock(side_effect=error)
    )
    message = _message(text="/deletechatstickerset -100123", chat_id=42)

    await commands.cmd_delete_chat_sticker_set(message)

    args, _ = message.answer.await_args
    assert "Could not delete the chat sticker set" in args[0]
    assert "CHAT_ADMIN_REQUIRED" not in args[0]
    assert "Please try again later" in args[0]


def test_parse_delete_chat_sticker_set_args_required_only():
    result = commands._parse_delete_chat_sticker_set_args(
        "/deletechatstickerset -100123"
    )

    assert result == -100123


def test_parse_delete_chat_sticker_set_args_requires_chat_id():
    assert commands._parse_delete_chat_sticker_set_args("/deletechatstickerset") is None


def test_parse_delete_chat_sticker_set_args_invalid_chat_id():
    assert (
        commands._parse_delete_chat_sticker_set_args(
            "/deletechatstickerset not-a-chat"
        )
        is None
    )


def test_parse_delete_chat_sticker_set_args_rejects_extra_args():
    assert (
        commands._parse_delete_chat_sticker_set_args("/deletechatstickerset -100123 extra")
        is None
    )
