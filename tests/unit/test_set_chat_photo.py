from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import SetChatPhoto
from aiogram.types import FSInputFile

from bot.handlers import commands
from bot.services.set_chat_photo import (
    format_set_chat_photo_result,
    perform_set_chat_photo,
)


def _message(text: str = "/setchatphoto", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_perform_set_chat_photo_uses_typed_aiogram_api():
    bot = SimpleNamespace(set_chat_photo=AsyncMock(return_value=True))

    result = await perform_set_chat_photo(
        bot,
        chat_id=-100123,
        photo_path="/tmp/group-photo.jpg",
    )

    assert result is True
    bot.set_chat_photo.assert_awaited_once()
    kwargs = bot.set_chat_photo.await_args.kwargs
    assert kwargs["chat_id"] == -100123
    assert isinstance(kwargs["photo"], FSInputFile)
    assert kwargs["photo"].path == "/tmp/group-photo.jpg"


async def test_perform_set_chat_photo_reraises_bad_request():
    error = TelegramBadRequest(
        method=SetChatPhoto(chat_id=-100123, photo=FSInputFile("/tmp/photo.jpg")),
        message="Bad Request: PHOTO_INVALID_DIMENSIONS",
    )
    bot = SimpleNamespace(set_chat_photo=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_set_chat_photo(
            bot,
            chat_id=-100123,
            photo_path="/tmp/photo.jpg",
        )


async def test_perform_set_chat_photo_reraises_forbidden():
    error = TelegramForbiddenError(
        method=SetChatPhoto(chat_id=-100123, photo=FSInputFile("/tmp/photo.jpg")),
        message="Forbidden: bot is not an administrator",
    )
    bot = SimpleNamespace(set_chat_photo=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_set_chat_photo(
            bot,
            chat_id=-100123,
            photo_path="/tmp/photo.jpg",
        )


def test_format_set_chat_photo_result_escapes_fields():
    text = format_set_chat_photo_result(
        chat_id=-100123,
        photo_path="/tmp/photo<&>.jpg",
    )

    assert "setChatPhoto" in text
    assert "-100123" in text
    assert "/tmp/photo&lt;&amp;&gt;.jpg" in text
    assert "chat photo updated" in text


async def test_cmd_set_chat_photo_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_set_chat_photo", AsyncMock())
    message = _message(text="/setchatphoto -100123 /tmp/photo.jpg", chat_id=42)

    await commands.cmd_set_chat_photo(message)

    commands.perform_set_chat_photo.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_set_chat_photo_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_set_chat_photo", AsyncMock())
    message = _message(text="/setchatphoto", chat_id=42)

    await commands.cmd_set_chat_photo(message)

    commands.perform_set_chat_photo.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "setchatphoto usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_set_chat_photo_calls_service(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_set_chat_photo", AsyncMock(return_value=True)
    )
    monkeypatch.setattr(commands, "format_set_chat_photo_result", lambda **_: "ok")
    message = _message(text="/setchatphoto -100123 /tmp/photo.jpg", chat_id=42)

    await commands.cmd_set_chat_photo(message)

    commands.perform_set_chat_photo.assert_awaited_once_with(
        message.bot,
        chat_id=-100123,
        photo_path="/tmp/photo.jpg",
    )
    message.answer.assert_awaited_once_with("ok", parse_mode="HTML")


async def test_cmd_set_chat_photo_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(
        method=SetChatPhoto(chat_id=-100123, photo=FSInputFile("/tmp/photo.jpg")),
        message="Bad Request: CHAT_ADMIN_REQUIRED",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_set_chat_photo", AsyncMock(side_effect=error)
    )
    message = _message(text="/setchatphoto -100123 /tmp/photo.jpg", chat_id=42)

    await commands.cmd_set_chat_photo(message)

    args, _ = message.answer.await_args
    assert "Could not set the chat photo" in args[0]
    assert "CHAT_ADMIN_REQUIRED" not in args[0]
    assert "Please try again later" in args[0]
