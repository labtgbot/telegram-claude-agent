from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import get_managed_bot_token
from bot.services.get_managed_bot_token import (
    GetManagedBotTokenError,
    format_managed_bot_token,
    perform_get_managed_bot_token,
)


MANAGED_BOT_USER_ID = 987654321
MANAGED_BOT_TOKEN = "987654321:AAExampleManagedBotToken"


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
        get_managed_bot_token.httpx, "AsyncClient", lambda *a, **k: client
    )


async def test_perform_get_managed_bot_token_posts_raw_payload(monkeypatch):
    client = _FakeClient(
        response=_FakeResponse({"ok": True, "result": MANAGED_BOT_TOKEN})
    )
    _install_client(monkeypatch, client)

    result = await perform_get_managed_bot_token(
        _bot(), user_id=MANAGED_BOT_USER_ID
    )

    assert result == MANAGED_BOT_TOKEN
    assert client.posted["url"] == (
        "https://api.telegram.org/bot123:abc/getManagedBotToken"
    )
    assert client.posted["json"] == {"user_id": MANAGED_BOT_USER_ID}


async def test_perform_get_managed_bot_token_rejects_invalid_user_id(monkeypatch):
    client = _FakeClient(
        response=_FakeResponse({"ok": True, "result": MANAGED_BOT_TOKEN})
    )
    _install_client(monkeypatch, client)

    with pytest.raises(GetManagedBotTokenError):
        await perform_get_managed_bot_token(_bot(), user_id=0)

    assert client.posted is None


async def test_perform_get_managed_bot_token_raises_on_telegram_error(monkeypatch):
    client = _FakeClient(
        response=_FakeResponse(
            {
                "ok": False,
                "error_code": 403,
                "description": "Forbidden: managed bot token is unavailable",
            }
        )
    )
    _install_client(monkeypatch, client)

    with pytest.raises(GetManagedBotTokenError) as excinfo:
        await perform_get_managed_bot_token(_bot(), user_id=MANAGED_BOT_USER_ID)

    assert excinfo.value.error_code == 403
    assert "managed bot token is unavailable" in str(excinfo.value)


async def test_perform_get_managed_bot_token_raises_on_transport_error(monkeypatch):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(GetManagedBotTokenError):
        await perform_get_managed_bot_token(_bot(), user_id=MANAGED_BOT_USER_ID)


async def test_perform_get_managed_bot_token_rejects_empty_result(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": ""}))
    _install_client(monkeypatch, client)

    with pytest.raises(GetManagedBotTokenError):
        await perform_get_managed_bot_token(_bot(), user_id=MANAGED_BOT_USER_ID)


def test_format_managed_bot_token_escapes_token():
    rendered = format_managed_bot_token(
        user_id=MANAGED_BOT_USER_ID,
        token="123:<unsafe>",
    )

    assert "<b>Managed bot token</b>" in rendered
    assert f"User id: <code>{MANAGED_BOT_USER_ID}</code>" in rendered
    assert "Token: <code>123:&lt;unsafe&gt;</code>" in rendered


def test_parse_managed_bot_token_args():
    assert (
        commands._parse_managed_bot_token_args(
            f"/managedbottoken {MANAGED_BOT_USER_ID}"
        )
        == MANAGED_BOT_USER_ID
    )
    assert commands._parse_managed_bot_token_args("/managedbottoken") is None
    assert commands._parse_managed_bot_token_args("/managedbottoken abc") is None
    assert commands._parse_managed_bot_token_args("/managedbottoken 0") is None
    assert (
        commands._parse_managed_bot_token_args("/managedbottoken 1 extra") is None
    )


def _message(text: str = "/managedbottoken", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_managed_bot_token_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_get_managed_bot_token", AsyncMock())
    message = _message(text=f"/managedbottoken {MANAGED_BOT_USER_ID}", chat_id=42)

    await commands.cmd_managed_bot_token(message)

    commands.perform_get_managed_bot_token.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_managed_bot_token_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_get_managed_bot_token", AsyncMock())
    message = _message(text="/managedbottoken", chat_id=42)

    await commands.cmd_managed_bot_token(message)

    commands.perform_get_managed_bot_token.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "managedbottoken usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_managed_bot_token_fetches_and_formats(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_get_managed_bot_token",
        AsyncMock(return_value=MANAGED_BOT_TOKEN),
    )
    message = _message(text=f"/managedbottoken {MANAGED_BOT_USER_ID}", chat_id=42)

    await commands.cmd_managed_bot_token(message)

    commands.perform_get_managed_bot_token.assert_awaited_once_with(
        message.bot,
        user_id=MANAGED_BOT_USER_ID,
    )
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert MANAGED_BOT_TOKEN in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_managed_bot_token_reports_fetch_errors(monkeypatch):
    error = GetManagedBotTokenError(
        "Forbidden: managed bot token is unavailable", error_code=403
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_get_managed_bot_token", AsyncMock(side_effect=error)
    )
    message = _message(text=f"/managedbottoken {MANAGED_BOT_USER_ID}", chat_id=42)

    await commands.cmd_managed_bot_token(message)

    message.answer.assert_awaited_once_with(
        "Could not fetch the managed bot token. Please try again later."
    )
