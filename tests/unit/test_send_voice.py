from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import SendVoice

from bot.handlers import commands
from bot.services.send_voice import perform_send_voice

VOICE_URL = "https://example.com/note.ogg"


async def test_perform_send_voice_uses_typed_aiogram_api():
    sent = SimpleNamespace(message_id=555)
    bot = SimpleNamespace(send_voice=AsyncMock(return_value=sent))

    result = await perform_send_voice(
        bot,
        chat_id=42,
        voice=VOICE_URL,
        caption="hello",
    )

    assert result is sent
    bot.send_voice.assert_awaited_once_with(
        chat_id=42,
        voice=VOICE_URL,
        caption="hello",
        parse_mode=None,
        duration=None,
        message_thread_id=None,
        disable_notification=None,
        protect_content=None,
    )


async def test_perform_send_voice_reraises_telegram_errors():
    error = TelegramBadRequest(
        method=SendVoice(chat_id=1, voice=VOICE_URL),
        message="Bad Request: wrong file identifier/HTTP URL specified",
    )
    bot = SimpleNamespace(send_voice=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_send_voice(bot, chat_id=1, voice=VOICE_URL)


async def test_perform_send_voice_reraises_forbidden():
    error = TelegramForbiddenError(
        method=SendVoice(chat_id=1, voice=VOICE_URL),
        message="Forbidden: bot was blocked by the user",
    )
    bot = SimpleNamespace(send_voice=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_send_voice(bot, chat_id=1, voice=VOICE_URL)


def _message(text: str = "/voice", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_voice_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_voice", AsyncMock())
    message = _message(text=f"/voice {VOICE_URL}", chat_id=42)

    await commands.cmd_voice(message)

    commands.perform_send_voice.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_voice_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_voice", AsyncMock())
    message = _message(text="/voice", chat_id=42)

    await commands.cmd_voice(message)

    commands.perform_send_voice.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "voice usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_voice_rejects_too_long_caption(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_voice", AsyncMock())
    long_caption = "x" * (commands.VOICE_CAPTION_LIMIT + 1)
    message = _message(
        text=f"/voice {VOICE_URL} {long_caption}", chat_id=42
    )

    await commands.cmd_voice(message)

    commands.perform_send_voice.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Caption is too long" in args[0]


async def test_cmd_voice_sends_with_caption(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_send_voice", AsyncMock(return_value=object())
    )
    message = _message(text=f"/voice {VOICE_URL} a short note", chat_id=42)

    await commands.cmd_voice(message)

    commands.perform_send_voice.assert_awaited_once_with(
        message.bot,
        chat_id=42,
        voice=VOICE_URL,
        caption="a short note",
    )
    args, _ = message.answer.await_args
    assert "Sent voice message with caption." in args[0]


async def test_cmd_voice_sends_without_caption(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_send_voice", AsyncMock(return_value=object())
    )
    message = _message(text=f"/voice {VOICE_URL}", chat_id=42)

    await commands.cmd_voice(message)

    commands.perform_send_voice.assert_awaited_once_with(
        message.bot,
        chat_id=42,
        voice=VOICE_URL,
        caption=None,
    )
    args, _ = message.answer.await_args
    assert args[0] == "Sent voice message."


async def test_cmd_voice_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(
        method=SendVoice(chat_id=42, voice=VOICE_URL),
        message="Bad Request: wrong file identifier/HTTP URL specified",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_send_voice", AsyncMock(side_effect=error)
    )
    message = _message(text=f"/voice {VOICE_URL}", chat_id=42)

    await commands.cmd_voice(message)

    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Could not send the voice message" in args[0]
