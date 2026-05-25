from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import SendLocation

from bot.handlers import commands
from bot.services.send_location import perform_send_location

LATITUDE = 51.5074
LONGITUDE = -0.1278


async def test_perform_send_location_uses_typed_aiogram_api():
    sent = SimpleNamespace(message_id=777)
    bot = SimpleNamespace(send_location=AsyncMock(return_value=sent))

    result = await perform_send_location(
        bot,
        chat_id=42,
        latitude=LATITUDE,
        longitude=LONGITUDE,
    )

    assert result is sent
    bot.send_location.assert_awaited_once_with(
        chat_id=42,
        latitude=LATITUDE,
        longitude=LONGITUDE,
        horizontal_accuracy=None,
        live_period=None,
        heading=None,
        proximity_alert_radius=None,
        message_thread_id=None,
        disable_notification=None,
        protect_content=None,
    )


async def test_perform_send_location_forwards_live_options():
    bot = SimpleNamespace(send_location=AsyncMock(return_value=SimpleNamespace(message_id=1)))

    await perform_send_location(
        bot,
        chat_id=42,
        latitude=LATITUDE,
        longitude=LONGITUDE,
        horizontal_accuracy=12.5,
        live_period=120,
        heading=90,
        proximity_alert_radius=200,
    )

    _, kwargs = bot.send_location.await_args
    assert kwargs["horizontal_accuracy"] == 12.5
    assert kwargs["live_period"] == 120
    assert kwargs["heading"] == 90
    assert kwargs["proximity_alert_radius"] == 200


async def test_perform_send_location_reraises_telegram_errors():
    error = TelegramBadRequest(
        method=SendLocation(chat_id=1, latitude=LATITUDE, longitude=LONGITUDE),
        message="Bad Request: latitude is missing",
    )
    bot = SimpleNamespace(send_location=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_send_location(
            bot, chat_id=1, latitude=LATITUDE, longitude=LONGITUDE
        )


async def test_perform_send_location_reraises_forbidden():
    error = TelegramForbiddenError(
        method=SendLocation(chat_id=1, latitude=LATITUDE, longitude=LONGITUDE),
        message="Forbidden: bot was blocked by the user",
    )
    bot = SimpleNamespace(send_location=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_send_location(
            bot, chat_id=1, latitude=LATITUDE, longitude=LONGITUDE
        )


def _message(text: str = "/location", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_location_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_location", AsyncMock())
    message = _message(text=f"/location {LATITUDE} {LONGITUDE}", chat_id=42)

    await commands.cmd_location(message)

    commands.perform_send_location.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_location_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_location", AsyncMock())
    message = _message(text="/location", chat_id=42)

    await commands.cmd_location(message)

    commands.perform_send_location.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "location usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_location_shows_usage_for_non_numeric(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_location", AsyncMock())
    message = _message(text="/location north south", chat_id=42)

    await commands.cmd_location(message)

    commands.perform_send_location.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "location usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_location_sends_coordinates(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_send_location", AsyncMock(return_value=object())
    )
    message = _message(text=f"/location {LATITUDE} {LONGITUDE}", chat_id=42)

    await commands.cmd_location(message)

    commands.perform_send_location.assert_awaited_once_with(
        message.bot,
        chat_id=42,
        latitude=LATITUDE,
        longitude=LONGITUDE,
    )
    args, _ = message.answer.await_args
    assert args[0] == "Sent location."


async def test_cmd_location_ignores_trailing_tokens(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_send_location", AsyncMock(return_value=object())
    )
    message = _message(
        text=f"/location {LATITUDE} {LONGITUDE} this caption is not supported",
        chat_id=42,
    )

    await commands.cmd_location(message)

    commands.perform_send_location.assert_awaited_once_with(
        message.bot,
        chat_id=42,
        latitude=LATITUDE,
        longitude=LONGITUDE,
    )


async def test_cmd_location_rejects_out_of_range_latitude(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_location", AsyncMock())
    message = _message(text="/location 100 0", chat_id=42)

    await commands.cmd_location(message)

    commands.perform_send_location.assert_not_awaited()
    args, _ = message.answer.await_args
    assert "Latitude must be between" in args[0]


async def test_cmd_location_rejects_out_of_range_longitude(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_location", AsyncMock())
    message = _message(text="/location 0 200", chat_id=42)

    await commands.cmd_location(message)

    commands.perform_send_location.assert_not_awaited()
    args, _ = message.answer.await_args
    assert "Longitude must be between" in args[0]


async def test_cmd_location_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(
        method=SendLocation(chat_id=42, latitude=LATITUDE, longitude=LONGITUDE),
        message="Bad Request: chat not found",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_send_location", AsyncMock(side_effect=error)
    )
    message = _message(text=f"/location {LATITUDE} {LONGITUDE}", chat_id=42)

    await commands.cmd_location(message)

    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Could not send the location" in args[0]
