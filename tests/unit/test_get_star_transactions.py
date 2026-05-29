from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import get_star_transactions
from bot.services.get_star_transactions import (
    GetStarTransactionsError,
    format_star_transactions,
    perform_get_star_transactions,
)


STAR_TRANSACTIONS = {
    "transactions": [
        {
            "id": "charge-1",
            "amount": 25,
            "nanostar_amount": 500000000,
            "date": 1710000000,
            "source": {"type": "user", "user": {"id": 777}},
        }
    ]
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
        get_star_transactions.httpx,
        "AsyncClient",
        lambda *a, **k: client,
    )


async def test_perform_get_star_transactions_posts_raw_payload(monkeypatch):
    client = _FakeClient(
        response=_FakeResponse({"ok": True, "result": STAR_TRANSACTIONS})
    )
    _install_client(monkeypatch, client)

    result = await perform_get_star_transactions(_bot(), offset=10, limit=50)

    assert result == STAR_TRANSACTIONS
    assert client.posted["url"] == (
        "https://api.telegram.org/bot123:abc/getStarTransactions"
    )
    assert client.posted["json"] == {"offset": 10, "limit": 50}


async def test_perform_get_star_transactions_rejects_invalid_args(monkeypatch):
    client = _FakeClient(
        response=_FakeResponse({"ok": True, "result": STAR_TRANSACTIONS})
    )
    _install_client(monkeypatch, client)

    invalid_cases = [
        {"offset": -1},
        {"offset": True},
        {"offset": "1"},
        {"limit": 0},
        {"limit": 101},
        {"limit": True},
        {"limit": "10"},
    ]
    for kwargs in invalid_cases:
        with pytest.raises(GetStarTransactionsError):
            await perform_get_star_transactions(_bot(), **kwargs)

    assert client.posted is None


async def test_perform_get_star_transactions_raises_on_telegram_error(monkeypatch):
    client = _FakeClient(
        response=_FakeResponse(
            {
                "ok": False,
                "error_code": 429,
                "description": "Too Many Requests: retry later",
            }
        )
    )
    _install_client(monkeypatch, client)

    with pytest.raises(GetStarTransactionsError) as excinfo:
        await perform_get_star_transactions(_bot())

    assert excinfo.value.error_code == 429
    assert "Too Many Requests" in str(excinfo.value)


async def test_perform_get_star_transactions_raises_on_transport_error(monkeypatch):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(GetStarTransactionsError):
        await perform_get_star_transactions(_bot())


async def test_perform_get_star_transactions_rejects_unexpected_result(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    with pytest.raises(GetStarTransactionsError):
        await perform_get_star_transactions(_bot())


def test_format_star_transactions_escapes_values():
    rendered = format_star_transactions(
        {
            "transactions": [
                {
                    "id": "charge<1>",
                    "amount": 25,
                    "nanostar_amount": 5,
                    "date": 1710000000,
                    "source": {"type": "user"},
                }
            ]
        },
        offset=0,
        limit=10,
    )

    assert "<b>Bot Star transactions</b>" in rendered
    assert "charge&lt;1&gt;" in rendered
    assert "25 Stars" in rendered
    assert "incoming" in rendered
    assert "nanostars <code>5</code>" in rendered


def test_parse_get_star_transactions_args():
    assert commands._parse_get_star_transactions_args("/startransactions") == {
        "offset": None,
        "limit": None,
    }
    assert commands._parse_get_star_transactions_args(
        "/startransactions offset=10 limit=50"
    ) == {"offset": 10, "limit": 50}
    assert commands._parse_get_star_transactions_args(
        "/startransactions limit=101"
    ) is None
    assert commands._parse_get_star_transactions_args(
        "/startransactions offset=-1"
    ) is None
    assert commands._parse_get_star_transactions_args(
        "/startransactions nope"
    ) is None


def _message(text: str = "/startransactions", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_star_transactions_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_get_star_transactions", AsyncMock())
    message = _message(chat_id=42)

    await commands.cmd_star_transactions(message)

    commands.perform_get_star_transactions.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_star_transactions_shows_usage_with_invalid_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_get_star_transactions", AsyncMock())
    message = _message(text="/startransactions limit=0", chat_id=42)

    await commands.cmd_star_transactions(message)

    commands.perform_get_star_transactions.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "startransactions usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_star_transactions_fetches_and_formats(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_get_star_transactions",
        AsyncMock(return_value=STAR_TRANSACTIONS),
    )
    message = _message(text="/startransactions offset=1 limit=10", chat_id=42)

    await commands.cmd_star_transactions(message)

    commands.perform_get_star_transactions.assert_awaited_once_with(
        message.bot,
        offset=1,
        limit=10,
    )
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "Bot Star transactions" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_star_transactions_reports_errors(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_get_star_transactions",
        AsyncMock(side_effect=GetStarTransactionsError("Too Many Requests")),
    )
    message = _message(chat_id=42)

    await commands.cmd_star_transactions(message)

    message.answer.assert_awaited_once_with(
        "Could not fetch the bot Star transactions: Too Many Requests"
    )
