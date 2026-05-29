import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import stop_message_live_location
from bot.services.stop_message_live_location import (
    StopMessageLiveLocationError,
    perform_stop_message_live_location,
)


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
        stop_message_live_location.httpx, "AsyncClient", lambda *a, **k: client
    )


async def test_perform_stop_message_live_location_posts_raw_chat_payload(monkeypatch):
    client = _FakeClient(
        response=_FakeResponse({"ok": True, "result": {"message_id": 55}})
    )
    _install_client(monkeypatch, client)

    result = await perform_stop_message_live_location(
        _bot(),
        chat_id=-100123,
        message_id=55,
    )

    assert result == {"message_id": 55}
    assert (
        client.posted["url"]
        == "https://api.telegram.org/bot123:abc/stopMessageLiveLocation"
    )
    assert client.posted["json"] == {
        "chat_id": -100123,
        "message_id": 55,
    }


async def test_perform_stop_message_live_location_posts_inline_payload(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    result = await perform_stop_message_live_location(
        _bot(),
        inline_message_id=" inline-1 ",
        reply_markup={"inline_keyboard": []},
    )

    assert result is True
    assert client.posted["json"] == {
        "inline_message_id": "inline-1",
        "reply_markup": json.dumps({"inline_keyboard": []}),
    }


@pytest.mark.parametrize(
    "kwargs",
    [
        {"chat_id": -100123},
        {"message_id": 55},
        {"chat_id": -100123, "message_id": 0},
        {
            "chat_id": -100123,
            "message_id": 55,
            "inline_message_id": "inline-1",
        },
    ],
)
async def test_perform_stop_message_live_location_validates_before_request(
    monkeypatch, kwargs
):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    with pytest.raises(StopMessageLiveLocationError):
        await perform_stop_message_live_location(_bot(), **kwargs)

    assert client.posted is None


async def test_perform_stop_message_live_location_raises_on_telegram_error(monkeypatch):
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

    with pytest.raises(StopMessageLiveLocationError) as excinfo:
        await perform_stop_message_live_location(
            _bot(),
            chat_id=-100123,
            message_id=55,
        )

    assert excinfo.value.error_code == 400
    assert "can't be edited" in str(excinfo.value)


async def test_perform_stop_message_live_location_raises_on_transport_error(monkeypatch):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(StopMessageLiveLocationError):
        await perform_stop_message_live_location(
            _bot(),
            chat_id=-100123,
            message_id=55,
        )


def test_parse_message_management_target_args_chat_target():
    assert commands._parse_message_management_target_args(
        "/stoplivelocation -100123 55"
    ) == {"chat_id": -100123, "message_id": 55}


def test_parse_message_management_target_args_inline_target():
    assert commands._parse_message_management_target_args(
        "/stoplivelocation inline=abc123"
    ) == {"inline_message_id": "abc123"}


def test_parse_message_management_target_args_rejects_invalid_input():
    assert commands._parse_message_management_target_args("/stoplivelocation") is None
    assert (
        commands._parse_message_management_target_args(
            "/stoplivelocation nope 55"
        )
        is None
    )
    assert (
        commands._parse_message_management_target_args("/stoplivelocation -100123 0")
        is None
    )
    assert (
        commands._parse_message_management_target_args(
            "/stoplivelocation inline=abc unexpected"
        )
        is None
    )


def _message(text: str = "/stoplivelocation", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_stop_message_live_location_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_stop_message_live_location", AsyncMock())
    message = _message(text="/stoplivelocation -100123 55")

    await commands.cmd_stop_message_live_location(message)

    commands.perform_stop_message_live_location.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_stop_message_live_location_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_stop_message_live_location", AsyncMock())
    message = _message(text="/stoplivelocation", chat_id=42)

    await commands.cmd_stop_message_live_location(message)

    commands.perform_stop_message_live_location.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "stoplivelocation usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_stop_message_live_location_stops_chat_message(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_stop_message_live_location",
        AsyncMock(return_value={"message_id": 55}),
    )
    message = _message(text="/stoplivelocation -100123 55", chat_id=42)

    await commands.cmd_stop_message_live_location(message)

    commands.perform_stop_message_live_location.assert_awaited_once_with(
        message.bot,
        chat_id=-100123,
        message_id=55,
    )
    message.answer.assert_awaited_once_with("Stopped live location for message 55.")
