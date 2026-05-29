from types import SimpleNamespace

import httpx
import pytest

from bot.services import answer_pre_checkout_query
from bot.services.answer_pre_checkout_query import (
    AnswerPreCheckoutQueryError,
    perform_answer_pre_checkout_query,
)


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
    monkeypatch.setattr(
        answer_pre_checkout_query.httpx, "AsyncClient", lambda *a, **k: client
    )


async def test_perform_answer_pre_checkout_query_approves_checkout(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    result = await perform_answer_pre_checkout_query(
        _bot(),
        pre_checkout_query_id="pre-checkout-1",
        ok=True,
    )

    assert result is True
    assert client.posted["url"] == (
        "https://api.telegram.org/bot123:abc/answerPreCheckoutQuery"
    )
    assert client.posted["json"] == {
        "pre_checkout_query_id": "pre-checkout-1",
        "ok": True,
    }


async def test_perform_answer_pre_checkout_query_rejects_checkout(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    await perform_answer_pre_checkout_query(
        _bot(),
        pre_checkout_query_id="pre-checkout-1",
        ok=False,
        error_message="Payment payload is no longer valid.",
    )

    assert client.posted["json"] == {
        "pre_checkout_query_id": "pre-checkout-1",
        "ok": False,
        "error_message": "Payment payload is no longer valid.",
    }


async def test_perform_answer_pre_checkout_query_requires_error_message_on_reject(
    monkeypatch,
):
    client = _FakeClient()
    _install_client(monkeypatch, client)

    with pytest.raises(AnswerPreCheckoutQueryError, match="error_message"):
        await perform_answer_pre_checkout_query(
            _bot(),
            pre_checkout_query_id="pre-checkout-1",
            ok=False,
        )

    assert client.posted is None


async def test_perform_answer_pre_checkout_query_raises_on_telegram_error(
    monkeypatch,
):
    client = _FakeClient(
        response=_FakeResponse(
            {
                "ok": False,
                "error_code": 400,
                "description": "Bad Request: query is too old",
            }
        )
    )
    _install_client(monkeypatch, client)

    with pytest.raises(AnswerPreCheckoutQueryError) as excinfo:
        await perform_answer_pre_checkout_query(
            _bot(),
            pre_checkout_query_id="pre-checkout-1",
            ok=True,
        )

    assert excinfo.value.error_code == 400
    assert "too old" in str(excinfo.value)


async def test_perform_answer_pre_checkout_query_raises_on_transport_error(
    monkeypatch,
):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(AnswerPreCheckoutQueryError):
        await perform_answer_pre_checkout_query(
            _bot(),
            pre_checkout_query_id="pre-checkout-1",
            ok=True,
        )
