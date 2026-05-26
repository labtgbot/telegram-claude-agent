from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import SendVenue

from bot.handlers import commands
from bot.services.send_venue import perform_send_venue

LATITUDE = 51.5074
LONGITUDE = -0.1278
TITLE = "British Museum"
ADDRESS = "Great Russell St, London"


async def test_perform_send_venue_uses_typed_aiogram_api():
    sent = SimpleNamespace(message_id=777)
    bot = SimpleNamespace(send_venue=AsyncMock(return_value=sent))

    result = await perform_send_venue(
        bot,
        chat_id=42,
        latitude=LATITUDE,
        longitude=LONGITUDE,
        title=TITLE,
        address=ADDRESS,
    )

    assert result is sent
    bot.send_venue.assert_awaited_once_with(
        chat_id=42,
        latitude=LATITUDE,
        longitude=LONGITUDE,
        title=TITLE,
        address=ADDRESS,
        foursquare_id=None,
        foursquare_type=None,
        google_place_id=None,
        google_place_type=None,
        message_thread_id=None,
        disable_notification=None,
        protect_content=None,
    )


async def test_perform_send_venue_forwards_place_metadata():
    bot = SimpleNamespace(send_venue=AsyncMock(return_value=SimpleNamespace(message_id=1)))

    await perform_send_venue(
        bot,
        chat_id=42,
        latitude=LATITUDE,
        longitude=LONGITUDE,
        title=TITLE,
        address=ADDRESS,
        foursquare_id="4ac518cef964a520b6a520e3",
        foursquare_type="arts_entertainment/museum",
        google_place_id="ChIJB9OTMDIbdkgRp0JWbQGZsS8",
        google_place_type="museum",
    )

    _, kwargs = bot.send_venue.await_args
    assert kwargs["foursquare_id"] == "4ac518cef964a520b6a520e3"
    assert kwargs["foursquare_type"] == "arts_entertainment/museum"
    assert kwargs["google_place_id"] == "ChIJB9OTMDIbdkgRp0JWbQGZsS8"
    assert kwargs["google_place_type"] == "museum"


async def test_perform_send_venue_reraises_telegram_errors():
    error = TelegramBadRequest(
        method=SendVenue(
            chat_id=1,
            latitude=LATITUDE,
            longitude=LONGITUDE,
            title=TITLE,
            address=ADDRESS,
        ),
        message="Bad Request: venue address is empty",
    )
    bot = SimpleNamespace(send_venue=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_send_venue(
            bot,
            chat_id=1,
            latitude=LATITUDE,
            longitude=LONGITUDE,
            title=TITLE,
            address=ADDRESS,
        )


async def test_perform_send_venue_reraises_forbidden():
    error = TelegramForbiddenError(
        method=SendVenue(
            chat_id=1,
            latitude=LATITUDE,
            longitude=LONGITUDE,
            title=TITLE,
            address=ADDRESS,
        ),
        message="Forbidden: bot was blocked by the user",
    )
    bot = SimpleNamespace(send_venue=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_send_venue(
            bot,
            chat_id=1,
            latitude=LATITUDE,
            longitude=LONGITUDE,
            title=TITLE,
            address=ADDRESS,
        )


def _message(text: str = "/venue", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_venue_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_venue", AsyncMock())
    message = _message(
        text=f"/venue {LATITUDE} {LONGITUDE} {TITLE} | {ADDRESS}", chat_id=42
    )

    await commands.cmd_venue(message)

    commands.perform_send_venue.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_venue_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_venue", AsyncMock())
    message = _message(text="/venue", chat_id=42)

    await commands.cmd_venue(message)

    commands.perform_send_venue.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "venue usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_venue_shows_usage_for_non_numeric(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_venue", AsyncMock())
    message = _message(text="/venue north south Museum | Street", chat_id=42)

    await commands.cmd_venue(message)

    commands.perform_send_venue.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "venue usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_venue_shows_usage_without_separator(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_venue", AsyncMock())
    message = _message(
        text=f"/venue {LATITUDE} {LONGITUDE} {TITLE} {ADDRESS}", chat_id=42
    )

    await commands.cmd_venue(message)

    commands.perform_send_venue.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "venue usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_venue_shows_usage_for_empty_address(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_venue", AsyncMock())
    message = _message(text=f"/venue {LATITUDE} {LONGITUDE} {TITLE} |", chat_id=42)

    await commands.cmd_venue(message)

    commands.perform_send_venue.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "venue usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_venue_sends_place(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_send_venue", AsyncMock(return_value=object())
    )
    message = _message(
        text=f"/venue {LATITUDE} {LONGITUDE} {TITLE} | {ADDRESS}", chat_id=42
    )

    await commands.cmd_venue(message)

    commands.perform_send_venue.assert_awaited_once_with(
        message.bot,
        chat_id=42,
        latitude=LATITUDE,
        longitude=LONGITUDE,
        title=TITLE,
        address=ADDRESS,
    )
    args, _ = message.answer.await_args
    assert args[0] == "Sent venue."


async def test_cmd_venue_keeps_spaces_in_title_and_address(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_send_venue", AsyncMock(return_value=object())
    )
    message = _message(
        text=f"/venue {LATITUDE} {LONGITUDE}   The   Museum   |   42  Main  St  ",
        chat_id=42,
    )

    await commands.cmd_venue(message)

    _, kwargs = commands.perform_send_venue.await_args
    assert kwargs["title"] == "The   Museum"
    assert kwargs["address"] == "42  Main  St"


async def test_cmd_venue_rejects_out_of_range_latitude(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_venue", AsyncMock())
    message = _message(text=f"/venue 100 0 {TITLE} | {ADDRESS}", chat_id=42)

    await commands.cmd_venue(message)

    commands.perform_send_venue.assert_not_awaited()
    args, _ = message.answer.await_args
    assert "Latitude must be between" in args[0]


async def test_cmd_venue_rejects_out_of_range_longitude(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_venue", AsyncMock())
    message = _message(text=f"/venue 0 200 {TITLE} | {ADDRESS}", chat_id=42)

    await commands.cmd_venue(message)

    commands.perform_send_venue.assert_not_awaited()
    args, _ = message.answer.await_args
    assert "Longitude must be between" in args[0]


async def test_cmd_venue_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(
        method=SendVenue(
            chat_id=42,
            latitude=LATITUDE,
            longitude=LONGITUDE,
            title=TITLE,
            address=ADDRESS,
        ),
        message="Bad Request: chat not found",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_send_venue", AsyncMock(side_effect=error)
    )
    message = _message(
        text=f"/venue {LATITUDE} {LONGITUDE} {TITLE} | {ADDRESS}", chat_id=42
    )

    await commands.cmd_venue(message)

    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Could not send the venue" in args[0]
