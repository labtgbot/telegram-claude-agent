from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import SendAudio

from bot.handlers import commands
from bot.services.send_audio import perform_send_audio

AUDIO_URL = "https://example.com/song.mp3"


async def test_perform_send_audio_uses_typed_aiogram_api():
    sent = SimpleNamespace(message_id=777)
    bot = SimpleNamespace(send_audio=AsyncMock(return_value=sent))

    result = await perform_send_audio(
        bot,
        chat_id=42,
        audio=AUDIO_URL,
        caption="hello",
    )

    assert result is sent
    bot.send_audio.assert_awaited_once_with(
        chat_id=42,
        audio=AUDIO_URL,
        caption="hello",
        parse_mode=None,
        duration=None,
        performer=None,
        title=None,
        message_thread_id=None,
        disable_notification=None,
        protect_content=None,
    )


async def test_perform_send_audio_reraises_telegram_errors():
    error = TelegramBadRequest(
        method=SendAudio(chat_id=1, audio=AUDIO_URL),
        message="Bad Request: wrong file identifier/HTTP URL specified",
    )
    bot = SimpleNamespace(send_audio=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_send_audio(bot, chat_id=1, audio=AUDIO_URL)


async def test_perform_send_audio_reraises_forbidden():
    error = TelegramForbiddenError(
        method=SendAudio(chat_id=1, audio=AUDIO_URL),
        message="Forbidden: bot was blocked by the user",
    )
    bot = SimpleNamespace(send_audio=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_send_audio(bot, chat_id=1, audio=AUDIO_URL)


def _message(text: str = "/audio", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_audio_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_audio", AsyncMock())
    message = _message(text=f"/audio {AUDIO_URL}", chat_id=42)

    await commands.cmd_audio(message)

    commands.perform_send_audio.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_audio_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_audio", AsyncMock())
    message = _message(text="/audio", chat_id=42)

    await commands.cmd_audio(message)

    commands.perform_send_audio.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "audio usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_audio_rejects_too_long_caption(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_audio", AsyncMock())
    long_caption = "x" * (commands.AUDIO_CAPTION_LIMIT + 1)
    message = _message(text=f"/audio {AUDIO_URL} {long_caption}", chat_id=42)

    await commands.cmd_audio(message)

    commands.perform_send_audio.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Caption is too long" in args[0]


async def test_cmd_audio_sends_with_caption(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_send_audio", AsyncMock(return_value=object())
    )
    message = _message(text=f"/audio {AUDIO_URL} a nice song", chat_id=42)

    await commands.cmd_audio(message)

    commands.perform_send_audio.assert_awaited_once_with(
        message.bot,
        chat_id=42,
        audio=AUDIO_URL,
        caption="a nice song",
    )
    args, _ = message.answer.await_args
    assert "Sent audio with caption." in args[0]


async def test_cmd_audio_sends_without_caption(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_send_audio", AsyncMock(return_value=object())
    )
    message = _message(text=f"/audio {AUDIO_URL}", chat_id=42)

    await commands.cmd_audio(message)

    commands.perform_send_audio.assert_awaited_once_with(
        message.bot,
        chat_id=42,
        audio=AUDIO_URL,
        caption=None,
    )
    args, _ = message.answer.await_args
    assert args[0] == "Sent audio."


async def test_cmd_audio_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(
        method=SendAudio(chat_id=42, audio=AUDIO_URL),
        message="Bad Request: wrong file identifier/HTTP URL specified",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_send_audio", AsyncMock(side_effect=error)
    )
    message = _message(text=f"/audio {AUDIO_URL}", chat_id=42)

    await commands.cmd_audio(message)

    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Could not send the audio" in args[0]
