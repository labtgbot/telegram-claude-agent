from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import DeleteChatPhoto

from bot.handlers import commands
from bot.services.delete_chat_photo import (
    format_delete_chat_photo_result,
    perform_delete_chat_photo,
)


def _message(text: str = "/deletechatphoto", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_perform_delete_chat_photo_uses_typed_aiogram_api():
    bot = SimpleNamespace(delete_chat_photo=AsyncMock(return_value=True))

    result = await perform_delete_chat_photo(bot, chat_id=-100123)

    assert result is True
    bot.delete_chat_photo.assert_awaited_once_with(chat_id=-100123)


async def test_perform_delete_chat_photo_reraises_bad_request():
    error = TelegramBadRequest(
        method=DeleteChatPhoto(chat_id=-100123),
        message="Bad Request: not enough rights",
    )
    bot = SimpleNamespace(delete_chat_photo=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_delete_chat_photo(bot, chat_id=-100123)


async def test_perform_delete_chat_photo_reraises_forbidden():
    error = TelegramForbiddenError(
        method=DeleteChatPhoto(chat_id=-100123),
        message="Forbidden: bot is not an administrator",
    )
    bot = SimpleNamespace(delete_chat_photo=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_delete_chat_photo(bot, chat_id=-100123)


def test_format_delete_chat_photo_result_escapes_chat_id():
    text = format_delete_chat_photo_result(chat_id=-100123)

    assert "deleteChatPhoto" in text
    assert "-100123" in text
    assert "chat photo deleted" in text


async def test_cmd_delete_chat_photo_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_delete_chat_photo", AsyncMock())
    message = _message(text="/deletechatphoto -100123", chat_id=42)

    await commands.cmd_delete_chat_photo(message)

    commands.perform_delete_chat_photo.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_delete_chat_photo_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_delete_chat_photo", AsyncMock())
    message = _message(text="/deletechatphoto", chat_id=42)

    await commands.cmd_delete_chat_photo(message)

    commands.perform_delete_chat_photo.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "deletechatphoto usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_delete_chat_photo_calls_service(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_delete_chat_photo", AsyncMock(return_value=True)
    )
    monkeypatch.setattr(commands, "format_delete_chat_photo_result", lambda **_: "ok")
    message = _message(text="/deletechatphoto -100123", chat_id=42)

    await commands.cmd_delete_chat_photo(message)

    commands.perform_delete_chat_photo.assert_awaited_once_with(
        message.bot,
        chat_id=-100123,
    )
    message.answer.assert_awaited_once_with("ok", parse_mode="HTML")


async def test_cmd_delete_chat_photo_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(
        method=DeleteChatPhoto(chat_id=-100123),
        message="Bad Request: CHAT_ADMIN_REQUIRED",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_delete_chat_photo", AsyncMock(side_effect=error)
    )
    message = _message(text="/deletechatphoto -100123", chat_id=42)

    await commands.cmd_delete_chat_photo(message)

    args, _ = message.answer.await_args
    assert "Could not delete the chat photo" in args[0]
    assert "CHAT_ADMIN_REQUIRED" not in args[0]
    assert "Please try again later" in args[0]
