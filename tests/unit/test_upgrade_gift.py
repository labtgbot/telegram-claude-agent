from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import upgrade_gift
from bot.services.upgrade_gift import (
    UpgradeGiftError,
    format_upgrade_gift_result,
    perform_upgrade_gift,
)


BUSINESS_CONNECTION_ID = "bizconn-123"
OWNED_GIFT_ID = "owned-gift-1"


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
    monkeypatch.setattr(upgrade_gift.httpx, "AsyncClient", lambda *a, **k: client)


async def test_perform_upgrade_gift_posts_raw_payload(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    result = await perform_upgrade_gift(
        _bot(),
        business_connection_id=f" {BUSINESS_CONNECTION_ID} ",
        owned_gift_id=f" {OWNED_GIFT_ID} ",
        keep_original_details=True,
    )

    assert result is True
    assert client.posted["url"] == "https://api.telegram.org/bot123:abc/upgradeGift"
    assert client.posted["json"] == {
        "business_connection_id": BUSINESS_CONNECTION_ID,
        "owned_gift_id": OWNED_GIFT_ID,
        "keep_original_details": True,
    }


async def test_perform_upgrade_gift_omits_optional_flag(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    await perform_upgrade_gift(
        _bot(),
        business_connection_id=BUSINESS_CONNECTION_ID,
        owned_gift_id=OWNED_GIFT_ID,
    )

    assert client.posted["json"] == {
        "business_connection_id": BUSINESS_CONNECTION_ID,
        "owned_gift_id": OWNED_GIFT_ID,
    }


async def test_perform_upgrade_gift_rejects_invalid_args(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    invalid_cases = [
        {"business_connection_id": "", "owned_gift_id": OWNED_GIFT_ID},
        {"business_connection_id": BUSINESS_CONNECTION_ID, "owned_gift_id": ""},
        {
            "business_connection_id": BUSINESS_CONNECTION_ID,
            "owned_gift_id": OWNED_GIFT_ID,
            "keep_original_details": "true",
        },
    ]
    for kwargs in invalid_cases:
        with pytest.raises(UpgradeGiftError):
            await perform_upgrade_gift(_bot(), **kwargs)

    assert client.posted is None


async def test_perform_upgrade_gift_raises_on_telegram_error(monkeypatch):
    client = _FakeClient(
        response=_FakeResponse(
            {
                "ok": False,
                "error_code": 403,
                "description": "Forbidden: bot lacks can_transfer_and_upgrade_gifts right",
            }
        )
    )
    _install_client(monkeypatch, client)

    with pytest.raises(UpgradeGiftError) as excinfo:
        await perform_upgrade_gift(
            _bot(),
            business_connection_id=BUSINESS_CONNECTION_ID,
            owned_gift_id=OWNED_GIFT_ID,
        )

    assert excinfo.value.error_code == 403
    assert "can_transfer_and_upgrade_gifts" in str(excinfo.value)


async def test_perform_upgrade_gift_raises_on_transport_error(monkeypatch):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(UpgradeGiftError):
        await perform_upgrade_gift(
            _bot(),
            business_connection_id=BUSINESS_CONNECTION_ID,
            owned_gift_id=OWNED_GIFT_ID,
        )


async def test_perform_upgrade_gift_rejects_unexpected_result(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": {}}))
    _install_client(monkeypatch, client)

    with pytest.raises(UpgradeGiftError):
        await perform_upgrade_gift(
            _bot(),
            business_connection_id=BUSINESS_CONNECTION_ID,
            owned_gift_id=OWNED_GIFT_ID,
        )


def test_format_upgrade_gift_result_escapes_values():
    rendered = format_upgrade_gift_result(
        business_connection_id="biz<conn>",
        owned_gift_id="owned<gift>",
        keep_original_details=False,
    )

    assert "<b>upgradeGift</b>" in rendered
    assert "Business connection: <code>biz&lt;conn&gt;</code>" in rendered
    assert "Owned gift: <code>owned&lt;gift&gt;</code>" in rendered
    assert "Keep original details: <code>false</code>" in rendered
    assert "cannot be reversed" in rendered


def test_parse_upgrade_gift_args():
    assert commands._parse_upgrade_gift_args(
        f"/upgradegift {BUSINESS_CONNECTION_ID} {OWNED_GIFT_ID} confirm"
    ) == (BUSINESS_CONNECTION_ID, OWNED_GIFT_ID, None, True)
    assert commands._parse_upgrade_gift_args(
        f"/upgradegift {BUSINESS_CONNECTION_ID} {OWNED_GIFT_ID} "
        "keep_original_details=true confirm"
    ) == (BUSINESS_CONNECTION_ID, OWNED_GIFT_ID, True, True)
    assert commands._parse_upgrade_gift_args(
        f"/upgradegift {BUSINESS_CONNECTION_ID} {OWNED_GIFT_ID}"
    ) == (BUSINESS_CONNECTION_ID, OWNED_GIFT_ID, None, False)
    assert commands._parse_upgrade_gift_args("/upgradegift") is None
    assert (
        commands._parse_upgrade_gift_args(
            f"/upgradegift {BUSINESS_CONNECTION_ID} {OWNED_GIFT_ID} maybe"
        )
        is None
    )
    assert (
        commands._parse_upgrade_gift_args(
            f"/upgradegift {BUSINESS_CONNECTION_ID} {OWNED_GIFT_ID} "
            "keep_original_details=maybe confirm"
        )
        is None
    )


def _message(text: str = "/upgradegift", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_upgrade_gift_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_upgrade_gift", AsyncMock())
    message = _message(
        text=f"/upgradegift {BUSINESS_CONNECTION_ID} {OWNED_GIFT_ID} confirm",
        chat_id=42,
    )

    await commands.cmd_upgrade_gift(message)

    commands.perform_upgrade_gift.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_upgrade_gift_requires_confirmation(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_upgrade_gift", AsyncMock())
    message = _message(
        text=f"/upgradegift {BUSINESS_CONNECTION_ID} {OWNED_GIFT_ID}",
        chat_id=42,
    )

    await commands.cmd_upgrade_gift(message)

    commands.perform_upgrade_gift.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "confirmation required" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_upgrade_gift_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_upgrade_gift", AsyncMock())
    message = _message(text="/upgradegift", chat_id=42)

    await commands.cmd_upgrade_gift(message)

    commands.perform_upgrade_gift.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "upgradegift usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_upgrade_gift_upgrades_confirmed_gift(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_upgrade_gift", AsyncMock(return_value=True))
    message = _message(
        text=f"/upgradegift {BUSINESS_CONNECTION_ID} {OWNED_GIFT_ID} "
        "keep_original_details=false confirm",
        chat_id=42,
    )

    await commands.cmd_upgrade_gift(message)

    commands.perform_upgrade_gift.assert_awaited_once_with(
        message.bot,
        business_connection_id=BUSINESS_CONNECTION_ID,
        owned_gift_id=OWNED_GIFT_ID,
        keep_original_details=False,
    )
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "upgradeGift" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_upgrade_gift_reports_errors(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_upgrade_gift",
        AsyncMock(side_effect=UpgradeGiftError("Bad Request")),
    )
    message = _message(
        text=f"/upgradegift {BUSINESS_CONNECTION_ID} {OWNED_GIFT_ID} confirm",
        chat_id=42,
    )

    await commands.cmd_upgrade_gift(message)

    message.answer.assert_awaited_once_with("Could not upgrade the gift. Please try again later.")
