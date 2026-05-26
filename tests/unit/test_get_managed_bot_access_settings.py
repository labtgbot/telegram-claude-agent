from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import get_managed_bot_access_settings
from bot.services.get_managed_bot_access_settings import (
    GetManagedBotAccessSettingsError,
    format_managed_bot_access_settings,
    perform_get_managed_bot_access_settings,
)


MANAGED_BOT_USER_ID = 987654321
ACCESS_SETTINGS = {
    "is_access_restricted": True,
    "added_users": [
        {
            "id": 111,
            "is_bot": False,
            "first_name": "Alice",
            "last_name": "<Ops>",
            "username": "alice_ops",
        }
    ],
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
        get_managed_bot_access_settings.httpx,
        "AsyncClient",
        lambda *a, **k: client,
    )


async def test_perform_get_managed_bot_access_settings_posts_raw_payload(
    monkeypatch,
):
    client = _FakeClient(
        response=_FakeResponse({"ok": True, "result": ACCESS_SETTINGS})
    )
    _install_client(monkeypatch, client)

    result = await perform_get_managed_bot_access_settings(
        _bot(), user_id=MANAGED_BOT_USER_ID
    )

    assert result == ACCESS_SETTINGS
    assert client.posted["url"] == (
        "https://api.telegram.org/bot123:abc/getManagedBotAccessSettings"
    )
    assert client.posted["json"] == {"user_id": MANAGED_BOT_USER_ID}


async def test_perform_get_managed_bot_access_settings_rejects_invalid_user_id(
    monkeypatch,
):
    client = _FakeClient(
        response=_FakeResponse({"ok": True, "result": ACCESS_SETTINGS})
    )
    _install_client(monkeypatch, client)

    with pytest.raises(GetManagedBotAccessSettingsError):
        await perform_get_managed_bot_access_settings(_bot(), user_id=0)

    assert client.posted is None


async def test_perform_get_managed_bot_access_settings_raises_on_telegram_error(
    monkeypatch,
):
    client = _FakeClient(
        response=_FakeResponse(
            {
                "ok": False,
                "error_code": 403,
                "description": "Forbidden: managed bot access is unavailable",
            }
        )
    )
    _install_client(monkeypatch, client)

    with pytest.raises(GetManagedBotAccessSettingsError) as excinfo:
        await perform_get_managed_bot_access_settings(
            _bot(), user_id=MANAGED_BOT_USER_ID
        )

    assert excinfo.value.error_code == 403
    assert "managed bot access is unavailable" in str(excinfo.value)


async def test_perform_get_managed_bot_access_settings_raises_on_transport_error(
    monkeypatch,
):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(GetManagedBotAccessSettingsError):
        await perform_get_managed_bot_access_settings(
            _bot(), user_id=MANAGED_BOT_USER_ID
        )


async def test_perform_get_managed_bot_access_settings_rejects_invalid_result(
    monkeypatch,
):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": ""}))
    _install_client(monkeypatch, client)

    with pytest.raises(GetManagedBotAccessSettingsError):
        await perform_get_managed_bot_access_settings(
            _bot(), user_id=MANAGED_BOT_USER_ID
        )


async def test_perform_get_managed_bot_access_settings_requires_flag(
    monkeypatch,
):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": {}}))
    _install_client(monkeypatch, client)

    with pytest.raises(GetManagedBotAccessSettingsError):
        await perform_get_managed_bot_access_settings(
            _bot(), user_id=MANAGED_BOT_USER_ID
        )


def test_format_managed_bot_access_settings_escapes_user_data():
    rendered = format_managed_bot_access_settings(
        user_id=MANAGED_BOT_USER_ID,
        settings=ACCESS_SETTINGS,
    )

    assert "<b>Managed bot access settings</b>" in rendered
    assert f"User id: <code>{MANAGED_BOT_USER_ID}</code>" in rendered
    assert "Access restricted: <code>true</code>" in rendered
    assert "Added users: <code>1</code>" in rendered
    assert "Alice &lt;Ops&gt; @alice_ops" in rendered


def test_parse_managed_bot_access_settings_args():
    assert (
        commands._parse_managed_bot_access_settings_args(
            f"/managedbotaccess {MANAGED_BOT_USER_ID}"
        )
        == MANAGED_BOT_USER_ID
    )
    assert (
        commands._parse_managed_bot_access_settings_args("/managedbotaccess")
        is None
    )
    assert (
        commands._parse_managed_bot_access_settings_args("/managedbotaccess abc")
        is None
    )
    assert (
        commands._parse_managed_bot_access_settings_args("/managedbotaccess 0")
        is None
    )
    assert (
        commands._parse_managed_bot_access_settings_args(
            "/managedbotaccess 1 extra"
        )
        is None
    )


def _message(text: str = "/managedbotaccess", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_managed_bot_access_settings_rejects_unlisted_chat(
    monkeypatch,
):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_get_managed_bot_access_settings", AsyncMock()
    )
    message = _message(text=f"/managedbotaccess {MANAGED_BOT_USER_ID}", chat_id=42)

    await commands.cmd_managed_bot_access_settings(message)

    commands.perform_get_managed_bot_access_settings.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_managed_bot_access_settings_shows_usage_without_args(
    monkeypatch,
):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_get_managed_bot_access_settings", AsyncMock()
    )
    message = _message(text="/managedbotaccess", chat_id=42)

    await commands.cmd_managed_bot_access_settings(message)

    commands.perform_get_managed_bot_access_settings.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "managedbotaccess usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_managed_bot_access_settings_fetches_and_formats(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_get_managed_bot_access_settings",
        AsyncMock(return_value=ACCESS_SETTINGS),
    )
    message = _message(text=f"/managedbotaccess {MANAGED_BOT_USER_ID}", chat_id=42)

    await commands.cmd_managed_bot_access_settings(message)

    commands.perform_get_managed_bot_access_settings.assert_awaited_once_with(
        message.bot,
        user_id=MANAGED_BOT_USER_ID,
    )
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "Managed bot access settings" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_managed_bot_access_settings_reports_fetch_errors(monkeypatch):
    error = GetManagedBotAccessSettingsError(
        "Forbidden: managed bot access is unavailable", error_code=403
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_get_managed_bot_access_settings",
        AsyncMock(side_effect=error),
    )
    message = _message(text=f"/managedbotaccess {MANAGED_BOT_USER_ID}", chat_id=42)

    await commands.cmd_managed_bot_access_settings(message)

    message.answer.assert_awaited_once_with(
        "Could not fetch the managed bot access settings: "
        "Forbidden: managed bot access is unavailable"
    )
