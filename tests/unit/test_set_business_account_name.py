from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import set_business_account_name
from bot.services.set_business_account_name import (
    MAX_BUSINESS_ACCOUNT_NAME_LENGTH,
    SetBusinessAccountNameError,
    perform_set_business_account_name,
)


BUSINESS_CONNECTION_ID = "bizconn-123"
FIRST_NAME = "Alice"
LAST_NAME = "Example"


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
        set_business_account_name.httpx, "AsyncClient", lambda *a, **k: client
    )


async def test_perform_set_business_account_name_posts_raw_payload(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    result = await perform_set_business_account_name(
        _bot(),
        business_connection_id=f" {BUSINESS_CONNECTION_ID} ",
        first_name=f" {FIRST_NAME} ",
        last_name=f" {LAST_NAME} ",
    )

    assert result is True
    assert client.posted["url"] == (
        "https://api.telegram.org/bot123:abc/setBusinessAccountName"
    )
    assert client.posted["json"] == {
        "business_connection_id": BUSINESS_CONNECTION_ID,
        "first_name": FIRST_NAME,
        "last_name": LAST_NAME,
    }


async def test_perform_set_business_account_name_omits_missing_last_name(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    await perform_set_business_account_name(
        _bot(),
        business_connection_id=BUSINESS_CONNECTION_ID,
        first_name=FIRST_NAME,
    )

    assert client.posted["json"] == {
        "business_connection_id": BUSINESS_CONNECTION_ID,
        "first_name": FIRST_NAME,
    }


async def test_perform_set_business_account_name_rejects_invalid_args(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    invalid_cases = [
        {"business_connection_id": "", "first_name": FIRST_NAME},
        {"business_connection_id": BUSINESS_CONNECTION_ID, "first_name": ""},
        {
            "business_connection_id": BUSINESS_CONNECTION_ID,
            "first_name": "x" * (MAX_BUSINESS_ACCOUNT_NAME_LENGTH + 1),
        },
        {
            "business_connection_id": BUSINESS_CONNECTION_ID,
            "first_name": FIRST_NAME,
            "last_name": "x" * (MAX_BUSINESS_ACCOUNT_NAME_LENGTH + 1),
        },
    ]
    for kwargs in invalid_cases:
        with pytest.raises(SetBusinessAccountNameError):
            await perform_set_business_account_name(_bot(), **kwargs)

    assert client.posted is None


async def test_perform_set_business_account_name_raises_on_telegram_error(monkeypatch):
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

    with pytest.raises(SetBusinessAccountNameError) as excinfo:
        await perform_set_business_account_name(
            _bot(),
            business_connection_id=BUSINESS_CONNECTION_ID,
            first_name=FIRST_NAME,
        )

    assert excinfo.value.error_code == 400
    assert "business connection not found" in str(excinfo.value)


async def test_perform_set_business_account_name_raises_on_transport_error(monkeypatch):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(SetBusinessAccountNameError):
        await perform_set_business_account_name(
            _bot(),
            business_connection_id=BUSINESS_CONNECTION_ID,
            first_name=FIRST_NAME,
        )


def test_parse_set_business_account_name_args():
    assert commands._parse_set_business_account_name_args(
        f"/setbusinessaccountname {BUSINESS_CONNECTION_ID} {FIRST_NAME}"
    ) == (BUSINESS_CONNECTION_ID, FIRST_NAME, None)
    assert commands._parse_set_business_account_name_args(
        f"/setbusinessaccountname {BUSINESS_CONNECTION_ID} {FIRST_NAME} {LAST_NAME}"
    ) == (BUSINESS_CONNECTION_ID, FIRST_NAME, LAST_NAME)
    assert commands._parse_set_business_account_name_args(
        "/setbusinessaccountname"
    ) is None
    assert commands._parse_set_business_account_name_args(
        f"/setbusinessaccountname {BUSINESS_CONNECTION_ID}"
    ) is None
    assert commands._parse_set_business_account_name_args(
        f"/setbusinessaccountname {BUSINESS_CONNECTION_ID} "
        f"{'x' * (MAX_BUSINESS_ACCOUNT_NAME_LENGTH + 1)}"
    ) is None


def _message(text: str = "/setbusinessaccountname", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_set_business_account_name_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_set_business_account_name", AsyncMock())
    message = _message(
        text=f"/setbusinessaccountname {BUSINESS_CONNECTION_ID} {FIRST_NAME}",
        chat_id=42,
    )

    await commands.cmd_set_business_account_name(message)

    commands.perform_set_business_account_name.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_set_business_account_name_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_set_business_account_name", AsyncMock())
    message = _message(text="/setbusinessaccountname", chat_id=42)

    await commands.cmd_set_business_account_name(message)

    commands.perform_set_business_account_name.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "setbusinessaccountname usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_set_business_account_name_sets_name(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_set_business_account_name",
        AsyncMock(return_value=True),
    )
    message = _message(
        text=f"/setbusinessaccountname {BUSINESS_CONNECTION_ID} {FIRST_NAME} {LAST_NAME}",
        chat_id=42,
    )

    await commands.cmd_set_business_account_name(message)

    commands.perform_set_business_account_name.assert_awaited_once_with(
        message.bot,
        business_connection_id=BUSINESS_CONNECTION_ID,
        first_name=FIRST_NAME,
        last_name=LAST_NAME,
    )
    message.answer.assert_awaited_once_with(
        f"Set business account name for {BUSINESS_CONNECTION_ID}."
    )


async def test_cmd_set_business_account_name_reports_errors(monkeypatch):
    error = SetBusinessAccountNameError(
        "Bad Request: business connection not found", error_code=400
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_set_business_account_name", AsyncMock(side_effect=error)
    )
    message = _message(
        text=f"/setbusinessaccountname {BUSINESS_CONNECTION_ID} {FIRST_NAME}",
        chat_id=42,
    )

    await commands.cmd_set_business_account_name(message)

    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Could not set the business account name" in args[0]
