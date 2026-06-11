from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import set_managed_bot_access_settings
from bot.services.set_managed_bot_access_settings import (
    SetManagedBotAccessSettingsError,
    format_set_managed_bot_access_settings_result,
    perform_set_managed_bot_access_settings,
)


MANAGED_BOT_USER_ID = 987654321
ADDED_USER_IDS = [111, 222]


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
        set_managed_bot_access_settings.httpx,
        "AsyncClient",
        lambda *a, **k: client,
    )


async def test_perform_set_managed_bot_access_settings_posts_raw_payload(
    monkeypatch,
):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    result = await perform_set_managed_bot_access_settings(
        _bot(),
        user_id=MANAGED_BOT_USER_ID,
        is_access_restricted=True,
        added_user_ids=ADDED_USER_IDS,
    )

    assert result is True
    assert client.posted["url"] == (
        "https://api.telegram.org/bot123:abc/setManagedBotAccessSettings"
    )
    assert client.posted["json"] == {
        "user_id": MANAGED_BOT_USER_ID,
        "settings": {
            "is_access_restricted": True,
            "added_users": ADDED_USER_IDS,
        },
    }


async def test_perform_set_managed_bot_access_settings_can_open_access(
    monkeypatch,
):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    await perform_set_managed_bot_access_settings(
        _bot(),
        user_id=MANAGED_BOT_USER_ID,
        is_access_restricted=False,
    )

    assert client.posted["json"] == {
        "user_id": MANAGED_BOT_USER_ID,
        "settings": {"is_access_restricted": False},
    }


async def test_perform_set_managed_bot_access_settings_rejects_invalid_user_id(
    monkeypatch,
):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    with pytest.raises(SetManagedBotAccessSettingsError):
        await perform_set_managed_bot_access_settings(
            _bot(), user_id=0, is_access_restricted=True
        )

    assert client.posted is None


async def test_perform_set_managed_bot_access_settings_rejects_invalid_added_user(
    monkeypatch,
):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    with pytest.raises(SetManagedBotAccessSettingsError):
        await perform_set_managed_bot_access_settings(
            _bot(),
            user_id=MANAGED_BOT_USER_ID,
            is_access_restricted=True,
            added_user_ids=[0],
        )

    assert client.posted is None


async def test_perform_set_managed_bot_access_settings_raises_on_telegram_error(
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

    with pytest.raises(SetManagedBotAccessSettingsError) as excinfo:
        await perform_set_managed_bot_access_settings(
            _bot(),
            user_id=MANAGED_BOT_USER_ID,
            is_access_restricted=True,
        )

    assert excinfo.value.error_code == 403
    assert "managed bot access is unavailable" in str(excinfo.value)


async def test_perform_set_managed_bot_access_settings_raises_on_transport_error(
    monkeypatch,
):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(SetManagedBotAccessSettingsError):
        await perform_set_managed_bot_access_settings(
            _bot(),
            user_id=MANAGED_BOT_USER_ID,
            is_access_restricted=True,
        )


async def test_perform_set_managed_bot_access_settings_rejects_unexpected_result(
    monkeypatch,
):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": False}))
    _install_client(monkeypatch, client)

    with pytest.raises(SetManagedBotAccessSettingsError):
        await perform_set_managed_bot_access_settings(
            _bot(),
            user_id=MANAGED_BOT_USER_ID,
            is_access_restricted=True,
        )


def test_format_set_managed_bot_access_settings_result():
    rendered = format_set_managed_bot_access_settings_result(
        user_id=MANAGED_BOT_USER_ID,
        is_access_restricted=True,
        added_user_ids=ADDED_USER_IDS,
    )

    assert "<b>Managed bot access settings updated</b>" in rendered
    assert f"User id: <code>{MANAGED_BOT_USER_ID}</code>" in rendered
    assert "Access restricted: <code>true</code>" in rendered
    assert "Added users: <code>2</code>" in rendered
    assert "<code>111</code>" in rendered
    assert "<code>222</code>" in rendered


def test_parse_set_managed_bot_access_settings_args():
    assert commands._parse_set_managed_bot_access_settings_args(
        f"/setmanagedbotaccess {MANAGED_BOT_USER_ID} restricted 111 222 confirm"
    ) == (MANAGED_BOT_USER_ID, True, ADDED_USER_IDS, True)
    assert commands._parse_set_managed_bot_access_settings_args(
        f"/setmanagedbotaccess {MANAGED_BOT_USER_ID} open"
    ) == (MANAGED_BOT_USER_ID, False, [], False)
    assert (
        commands._parse_set_managed_bot_access_settings_args(
            "/setmanagedbotaccess"
        )
        is None
    )
    assert (
        commands._parse_set_managed_bot_access_settings_args(
            "/setmanagedbotaccess abc restricted"
        )
        is None
    )
    assert (
        commands._parse_set_managed_bot_access_settings_args(
            "/setmanagedbotaccess 0 restricted"
        )
        is None
    )
    assert (
        commands._parse_set_managed_bot_access_settings_args(
            f"/setmanagedbotaccess {MANAGED_BOT_USER_ID} restricted nope"
        )
        is None
    )


def _message(text: str = "/setmanagedbotaccess", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_set_managed_bot_access_settings_rejects_unlisted_chat(
    monkeypatch,
):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_set_managed_bot_access_settings", AsyncMock()
    )
    message = _message(
        text=f"/setmanagedbotaccess {MANAGED_BOT_USER_ID} restricted confirm",
        chat_id=42,
    )

    await commands.cmd_set_managed_bot_access_settings(message)

    commands.perform_set_managed_bot_access_settings.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_set_managed_bot_access_settings_shows_usage_without_args(
    monkeypatch,
):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_set_managed_bot_access_settings", AsyncMock()
    )
    message = _message(text="/setmanagedbotaccess", chat_id=42)

    await commands.cmd_set_managed_bot_access_settings(message)

    commands.perform_set_managed_bot_access_settings.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "setmanagedbotaccess usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_set_managed_bot_access_settings_requires_confirmation(
    monkeypatch,
):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_set_managed_bot_access_settings", AsyncMock()
    )
    message = _message(
        text=f"/setmanagedbotaccess {MANAGED_BOT_USER_ID} restricted 111",
        chat_id=42,
    )

    await commands.cmd_set_managed_bot_access_settings(message)

    commands.perform_set_managed_bot_access_settings.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "confirmation required" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_set_managed_bot_access_settings_sets_and_formats(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_set_managed_bot_access_settings",
        AsyncMock(return_value=True),
    )
    message = _message(
        text=(
            f"/setmanagedbotaccess {MANAGED_BOT_USER_ID} "
            "restricted 111 222 confirm"
        ),
        chat_id=42,
    )

    await commands.cmd_set_managed_bot_access_settings(message)

    commands.perform_set_managed_bot_access_settings.assert_awaited_once_with(
        message.bot,
        user_id=MANAGED_BOT_USER_ID,
        is_access_restricted=True,
        added_user_ids=ADDED_USER_IDS,
    )
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "Managed bot access settings updated" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_set_managed_bot_access_settings_reports_set_errors(
    monkeypatch,
):
    error = SetManagedBotAccessSettingsError(
        "Forbidden: managed bot access is unavailable", error_code=403
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_set_managed_bot_access_settings",
        AsyncMock(side_effect=error),
    )
    message = _message(
        text=f"/setmanagedbotaccess {MANAGED_BOT_USER_ID} restricted confirm",
        chat_id=42,
    )

    await commands.cmd_set_managed_bot_access_settings(message)

    message.answer.assert_awaited_once_with(
        "Could not set the managed bot access settings. Please try again later."
    )
