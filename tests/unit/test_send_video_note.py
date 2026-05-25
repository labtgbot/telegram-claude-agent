from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import SendVideoNote

from bot.handlers import commands
from bot.services.send_video_note import perform_send_video_note

VIDEO_NOTE_ID = "BAACAgIAAxkBAAVideoNoteFileId"


async def test_perform_send_video_note_uses_typed_aiogram_api():
    sent = SimpleNamespace(message_id=777)
    bot = SimpleNamespace(send_video_note=AsyncMock(return_value=sent))

    result = await perform_send_video_note(
        bot,
        chat_id=42,
        video_note=VIDEO_NOTE_ID,
    )

    assert result is sent
    bot.send_video_note.assert_awaited_once_with(
        chat_id=42,
        video_note=VIDEO_NOTE_ID,
        duration=None,
        length=None,
        thumbnail=None,
        message_thread_id=None,
        disable_notification=None,
        protect_content=None,
    )


async def test_perform_send_video_note_reraises_telegram_errors():
    error = TelegramBadRequest(
        method=SendVideoNote(chat_id=1, video_note=VIDEO_NOTE_ID),
        message="Bad Request: wrong file identifier specified",
    )
    bot = SimpleNamespace(send_video_note=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_send_video_note(bot, chat_id=1, video_note=VIDEO_NOTE_ID)


async def test_perform_send_video_note_reraises_forbidden():
    error = TelegramForbiddenError(
        method=SendVideoNote(chat_id=1, video_note=VIDEO_NOTE_ID),
        message="Forbidden: bot was blocked by the user",
    )
    bot = SimpleNamespace(send_video_note=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_send_video_note(bot, chat_id=1, video_note=VIDEO_NOTE_ID)


def _message(text: str = "/videonote", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_video_note_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_video_note", AsyncMock())
    message = _message(text=f"/videonote {VIDEO_NOTE_ID}", chat_id=42)

    await commands.cmd_video_note(message)

    commands.perform_send_video_note.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_video_note_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_video_note", AsyncMock())
    message = _message(text="/videonote", chat_id=42)

    await commands.cmd_video_note(message)

    commands.perform_send_video_note.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "videonote usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_video_note_sends_file_id(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_send_video_note", AsyncMock(return_value=object())
    )
    message = _message(text=f"/videonote {VIDEO_NOTE_ID}", chat_id=42)

    await commands.cmd_video_note(message)

    commands.perform_send_video_note.assert_awaited_once_with(
        message.bot,
        chat_id=42,
        video_note=VIDEO_NOTE_ID,
    )
    args, _ = message.answer.await_args
    assert args[0] == "Sent video note."


async def test_cmd_video_note_ignores_trailing_tokens(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_send_video_note", AsyncMock(return_value=object())
    )
    message = _message(
        text=f"/videonote {VIDEO_NOTE_ID} this caption is not supported",
        chat_id=42,
    )

    await commands.cmd_video_note(message)

    commands.perform_send_video_note.assert_awaited_once_with(
        message.bot,
        chat_id=42,
        video_note=VIDEO_NOTE_ID,
    )


async def test_cmd_video_note_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(
        method=SendVideoNote(chat_id=42, video_note=VIDEO_NOTE_ID),
        message="Bad Request: wrong file identifier specified",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_send_video_note", AsyncMock(side_effect=error)
    )
    message = _message(text=f"/videonote {VIDEO_NOTE_ID}", chat_id=42)

    await commands.cmd_video_note(message)

    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Could not send the video note" in args[0]
