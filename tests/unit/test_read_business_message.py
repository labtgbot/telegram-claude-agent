from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import read_business_message
from bot.services.read_business_message import (
    ReadBusinessMessageError,
    perform_read_business_message,
)


BUSINESS_CONNECTION_ID = "bizconn-123"
MESSAGE_ID = 456


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
        read_business_message.httpx, "AsyncClient", lambda *a, **k: client
    )


async def test_perform_read_business_message_posts_raw_payload(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    result = await perform_read_business_message(
        _bot(),
        business_connection_id=BUSINESS_CONNECTION_ID,
        message_id=MESSAGE_ID,
    )

    assert result is True
    assert client.posted["url"] == (
        "https://api.telegram.org/bot123:abc/readBusinessMessage"
    )
    assert client.posted["json"] == {
        "business_connection_id": BUSINESS_CONNECTION_ID,
        "message_id": MESSAGE_ID,
    }


async def test_perform_read_business_message_rejects_invalid_args(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    with pytest.raises(ReadBusinessMessageError):
        await perform_read_business_message(
            _bot(), business_connection_id="", message_id=MESSAGE_ID
        )
    with pytest.raises(ReadBusinessMessageError):
        await perform_read_business_message(
            _bot(), business_connection_id=BUSINESS_CONNECTION_ID, message_id=0
        )

    assert client.posted is None


async def test_perform_read_business_message_raises_on_telegram_error(monkeypatch):
    client = _FakeClient(
        response=_FakeResponse(
            {
                "ok": False,
                "error_code": 400,
                "description": "Bad Request: business connection not found",
            }
        )
    )
    _install_client(monkeypatch, client)

    with pytest.raises(ReadBusinessMessageError) as excinfo:
        await perform_read_business_message(
            _bot(),
            business_connection_id=BUSINESS_CONNECTION_ID,
            message_id=MESSAGE_ID,
        )

    assert excinfo.value.error_code == 400
    assert "business connection not found" in str(excinfo.value)


async def test_perform_read_business_message_raises_on_transport_error(monkeypatch):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(ReadBusinessMessageError):
        await perform_read_business_message(
            _bot(),
            business_connection_id=BUSINESS_CONNECTION_ID,
            message_id=MESSAGE_ID,
        )


def test_parse_read_business_message_args():
    assert commands._parse_read_business_message_args(
        f"/readbusinessmessage {BUSINESS_CONNECTION_ID} {MESSAGE_ID}"
    ) == (BUSINESS_CONNECTION_ID, MESSAGE_ID)
    assert commands._parse_read_business_message_args("/readbusinessmessage") is None
    assert (
        commands._parse_read_business_message_args(
            f"/readbusinessmessage {BUSINESS_CONNECTION_ID} not-int"
        )
        is None
    )
    assert (
        commands._parse_read_business_message_args(
            f"/readbusinessmessage {BUSINESS_CONNECTION_ID} 0"
        )
        is None
    )


def _message(text: str = "/readbusinessmessage", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_read_business_message_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_read_business_message", AsyncMock())
    message = _message(
        text=f"/readbusinessmessage {BUSINESS_CONNECTION_ID} {MESSAGE_ID}",
        chat_id=42,
    )

    await commands.cmd_read_business_message(message)

    commands.perform_read_business_message.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_read_business_message_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_read_business_message", AsyncMock())
    message = _message(text="/readbusinessmessage", chat_id=42)

    await commands.cmd_read_business_message(message)

    commands.perform_read_business_message.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "readbusinessmessage usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_read_business_message_marks_message_as_read(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_read_business_message",
        AsyncMock(return_value=True),
    )
    message = _message(
        text=f"/readbusinessmessage {BUSINESS_CONNECTION_ID} {MESSAGE_ID}",
        chat_id=42,
    )

    await commands.cmd_read_business_message(message)

    commands.perform_read_business_message.assert_awaited_once_with(
        message.bot,
        business_connection_id=BUSINESS_CONNECTION_ID,
        message_id=MESSAGE_ID,
    )
    message.answer.assert_awaited_once_with(
        f"Marked business message {MESSAGE_ID} as read for {BUSINESS_CONNECTION_ID}."
    )


async def test_cmd_read_business_message_reports_errors(monkeypatch):
    error = ReadBusinessMessageError(
        "Bad Request: business connection not found", error_code=400
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_read_business_message", AsyncMock(side_effect=error)
    )
    message = _message(
        text=f"/readbusinessmessage {BUSINESS_CONNECTION_ID} {MESSAGE_ID}",
        chat_id=42,
    )

    await commands.cmd_read_business_message(message)

    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Could not mark the business message as read" in args[0]
