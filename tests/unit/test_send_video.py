from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import SendVideo

from bot.handlers import commands
from bot.services.send_video import perform_send_video

VIDEO_URL = "https://example.com/clip.mp4"


async def test_perform_send_video_uses_typed_aiogram_api():
    sent = SimpleNamespace(message_id=555)
    bot = SimpleNamespace(send_video=AsyncMock(return_value=sent))

    result = await perform_send_video(
        bot,
        chat_id=42,
        video=VIDEO_URL,
        caption="hello",
    )

    assert result is sent
    bot.send_video.assert_awaited_once_with(
        chat_id=42,
        video=VIDEO_URL,
        caption="hello",
        parse_mode=None,
        duration=None,
        width=None,
        height=None,
        thumbnail=None,
        has_spoiler=None,
        supports_streaming=None,
        message_thread_id=None,
        disable_notification=None,
        protect_content=None,
    )


async def test_perform_send_video_reraises_telegram_errors():
    error = TelegramBadRequest(
        method=SendVideo(chat_id=1, video=VIDEO_URL),
        message="Bad Request: wrong file identifier/HTTP URL specified",
    )
    bot = SimpleNamespace(send_video=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_send_video(bot, chat_id=1, video=VIDEO_URL)


async def test_perform_send_video_reraises_forbidden():
    error = TelegramForbiddenError(
        method=SendVideo(chat_id=1, video=VIDEO_URL),
        message="Forbidden: bot was blocked by the user",
    )
    bot = SimpleNamespace(send_video=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_send_video(bot, chat_id=1, video=VIDEO_URL)


def _message(text: str = "/video", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_video_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_video", AsyncMock())
    message = _message(text=f"/video {VIDEO_URL}", chat_id=42)

    await commands.cmd_video(message)

    commands.perform_send_video.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_video_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_video", AsyncMock())
    message = _message(text="/video", chat_id=42)

    await commands.cmd_video(message)

    commands.perform_send_video.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "video usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_video_rejects_too_long_caption(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_video", AsyncMock())
    long_caption = "x" * (commands.VIDEO_CAPTION_LIMIT + 1)
    message = _message(text=f"/video {VIDEO_URL} {long_caption}", chat_id=42)

    await commands.cmd_video(message)

    commands.perform_send_video.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Caption is too long" in args[0]


async def test_cmd_video_sends_with_caption(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_send_video", AsyncMock(return_value=object())
    )
    message = _message(text=f"/video {VIDEO_URL} a short clip", chat_id=42)

    await commands.cmd_video(message)

    commands.perform_send_video.assert_awaited_once_with(
        message.bot,
        chat_id=42,
        video=VIDEO_URL,
        caption="a short clip",
    )
    args, _ = message.answer.await_args
    assert "Sent video with caption." in args[0]


async def test_cmd_video_sends_without_caption(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_send_video", AsyncMock(return_value=object())
    )
    message = _message(text=f"/video {VIDEO_URL}", chat_id=42)

    await commands.cmd_video(message)

    commands.perform_send_video.assert_awaited_once_with(
        message.bot,
        chat_id=42,
        video=VIDEO_URL,
        caption=None,
    )
    args, _ = message.answer.await_args
    assert args[0] == "Sent video."


async def test_cmd_video_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(
        method=SendVideo(chat_id=42, video=VIDEO_URL),
        message="Bad Request: wrong file identifier/HTTP URL specified",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_send_video", AsyncMock(side_effect=error)
    )
    message = _message(text=f"/video {VIDEO_URL}", chat_id=42)

    await commands.cmd_video(message)

    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Could not send the video" in args[0]
