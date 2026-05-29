import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import edit_message_live_location
from bot.services.edit_message_live_location import (
    EditMessageLiveLocationError,
    perform_edit_message_live_location,
)

LATITUDE = 51.5074
LONGITUDE = -0.1278


class _FakeResponse:
    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data


class _FakeClient:
    """Minimal async-context-manager stand-in for ``httpx.AsyncClient``."""

    def __init__(self, *, response=None, exc=None):
        self._response = response
        self._exc = exc
        self.posted = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, url, json):
        self.posted = {"url": url, "json": json}
        if self._exc is not None:
            raise self._exc
        return self._response


def _bot(token="123:abc"):
    return SimpleNamespace(
        token=token,
        session=SimpleNamespace(
            api=SimpleNamespace(
                api_url=lambda token, method: (
                    f"https://api.telegram.org/bot{token}/{method}"
                )
            )
        ),
    )


def _install_client(monkeypatch, client):
    monkeypatch.setattr(
        edit_message_live_location.httpx, "AsyncClient", lambda *a, **k: client
    )


async def test_perform_edit_message_live_location_posts_raw_chat_payload(monkeypatch):
    client = _FakeClient(
        response=_FakeResponse({"ok": True, "result": {"message_id": 55}})
    )
    _install_client(monkeypatch, client)

    result = await perform_edit_message_live_location(
        _bot(),
        chat_id=-100123,
        message_id=55,
        latitude=LATITUDE,
        longitude=LONGITUDE,
        horizontal_accuracy=12.5,
        heading=90,
        proximity_alert_radius=200,
    )

    assert result == {"message_id": 55}
    assert (
        client.posted["url"]
        == "https://api.telegram.org/bot123:abc/editMessageLiveLocation"
    )
    assert client.posted["json"] == {
        "chat_id": -100123,
        "message_id": 55,
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "horizontal_accuracy": 12.5,
        "heading": 90,
        "proximity_alert_radius": 200,
    }


async def test_perform_edit_message_live_location_posts_inline_payload(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    result = await perform_edit_message_live_location(
        _bot(),
        inline_message_id=" inline-1 ",
        latitude=LATITUDE,
        longitude=LONGITUDE,
        reply_markup={"inline_keyboard": []},
    )

    assert result is True
    assert client.posted["json"] == {
        "inline_message_id": "inline-1",
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "reply_markup": json.dumps({"inline_keyboard": []}),
    }


@pytest.mark.parametrize(
    "kwargs",
    [
        {"chat_id": -100123, "latitude": LATITUDE, "longitude": LONGITUDE},
        {"message_id": 55, "latitude": LATITUDE, "longitude": LONGITUDE},
        {
            "chat_id": -100123,
            "message_id": 0,
            "latitude": LATITUDE,
            "longitude": LONGITUDE,
        },
        {
            "chat_id": -100123,
            "message_id": 55,
            "inline_message_id": "inline-1",
            "latitude": LATITUDE,
            "longitude": LONGITUDE,
        },
        {"chat_id": -100123, "message_id": 55, "latitude": 100, "longitude": 0},
        {"chat_id": -100123, "message_id": 55, "latitude": 0, "longitude": 200},
        {
            "chat_id": -100123,
            "message_id": 55,
            "latitude": LATITUDE,
            "longitude": LONGITUDE,
            "horizontal_accuracy": 2000,
        },
        {
            "chat_id": -100123,
            "message_id": 55,
            "latitude": LATITUDE,
            "longitude": LONGITUDE,
            "heading": 0,
        },
        {
            "chat_id": -100123,
            "message_id": 55,
            "latitude": LATITUDE,
            "longitude": LONGITUDE,
            "proximity_alert_radius": 0,
        },
    ],
)
async def test_perform_edit_message_live_location_validates_before_request(
    monkeypatch, kwargs
):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    with pytest.raises(EditMessageLiveLocationError):
        await perform_edit_message_live_location(_bot(), **kwargs)

    assert client.posted is None


async def test_perform_edit_message_live_location_raises_on_telegram_error(monkeypatch):
    client = _FakeClient(
        response=_FakeResponse(
            {
                "ok": False,
                "error_code": 400,
                "description": "Bad Request: message can't be edited",
            }
        )
    )
    _install_client(monkeypatch, client)

    with pytest.raises(EditMessageLiveLocationError) as excinfo:
        await perform_edit_message_live_location(
            _bot(),
            chat_id=-100123,
            message_id=55,
            latitude=LATITUDE,
            longitude=LONGITUDE,
        )

    assert excinfo.value.error_code == 400
    assert "can't be edited" in str(excinfo.value)


async def test_perform_edit_message_live_location_raises_on_transport_error(monkeypatch):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(EditMessageLiveLocationError):
        await perform_edit_message_live_location(
            _bot(),
            chat_id=-100123,
            message_id=55,
            latitude=LATITUDE,
            longitude=LONGITUDE,
        )


def test_parse_edit_message_live_location_args_chat_target():
    assert commands._parse_edit_message_live_location_args(
        "/editlivelocation -100123 55 51.5 -0.12 "
        "accuracy=12.5 heading=90 proximity=200"
    ) == (
        {"chat_id": -100123, "message_id": 55},
        51.5,
        -0.12,
        {
            "horizontal_accuracy": 12.5,
            "heading": 90,
            "proximity_alert_radius": 200,
        },
    )


def test_parse_edit_message_live_location_args_inline_target():
    assert commands._parse_edit_message_live_location_args(
        "/editlivelocation inline=abc123 51.5 -0.12"
    ) == (
        {"inline_message_id": "abc123"},
        51.5,
        -0.12,
        {},
    )


def test_parse_edit_message_live_location_args_rejects_invalid_input():
    assert commands._parse_edit_message_live_location_args("/editlivelocation") is None
    assert (
        commands._parse_edit_message_live_location_args(
            "/editlivelocation nope 55 51.5 -0.12"
        )
        is None
    )
    assert (
        commands._parse_edit_message_live_location_args(
            "/editlivelocation -100123 0 51.5 -0.12"
        )
        is None
    )
    assert (
        commands._parse_edit_message_live_location_args(
            "/editlivelocation -100123 55 100 -0.12"
        )
        is None
    )
    assert (
        commands._parse_edit_message_live_location_args(
            "/editlivelocation inline= 51.5 -0.12"
        )
        is None
    )
    assert (
        commands._parse_edit_message_live_location_args(
            "/editlivelocation inline=abc 51.5 -0.12 unexpected=true"
        )
        is None
    )


def _message(text: str = "/editlivelocation", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_edit_message_live_location_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_edit_message_live_location", AsyncMock())
    message = _message(text=f"/editlivelocation -100123 55 {LATITUDE} {LONGITUDE}")

    await commands.cmd_edit_message_live_location(message)

    commands.perform_edit_message_live_location.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_edit_message_live_location_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_edit_message_live_location", AsyncMock())
    message = _message(text="/editlivelocation", chat_id=42)

    await commands.cmd_edit_message_live_location(message)

    commands.perform_edit_message_live_location.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "editlivelocation usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_edit_message_live_location_edits_chat_message(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_edit_message_live_location",
        AsyncMock(return_value={"message_id": 55}),
    )
    message = _message(
        text=f"/editlivelocation -100123 55 {LATITUDE} {LONGITUDE} heading=90",
        chat_id=42,
    )

    await commands.cmd_edit_message_live_location(message)

    commands.perform_edit_message_live_location.assert_awaited_once_with(
        message.bot,
        chat_id=-100123,
        message_id=55,
        latitude=LATITUDE,
        longitude=LONGITUDE,
        heading=90,
    )
    message.answer.assert_awaited_once_with("Edited live location for message 55.")
