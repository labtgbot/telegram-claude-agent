from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import get_business_account_star_balance
from bot.services.get_business_account_star_balance import (
    GetBusinessAccountStarBalanceError,
    format_business_account_star_balance,
    perform_get_business_account_star_balance,
)


BUSINESS_CONNECTION_ID = "bizconn-123"
STAR_AMOUNT = {"amount": 125, "nanostar_amount": 500000000}


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
        get_business_account_star_balance.httpx,
        "AsyncClient",
        lambda *a, **k: client,
    )


async def test_perform_get_business_account_star_balance_posts_raw_payload(
    monkeypatch,
):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": STAR_AMOUNT}))
    _install_client(monkeypatch, client)

    result = await perform_get_business_account_star_balance(
        _bot(), business_connection_id=f" {BUSINESS_CONNECTION_ID} "
    )

    assert result == STAR_AMOUNT
    assert client.posted["url"] == (
        "https://api.telegram.org/bot123:abc/getBusinessAccountStarBalance"
    )
    assert client.posted["json"] == {
        "business_connection_id": BUSINESS_CONNECTION_ID,
    }


async def test_perform_get_business_account_star_balance_rejects_missing_id(
    monkeypatch,
):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": STAR_AMOUNT}))
    _install_client(monkeypatch, client)

    with pytest.raises(GetBusinessAccountStarBalanceError):
        await perform_get_business_account_star_balance(
            _bot(), business_connection_id=""
        )

    assert client.posted is None


async def test_perform_get_business_account_star_balance_raises_on_telegram_error(
    monkeypatch,
):
    client = _FakeClient(
        response=_FakeResponse(
            {
                "ok": False,
                "error_code": 403,
                "description": "Forbidden: bot lacks can_view_gifts_and_stars right",
            }
        )
    )
    _install_client(monkeypatch, client)

    with pytest.raises(GetBusinessAccountStarBalanceError) as excinfo:
        await perform_get_business_account_star_balance(
            _bot(), business_connection_id=BUSINESS_CONNECTION_ID
        )

    assert excinfo.value.error_code == 403
    assert "can_view_gifts_and_stars" in str(excinfo.value)


async def test_perform_get_business_account_star_balance_raises_on_transport_error(
    monkeypatch,
):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(GetBusinessAccountStarBalanceError):
        await perform_get_business_account_star_balance(
            _bot(), business_connection_id=BUSINESS_CONNECTION_ID
        )


async def test_perform_get_business_account_star_balance_rejects_unexpected_result(
    monkeypatch,
):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    with pytest.raises(GetBusinessAccountStarBalanceError):
        await perform_get_business_account_star_balance(
            _bot(), business_connection_id=BUSINESS_CONNECTION_ID
        )


def test_format_business_account_star_balance_escapes_connection_id():
    rendered = format_business_account_star_balance(
        {"amount": 125, "nanostar_amount": 500000000},
        business_connection_id="biz<conn>",
    )

    assert "<b>Business account Star balance</b>" in rendered
    assert "Business connection: <code>biz&lt;conn&gt;</code>" in rendered
    assert "Stars: <code>125</code>" in rendered
    assert "Nanostars: <code>500000000</code>" in rendered


def test_parse_get_business_account_star_balance_args():
    assert (
        commands._parse_get_business_account_star_balance_args(
            f"/businessstarbalance {BUSINESS_CONNECTION_ID}"
        )
        == BUSINESS_CONNECTION_ID
    )
    assert commands._parse_get_business_account_star_balance_args(
        "/businessstarbalance"
    ) is None
    assert commands._parse_get_business_account_star_balance_args(
        "/businessstarbalance one two"
    ) is None


def _message(text: str = "/businessstarbalance", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_business_star_balance_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_get_business_account_star_balance", AsyncMock()
    )
    message = _message(
        text=f"/businessstarbalance {BUSINESS_CONNECTION_ID}", chat_id=42
    )

    await commands.cmd_business_star_balance(message)

    commands.perform_get_business_account_star_balance.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_business_star_balance_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_get_business_account_star_balance", AsyncMock()
    )
    message = _message(text="/businessstarbalance", chat_id=42)

    await commands.cmd_business_star_balance(message)

    commands.perform_get_business_account_star_balance.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "businessstarbalance usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_business_star_balance_fetches_and_formats(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_get_business_account_star_balance",
        AsyncMock(return_value=STAR_AMOUNT),
    )
    message = _message(
        text=f"/businessstarbalance {BUSINESS_CONNECTION_ID}", chat_id=42
    )

    await commands.cmd_business_star_balance(message)

    commands.perform_get_business_account_star_balance.assert_awaited_once_with(
        message.bot,
        business_connection_id=BUSINESS_CONNECTION_ID,
    )
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "Business account Star balance" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_business_star_balance_reports_errors(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_get_business_account_star_balance",
        AsyncMock(
            side_effect=GetBusinessAccountStarBalanceError(
                "Forbidden: bot lacks can_view_gifts_and_stars right"
            )
        ),
    )
    message = _message(
        text=f"/businessstarbalance {BUSINESS_CONNECTION_ID}", chat_id=42
    )

    await commands.cmd_business_star_balance(message)

    message.answer.assert_awaited_once_with(
        "Could not fetch the business account Star balance: "
        "Forbidden: bot lacks can_view_gifts_and_stars right"
    )
