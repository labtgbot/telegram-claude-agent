from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import SendPhoto

from bot.handlers import commands
from bot.services.send_photo import perform_send_photo

PHOTO_URL = "https://example.com/cat.jpg"


async def test_perform_send_photo_uses_typed_aiogram_api():
    sent = SimpleNamespace(message_id=777)
    bot = SimpleNamespace(send_photo=AsyncMock(return_value=sent))

    result = await perform_send_photo(
        bot,
        chat_id=42,
        photo=PHOTO_URL,
        caption="hello",
    )

    assert result is sent
    bot.send_photo.assert_awaited_once_with(
        chat_id=42,
        photo=PHOTO_URL,
        caption="hello",
        parse_mode=None,
        message_thread_id=None,
        has_spoiler=None,
        disable_notification=None,
        protect_content=None,
    )


async def test_perform_send_photo_reraises_telegram_errors():
    error = TelegramBadRequest(
        method=SendPhoto(chat_id=1, photo=PHOTO_URL),
        message="Bad Request: wrong file identifier/HTTP URL specified",
    )
    bot = SimpleNamespace(send_photo=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_send_photo(bot, chat_id=1, photo=PHOTO_URL)


async def test_perform_send_photo_reraises_forbidden():
    error = TelegramForbiddenError(
        method=SendPhoto(chat_id=1, photo=PHOTO_URL),
        message="Forbidden: bot was blocked by the user",
    )
    bot = SimpleNamespace(send_photo=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_send_photo(bot, chat_id=1, photo=PHOTO_URL)


def _message(text: str = "/photo", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_photo_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_photo", AsyncMock())
    message = _message(text=f"/photo {PHOTO_URL}", chat_id=42)

    await commands.cmd_photo(message)

    commands.perform_send_photo.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_photo_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_photo", AsyncMock())
    message = _message(text="/photo", chat_id=42)

    await commands.cmd_photo(message)

    commands.perform_send_photo.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "photo usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_photo_rejects_too_long_caption(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_photo", AsyncMock())
    long_caption = "x" * (commands.PHOTO_CAPTION_LIMIT + 1)
    message = _message(text=f"/photo {PHOTO_URL} {long_caption}", chat_id=42)

    await commands.cmd_photo(message)

    commands.perform_send_photo.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Caption is too long" in args[0]


async def test_cmd_photo_sends_with_caption(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_send_photo", AsyncMock(return_value=object())
    )
    message = _message(text=f"/photo {PHOTO_URL} a nice cat", chat_id=42)

    await commands.cmd_photo(message)

    commands.perform_send_photo.assert_awaited_once_with(
        message.bot,
        chat_id=42,
        photo=PHOTO_URL,
        caption="a nice cat",
    )
    args, _ = message.answer.await_args
    assert "Sent photo with caption." in args[0]


async def test_cmd_photo_sends_without_caption(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_send_photo", AsyncMock(return_value=object())
    )
    message = _message(text=f"/photo {PHOTO_URL}", chat_id=42)

    await commands.cmd_photo(message)

    commands.perform_send_photo.assert_awaited_once_with(
        message.bot,
        chat_id=42,
        photo=PHOTO_URL,
        caption=None,
    )
    args, _ = message.answer.await_args
    assert args[0] == "Sent photo."


async def test_cmd_photo_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(
        method=SendPhoto(chat_id=42, photo=PHOTO_URL),
        message="Bad Request: wrong file identifier/HTTP URL specified",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_send_photo", AsyncMock(side_effect=error)
    )
    message = _message(text=f"/photo {PHOTO_URL}", chat_id=42)

    await commands.cmd_photo(message)

    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Could not send the photo" in args[0]
