from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import SendMediaGroup
from aiogram.types import (
    InputMediaAudio,
    InputMediaDocument,
    InputMediaPhoto,
    InputMediaVideo,
)

from bot.handlers import commands
from bot.services.send_media_group import perform_send_media_group

PHOTO_A = "https://example.com/a.jpg"
PHOTO_B = "https://example.com/b.jpg"


def _photo_album(caption=None):
    first = (
        InputMediaPhoto(media=PHOTO_A, caption=caption)
        if caption is not None
        else InputMediaPhoto(media=PHOTO_A)
    )
    return [first, InputMediaPhoto(media=PHOTO_B)]


async def test_perform_send_media_group_uses_typed_aiogram_api():
    sent = [SimpleNamespace(message_id=1), SimpleNamespace(message_id=2)]
    bot = SimpleNamespace(send_media_group=AsyncMock(return_value=sent))
    media = _photo_album()

    result = await perform_send_media_group(bot, chat_id=42, media=media)

    assert result is sent
    bot.send_media_group.assert_awaited_once_with(
        chat_id=42,
        media=media,
        message_thread_id=None,
        disable_notification=None,
        protect_content=None,
    )


async def test_perform_send_media_group_forwards_options():
    bot = SimpleNamespace(send_media_group=AsyncMock(return_value=[]))

    await perform_send_media_group(
        bot,
        chat_id=42,
        media=_photo_album(),
        message_thread_id=7,
        disable_notification=True,
        protect_content=True,
    )

    _, kwargs = bot.send_media_group.await_args
    assert kwargs["message_thread_id"] == 7
    assert kwargs["disable_notification"] is True
    assert kwargs["protect_content"] is True


async def test_perform_send_media_group_reraises_telegram_errors():
    error = TelegramBadRequest(
        method=SendMediaGroup(chat_id=1, media=_photo_album()),
        message="Bad Request: media group must include at least 2 items",
    )
    bot = SimpleNamespace(send_media_group=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_send_media_group(bot, chat_id=1, media=_photo_album())


async def test_perform_send_media_group_reraises_forbidden():
    error = TelegramForbiddenError(
        method=SendMediaGroup(chat_id=1, media=_photo_album()),
        message="Forbidden: bot was blocked by the user",
    )
    bot = SimpleNamespace(send_media_group=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_send_media_group(bot, chat_id=1, media=_photo_album())


def test_build_media_group_items_applies_caption_to_first_item():
    items = commands._build_media_group_items(
        "photo", [PHOTO_A, PHOTO_B], "album caption"
    )

    assert len(items) == 2
    assert all(isinstance(item, InputMediaPhoto) for item in items)
    assert items[0].caption == "album caption"
    assert items[1].caption is None


def test_build_media_group_items_maps_each_type():
    mapping = {
        "photo": InputMediaPhoto,
        "video": InputMediaVideo,
        "document": InputMediaDocument,
        "audio": InputMediaAudio,
    }
    for media_type, expected_class in mapping.items():
        items = commands._build_media_group_items(
            media_type, [PHOTO_A, PHOTO_B], None
        )
        assert all(isinstance(item, expected_class) for item in items)


def test_parse_media_group_args_extracts_caption_with_spaces():
    parsed = commands._parse_media_group_args(
        f"/mediagroup photo {PHOTO_A} {PHOTO_B} caption hello there"
    )

    assert parsed == ("photo", [PHOTO_A, PHOTO_B], "hello there")


def _message(text="/mediagroup", chat_id=42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_media_group_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_media_group", AsyncMock())
    message = _message(text=f"/mediagroup photo {PHOTO_A} {PHOTO_B}", chat_id=42)

    await commands.cmd_media_group(message)

    commands.perform_send_media_group.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_media_group_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_media_group", AsyncMock())
    message = _message(text="/mediagroup", chat_id=42)

    await commands.cmd_media_group(message)

    commands.perform_send_media_group.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "mediagroup usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_media_group_rejects_unsupported_type(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_media_group", AsyncMock())
    message = _message(text=f"/mediagroup sticker {PHOTO_A} {PHOTO_B}", chat_id=42)

    await commands.cmd_media_group(message)

    commands.perform_send_media_group.assert_not_awaited()
    args, _ = message.answer.await_args
    assert "Unsupported media type" in args[0]


async def test_cmd_media_group_rejects_too_few_items(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_media_group", AsyncMock())
    message = _message(text=f"/mediagroup photo {PHOTO_A}", chat_id=42)

    await commands.cmd_media_group(message)

    commands.perform_send_media_group.assert_not_awaited()
    args, _ = message.answer.await_args
    assert "needs between" in args[0]


async def test_cmd_media_group_rejects_too_many_items(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_media_group", AsyncMock())
    references = " ".join(f"https://example.com/{i}.jpg" for i in range(11))
    message = _message(text=f"/mediagroup photo {references}", chat_id=42)

    await commands.cmd_media_group(message)

    commands.perform_send_media_group.assert_not_awaited()
    args, _ = message.answer.await_args
    assert "needs between" in args[0]


async def test_cmd_media_group_rejects_long_caption(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_media_group", AsyncMock())
    long_caption = "x" * (commands.MEDIA_GROUP_CAPTION_LIMIT + 1)
    message = _message(
        text=f"/mediagroup photo {PHOTO_A} {PHOTO_B} caption {long_caption}",
        chat_id=42,
    )

    await commands.cmd_media_group(message)

    commands.perform_send_media_group.assert_not_awaited()
    args, _ = message.answer.await_args
    assert "Caption is too long" in args[0]


async def test_cmd_media_group_sends_album(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_send_media_group", AsyncMock(return_value=[object(), object()])
    )
    message = _message(text=f"/mediagroup photo {PHOTO_A} {PHOTO_B}", chat_id=42)

    await commands.cmd_media_group(message)

    commands.perform_send_media_group.assert_awaited_once()
    _, kwargs = commands.perform_send_media_group.await_args
    assert kwargs["chat_id"] == 42
    media = kwargs["media"]
    assert len(media) == 2
    assert all(isinstance(item, InputMediaPhoto) for item in media)
    assert media[0].caption is None
    args, _ = message.answer.await_args
    assert args[0] == "Sent media group of 2 items."


async def test_cmd_media_group_applies_caption_to_first_item(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_send_media_group", AsyncMock(return_value=[object()])
    )
    message = _message(
        text=f"/mediagroup photo {PHOTO_A} {PHOTO_B} caption album caption",
        chat_id=42,
    )

    await commands.cmd_media_group(message)

    _, kwargs = commands.perform_send_media_group.await_args
    media = kwargs["media"]
    assert media[0].caption == "album caption"
    assert media[1].caption is None
    args, _ = message.answer.await_args
    assert args[0] == "Sent media group of 2 items with caption."


async def test_cmd_media_group_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(
        method=SendMediaGroup(chat_id=42, media=_photo_album()),
        message="Bad Request: chat not found",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_send_media_group", AsyncMock(side_effect=error)
    )
    message = _message(text=f"/mediagroup photo {PHOTO_A} {PHOTO_B}", chat_id=42)

    await commands.cmd_media_group(message)

    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Could not send the media group" in args[0]
