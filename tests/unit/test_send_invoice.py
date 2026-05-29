import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import send_invoice
from bot.services.send_invoice import SendInvoiceError, perform_send_invoice


class _FakeResponse:
    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data


class _FakeClient:
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
    monkeypatch.setattr(send_invoice.httpx, "AsyncClient", lambda *a, **k: client)


async def test_perform_send_invoice_posts_raw_stars_payload(monkeypatch):
    prices = [{"label": "Test", "amount": 3}]
    client = _FakeClient(
        response=_FakeResponse({"ok": True, "result": {"message_id": 777}})
    )
    _install_client(monkeypatch, client)

    result = await perform_send_invoice(
        _bot(),
        chat_id=42,
        title="Test",
        description="Test invoice",
        payload="invoice-1",
        provider_token="",
        currency="XTR",
        prices=prices,
    )

    assert result == {"message_id": 777}
    assert client.posted["url"] == "https://api.telegram.org/bot123:abc/sendInvoice"
    assert client.posted["json"] == {
        "chat_id": 42,
        "title": "Test",
        "description": "Test invoice",
        "payload": "invoice-1",
        "provider_token": "",
        "currency": "XTR",
        "prices": json.dumps(prices),
    }
    assert json.loads(client.posted["json"]["prices"]) == prices


async def test_perform_send_invoice_rejects_empty_prices(monkeypatch):
    client = _FakeClient()
    _install_client(monkeypatch, client)

    with pytest.raises(SendInvoiceError, match="prices"):
        await perform_send_invoice(
            _bot(),
            chat_id=42,
            title="Test",
            description="Test invoice",
            payload="invoice-1",
            provider_token="",
            currency="XTR",
            prices=[],
        )

    assert client.posted is None


async def test_perform_send_invoice_raises_on_telegram_error(monkeypatch):
    client = _FakeClient(
        response=_FakeResponse(
            {
                "ok": False,
                "error_code": 400,
                "description": "Bad Request: invoice payload is invalid",
            }
        )
    )
    _install_client(monkeypatch, client)

    with pytest.raises(SendInvoiceError) as excinfo:
        await perform_send_invoice(
            _bot(),
            chat_id=42,
            title="Test",
            description="Test invoice",
            payload="invoice-1",
            provider_token="",
            currency="XTR",
            prices=[{"label": "Test", "amount": 3}],
        )

    assert excinfo.value.error_code == 400
    assert "payload" in str(excinfo.value)


async def test_perform_send_invoice_raises_on_transport_error(monkeypatch):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(SendInvoiceError):
        await perform_send_invoice(
            _bot(),
            chat_id=42,
            title="Test",
            description="Test invoice",
            payload="invoice-1",
            provider_token="",
            currency="XTR",
            prices=[{"label": "Test", "amount": 3}],
        )


def test_parse_send_invoice_args_variants():
    assert commands._parse_send_invoice_args(
        "/sendinvoice 3 payload-1 Test title | Test description"
    ) == (3, "payload-1", "Test title", "Test description")
    assert commands._parse_send_invoice_args("/sendinvoice 3 payload only-title") is None
    assert commands._parse_send_invoice_args("/sendinvoice free payload T | D") is None


def test_validate_send_invoice_args():
    assert (
        commands._validate_send_invoice_args(
            star_count=0, payload="p", title="T", description="D"
        )
        == "Star count must be between 1 and 25000."
    )
    assert "Payload is too long" in commands._validate_send_invoice_args(
        star_count=1, payload="x" * 129, title="T", description="D"
    )
    assert commands._validate_send_invoice_args(
        star_count=1, payload="p", title="T", description="D"
    ) is None


def _message(text: str = "/sendinvoice", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_send_invoice_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_invoice", AsyncMock())
    message = _message(text="/sendinvoice 3 payload T | D", chat_id=42)

    await commands.cmd_send_invoice(message)

    commands.perform_send_invoice.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_send_invoice_sends_stars_invoice(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_invoice", AsyncMock(return_value={}))
    message = _message(text="/sendinvoice 3 invoice-1 Test | Test description")

    await commands.cmd_send_invoice(message)

    commands.perform_send_invoice.assert_awaited_once_with(
        message.bot,
        chat_id=42,
        title="Test",
        description="Test description",
        payload="invoice-1",
        provider_token="",
        currency="XTR",
        prices=[{"label": "Test", "amount": 3}],
    )
    message.answer.assert_awaited_once_with("Sent Telegram Stars invoice.")
