from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import set_business_account_username
from bot.services.set_business_account_username import (
    MAX_BUSINESS_ACCOUNT_USERNAME_LENGTH,
    MIN_BUSINESS_ACCOUNT_USERNAME_LENGTH,
    SetBusinessAccountUsernameError,
    perform_set_business_account_username,
)


BUSINESS_CONNECTION_ID = "bizconn-123"
USERNAME = "alice_example"


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
        set_business_account_username.httpx, "AsyncClient", lambda *a, **k: client
    )


async def test_perform_set_business_account_username_posts_raw_payload(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    result = await perform_set_business_account_username(
        _bot(),
        business_connection_id=f" {BUSINESS_CONNECTION_ID} ",
        username=f" @{USERNAME} ",
    )

    assert result is True
    assert client.posted["url"] == (
        "https://api.telegram.org/bot123:abc/setBusinessAccountUsername"
    )
    assert client.posted["json"] == {
        "business_connection_id": BUSINESS_CONNECTION_ID,
        "username": USERNAME,
    }


async def test_perform_set_business_account_username_rejects_invalid_args(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    invalid_cases = [
        {"business_connection_id": "", "username": USERNAME},
        {"business_connection_id": BUSINESS_CONNECTION_ID, "username": ""},
        {
            "business_connection_id": BUSINESS_CONNECTION_ID,
            "username": "x" * (MIN_BUSINESS_ACCOUNT_USERNAME_LENGTH - 1),
        },
        {
            "business_connection_id": BUSINESS_CONNECTION_ID,
            "username": "x" * (MAX_BUSINESS_ACCOUNT_USERNAME_LENGTH + 1),
        },
    ]
    for kwargs in invalid_cases:
        with pytest.raises(SetBusinessAccountUsernameError):
            await perform_set_business_account_username(_bot(), **kwargs)

    assert client.posted is None


async def test_perform_set_business_account_username_raises_on_telegram_error(
    monkeypatch,
):
    client = _FakeClient(
        response=_FakeResponse(
            {
                "ok": False,
                "error_code": 400,
                "description": "Bad Request: username is invalid",
            }
        )
    )
    _install_client(monkeypatch, client)

    with pytest.raises(SetBusinessAccountUsernameError) as excinfo:
        await perform_set_business_account_username(
            _bot(),
            business_connection_id=BUSINESS_CONNECTION_ID,
            username=USERNAME,
        )

    assert excinfo.value.error_code == 400
    assert "username is invalid" in str(excinfo.value)


async def test_perform_set_business_account_username_raises_on_transport_error(
    monkeypatch,
):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(SetBusinessAccountUsernameError):
        await perform_set_business_account_username(
            _bot(),
            business_connection_id=BUSINESS_CONNECTION_ID,
            username=USERNAME,
        )


def test_parse_set_business_account_username_args():
    assert commands._parse_set_business_account_username_args(
        f"/setbusinessaccountusername {BUSINESS_CONNECTION_ID} @{USERNAME}"
    ) == (BUSINESS_CONNECTION_ID, USERNAME)
    assert commands._parse_set_business_account_username_args(
        "/setbusinessaccountusername"
    ) is None
    assert commands._parse_set_business_account_username_args(
        f"/setbusinessaccountusername {BUSINESS_CONNECTION_ID}"
    ) is None
    assert commands._parse_set_business_account_username_args(
        f"/setbusinessaccountusername {BUSINESS_CONNECTION_ID} "
        f"{'x' * (MAX_BUSINESS_ACCOUNT_USERNAME_LENGTH + 1)}"
    ) is None


def _message(text: str = "/setbusinessaccountusername", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_set_business_account_username_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_set_business_account_username", AsyncMock())
    message = _message(
        text=f"/setbusinessaccountusername {BUSINESS_CONNECTION_ID} {USERNAME}",
        chat_id=42,
    )

    await commands.cmd_set_business_account_username(message)

    commands.perform_set_business_account_username.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_set_business_account_username_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_set_business_account_username", AsyncMock())
    message = _message(text="/setbusinessaccountusername", chat_id=42)

    await commands.cmd_set_business_account_username(message)

    commands.perform_set_business_account_username.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "setbusinessaccountusername usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_set_business_account_username_sets_username(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_set_business_account_username",
        AsyncMock(return_value=True),
    )
    message = _message(
        text=f"/setbusinessaccountusername {BUSINESS_CONNECTION_ID} @{USERNAME}",
        chat_id=42,
    )

    await commands.cmd_set_business_account_username(message)

    commands.perform_set_business_account_username.assert_awaited_once_with(
        message.bot,
        business_connection_id=BUSINESS_CONNECTION_ID,
        username=USERNAME,
    )
    message.answer.assert_awaited_once_with(
        f"Set business account username for {BUSINESS_CONNECTION_ID}."
    )


async def test_cmd_set_business_account_username_reports_errors(monkeypatch):
    error = SetBusinessAccountUsernameError(
        "Bad Request: username is invalid", error_code=400
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_set_business_account_username", AsyncMock(side_effect=error)
    )
    message = _message(
        text=f"/setbusinessaccountusername {BUSINESS_CONNECTION_ID} {USERNAME}",
        chat_id=42,
    )

    await commands.cmd_set_business_account_username(message)

    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Could not set the business account username" in args[0]
