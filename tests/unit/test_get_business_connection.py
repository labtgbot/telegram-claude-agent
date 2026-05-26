from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import get_business_connection
from bot.services.get_business_connection import (
    GetBusinessConnectionError,
    format_business_connection,
    perform_get_business_connection,
)


BUSINESS_CONNECTION_ID = "bizconn-123"
BUSINESS_CONNECTION = {
    "id": BUSINESS_CONNECTION_ID,
    "user": {
        "id": 12345,
        "is_bot": False,
        "first_name": "Alice <Owner>",
        "username": "alice_owner",
    },
    "user_chat_id": 777000,
    "date": 1710000000,
    "can_reply": True,
    "is_enabled": True,
}


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
        get_business_connection.httpx, "AsyncClient", lambda *a, **k: client
    )


async def test_perform_get_business_connection_posts_raw_payload(monkeypatch):
    client = _FakeClient(
        response=_FakeResponse({"ok": True, "result": BUSINESS_CONNECTION})
    )
    _install_client(monkeypatch, client)

    result = await perform_get_business_connection(
        _bot(), business_connection_id=BUSINESS_CONNECTION_ID
    )

    assert result == BUSINESS_CONNECTION
    assert client.posted["url"] == (
        "https://api.telegram.org/bot123:abc/getBusinessConnection"
    )
    assert client.posted["json"] == {
        "business_connection_id": BUSINESS_CONNECTION_ID,
    }


async def test_perform_get_business_connection_rejects_missing_id(monkeypatch):
    client = _FakeClient(
        response=_FakeResponse({"ok": True, "result": BUSINESS_CONNECTION})
    )
    _install_client(monkeypatch, client)

    with pytest.raises(GetBusinessConnectionError):
        await perform_get_business_connection(_bot(), business_connection_id="")

    assert client.posted is None


async def test_perform_get_business_connection_raises_on_telegram_error(monkeypatch):
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

    with pytest.raises(GetBusinessConnectionError) as excinfo:
        await perform_get_business_connection(
            _bot(), business_connection_id=BUSINESS_CONNECTION_ID
        )

    assert excinfo.value.error_code == 400
    assert "business connection not found" in str(excinfo.value)


async def test_perform_get_business_connection_raises_on_transport_error(monkeypatch):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(GetBusinessConnectionError):
        await perform_get_business_connection(
            _bot(), business_connection_id=BUSINESS_CONNECTION_ID
        )


def test_format_business_connection_escapes_owner_fields():
    rendered = format_business_connection(BUSINESS_CONNECTION)

    assert "<b>Business connection</b>" in rendered
    assert "ID: <code>bizconn-123</code>" in rendered
    assert "Owner: Alice &lt;Owner&gt; (@alice_owner, id 12345)" in rendered
    assert "User chat id: <code>777000</code>" in rendered
    assert "Can reply: yes" in rendered
    assert "Enabled: yes" in rendered


def test_parse_business_connection_args():
    assert (
        commands._parse_business_connection_args(
            f"/businessconnection {BUSINESS_CONNECTION_ID}"
        )
        == BUSINESS_CONNECTION_ID
    )
    assert commands._parse_business_connection_args("/businessconnection") is None
    assert (
        commands._parse_business_connection_args("/businessconnection one two") is None
    )


def _message(text: str = "/businessconnection", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_business_connection_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_get_business_connection", AsyncMock())
    message = _message(
        text=f"/businessconnection {BUSINESS_CONNECTION_ID}", chat_id=42
    )

    await commands.cmd_business_connection(message)

    commands.perform_get_business_connection.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_business_connection_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_get_business_connection", AsyncMock())
    message = _message(text="/businessconnection", chat_id=42)

    await commands.cmd_business_connection(message)

    commands.perform_get_business_connection.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "businessconnection usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_business_connection_fetches_and_formats(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_get_business_connection",
        AsyncMock(return_value=BUSINESS_CONNECTION),
    )
    message = _message(
        text=f"/businessconnection {BUSINESS_CONNECTION_ID}", chat_id=42
    )

    await commands.cmd_business_connection(message)

    commands.perform_get_business_connection.assert_awaited_once_with(
        message.bot,
        business_connection_id=BUSINESS_CONNECTION_ID,
    )
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "Business connection" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_business_connection_reports_fetch_errors(monkeypatch):
    error = GetBusinessConnectionError(
        "Bad Request: business connection not found", error_code=400
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_get_business_connection", AsyncMock(side_effect=error)
    )
    message = _message(
        text=f"/businessconnection {BUSINESS_CONNECTION_ID}", chat_id=42
    )

    await commands.cmd_business_connection(message)

    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Could not fetch the business connection" in args[0]
