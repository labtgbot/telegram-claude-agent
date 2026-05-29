from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import set_business_account_gift_settings
from bot.services.set_business_account_gift_settings import (
    ACCEPTED_GIFT_TYPE_KEYS,
    SetBusinessAccountGiftSettingsError,
    perform_set_business_account_gift_settings,
)


BUSINESS_CONNECTION_ID = "bizconn-123"
ACCEPTED_GIFT_TYPES = {
    "unlimited_gifts": True,
    "limited_gifts": False,
    "unique_gifts": True,
    "premium_subscription": False,
    "gifts_from_channels": True,
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
        set_business_account_gift_settings.httpx,
        "AsyncClient",
        lambda *a, **k: client,
    )


async def test_perform_set_business_account_gift_settings_posts_raw_payload(
    monkeypatch,
):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    result = await perform_set_business_account_gift_settings(
        _bot(),
        business_connection_id=f" {BUSINESS_CONNECTION_ID} ",
        show_gift_button=True,
        accepted_gift_types=ACCEPTED_GIFT_TYPES,
    )

    assert result is True
    assert client.posted["url"] == (
        "https://api.telegram.org/bot123:abc/setBusinessAccountGiftSettings"
    )
    assert client.posted["json"] == {
        "business_connection_id": BUSINESS_CONNECTION_ID,
        "show_gift_button": True,
        "accepted_gift_types": ACCEPTED_GIFT_TYPES,
    }


async def test_perform_set_business_account_gift_settings_rejects_invalid_args(
    monkeypatch,
):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    invalid_cases = [
        {
            "business_connection_id": "",
            "show_gift_button": True,
            "accepted_gift_types": ACCEPTED_GIFT_TYPES,
        },
        {
            "business_connection_id": BUSINESS_CONNECTION_ID,
            "show_gift_button": "true",
            "accepted_gift_types": ACCEPTED_GIFT_TYPES,
        },
        {
            "business_connection_id": BUSINESS_CONNECTION_ID,
            "show_gift_button": True,
            "accepted_gift_types": {
                key: value
                for key, value in ACCEPTED_GIFT_TYPES.items()
                if key != "gifts_from_channels"
            },
        },
        {
            "business_connection_id": BUSINESS_CONNECTION_ID,
            "show_gift_button": True,
            "accepted_gift_types": {
                **ACCEPTED_GIFT_TYPES,
                "unlimited_gifts": "true",
            },
        },
        {
            "business_connection_id": BUSINESS_CONNECTION_ID,
            "show_gift_button": True,
            "accepted_gift_types": {
                **ACCEPTED_GIFT_TYPES,
                "unknown": True,
            },
        },
    ]
    for kwargs in invalid_cases:
        with pytest.raises(SetBusinessAccountGiftSettingsError):
            await perform_set_business_account_gift_settings(_bot(), **kwargs)

    assert client.posted is None


async def test_perform_set_business_account_gift_settings_raises_on_telegram_error(
    monkeypatch,
):
    client = _FakeClient(
        response=_FakeResponse(
            {
                "ok": False,
                "error_code": 403,
                "description": "Forbidden: bot lacks can_change_gift_settings right",
            }
        )
    )
    _install_client(monkeypatch, client)

    with pytest.raises(SetBusinessAccountGiftSettingsError) as excinfo:
        await perform_set_business_account_gift_settings(
            _bot(),
            business_connection_id=BUSINESS_CONNECTION_ID,
            show_gift_button=True,
            accepted_gift_types=ACCEPTED_GIFT_TYPES,
        )

    assert excinfo.value.error_code == 403
    assert "can_change_gift_settings" in str(excinfo.value)


async def test_perform_set_business_account_gift_settings_raises_on_transport_error(
    monkeypatch,
):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(SetBusinessAccountGiftSettingsError):
        await perform_set_business_account_gift_settings(
            _bot(),
            business_connection_id=BUSINESS_CONNECTION_ID,
            show_gift_button=True,
            accepted_gift_types=ACCEPTED_GIFT_TYPES,
        )


def test_parse_set_business_account_gift_settings_args():
    assert commands._parse_set_business_account_gift_settings_args(
        "/setbusinessaccountgiftsettings "
        f"{BUSINESS_CONNECTION_ID} show_gift_button=true "
        "unlimited_gifts=true limited_gifts=false unique_gifts=true "
        "premium_subscription=false gifts_from_channels=true"
    ) == (BUSINESS_CONNECTION_ID, True, ACCEPTED_GIFT_TYPES)
    assert commands._parse_set_business_account_gift_settings_args(
        "/setbusinessaccountgiftsettings "
        f"{BUSINESS_CONNECTION_ID} show_gift_button=false "
        "unlimited_gifts=false limited_gifts=false unique_gifts=false "
        "premium_subscription=false gifts_from_channels=false"
    ) == (
        BUSINESS_CONNECTION_ID,
        False,
        {key: False for key in ACCEPTED_GIFT_TYPE_KEYS},
    )
    assert commands._parse_set_business_account_gift_settings_args(
        "/setbusinessaccountgiftsettings"
    ) is None
    assert commands._parse_set_business_account_gift_settings_args(
        f"/setbusinessaccountgiftsettings {BUSINESS_CONNECTION_ID}"
    ) is None
    assert commands._parse_set_business_account_gift_settings_args(
        "/setbusinessaccountgiftsettings "
        f"{BUSINESS_CONNECTION_ID} show_gift_button=yes "
        "unlimited_gifts=true limited_gifts=false unique_gifts=true "
        "premium_subscription=false gifts_from_channels=true"
    ) is None
    assert commands._parse_set_business_account_gift_settings_args(
        "/setbusinessaccountgiftsettings "
        f"{BUSINESS_CONNECTION_ID} show_gift_button=true "
        "unlimited_gifts=true limited_gifts=false unique_gifts=true "
        "premium_subscription=false"
    ) is None


def _message(text: str = "/setbusinessaccountgiftsettings", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_set_business_account_gift_settings_rejects_unlisted_chat(
    monkeypatch,
):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_set_business_account_gift_settings", AsyncMock()
    )
    message = _message(
        text="/setbusinessaccountgiftsettings "
        f"{BUSINESS_CONNECTION_ID} show_gift_button=true "
        "unlimited_gifts=true limited_gifts=false unique_gifts=true "
        "premium_subscription=false gifts_from_channels=true",
        chat_id=42,
    )

    await commands.cmd_set_business_account_gift_settings(message)

    commands.perform_set_business_account_gift_settings.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_set_business_account_gift_settings_shows_usage_without_args(
    monkeypatch,
):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_set_business_account_gift_settings", AsyncMock()
    )
    message = _message(text="/setbusinessaccountgiftsettings", chat_id=42)

    await commands.cmd_set_business_account_gift_settings(message)

    commands.perform_set_business_account_gift_settings.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "setbusinessaccountgiftsettings usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_set_business_account_gift_settings_updates_settings(
    monkeypatch,
):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_set_business_account_gift_settings",
        AsyncMock(return_value=True),
    )
    message = _message(
        text="/setbusinessaccountgiftsettings "
        f"{BUSINESS_CONNECTION_ID} show_gift_button=true "
        "unlimited_gifts=true limited_gifts=false unique_gifts=true "
        "premium_subscription=false gifts_from_channels=true",
        chat_id=42,
    )

    await commands.cmd_set_business_account_gift_settings(message)

    commands.perform_set_business_account_gift_settings.assert_awaited_once_with(
        message.bot,
        business_connection_id=BUSINESS_CONNECTION_ID,
        show_gift_button=True,
        accepted_gift_types=ACCEPTED_GIFT_TYPES,
    )
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "setBusinessAccountGiftSettings" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_set_business_account_gift_settings_reports_errors(monkeypatch):
    error = SetBusinessAccountGiftSettingsError(
        "Forbidden: bot lacks can_change_gift_settings right", error_code=403
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_set_business_account_gift_settings",
        AsyncMock(side_effect=error),
    )
    message = _message(
        text="/setbusinessaccountgiftsettings "
        f"{BUSINESS_CONNECTION_ID} show_gift_button=true "
        "unlimited_gifts=true limited_gifts=false unique_gifts=true "
        "premium_subscription=false gifts_from_channels=true",
        chat_id=42,
    )

    await commands.cmd_set_business_account_gift_settings(message)

    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Could not set the business account gift settings" in args[0]
