from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import refund_star_payment
from bot.services.refund_star_payment import (
    RefundStarPaymentError,
    format_refund_star_payment_result,
    perform_refund_star_payment,
)


USER_ID = 777
CHARGE_ID = "tg-charge-1"


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
        self.posted = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, url, json):
        self.posted.append({"url": url, "json": json})
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
        refund_star_payment.httpx,
        "AsyncClient",
        lambda *a, **k: client,
    )


async def test_perform_refund_star_payment_posts_raw_payload(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    result = await perform_refund_star_payment(
        _bot(),
        user_id=USER_ID,
        telegram_payment_charge_id=f" {CHARGE_ID} ",
    )

    assert result is True
    assert client.posted == [
        {
            "url": "https://api.telegram.org/bot123:abc/refundStarPayment",
            "json": {
                "user_id": USER_ID,
                "telegram_payment_charge_id": CHARGE_ID,
            },
        }
    ]


async def test_perform_refund_star_payment_rejects_invalid_args(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    invalid_cases = [
        {"user_id": 0, "telegram_payment_charge_id": CHARGE_ID},
        {"user_id": -1, "telegram_payment_charge_id": CHARGE_ID},
        {"user_id": True, "telegram_payment_charge_id": CHARGE_ID},
        {"user_id": "777", "telegram_payment_charge_id": CHARGE_ID},
        {"user_id": USER_ID, "telegram_payment_charge_id": ""},
    ]
    for kwargs in invalid_cases:
        with pytest.raises(RefundStarPaymentError):
            await perform_refund_star_payment(_bot(), **kwargs)

    assert client.posted == []


async def test_perform_refund_star_payment_raises_on_telegram_error(monkeypatch):
    client = _FakeClient(
        response=_FakeResponse(
            {
                "ok": False,
                "error_code": 400,
                "description": "Bad Request: charge already refunded",
            }
        )
    )
    _install_client(monkeypatch, client)

    with pytest.raises(RefundStarPaymentError) as excinfo:
        await perform_refund_star_payment(
            _bot(),
            user_id=USER_ID,
            telegram_payment_charge_id=CHARGE_ID,
        )

    assert excinfo.value.error_code == 400
    assert "already refunded" in str(excinfo.value)


async def test_perform_refund_star_payment_raises_on_transport_error(monkeypatch):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(RefundStarPaymentError):
        await perform_refund_star_payment(
            _bot(),
            user_id=USER_ID,
            telegram_payment_charge_id=CHARGE_ID,
        )


async def test_perform_refund_star_payment_rejects_unexpected_result(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": {}}))
    _install_client(monkeypatch, client)

    with pytest.raises(RefundStarPaymentError):
        await perform_refund_star_payment(
            _bot(),
            user_id=USER_ID,
            telegram_payment_charge_id=CHARGE_ID,
        )


def test_format_refund_star_payment_result_escapes_values():
    rendered = format_refund_star_payment_result(
        user_id=USER_ID,
        telegram_payment_charge_id="charge<1>",
    )

    assert "<b>refundStarPayment</b>" in rendered
    assert "User id: <code>777</code>" in rendered
    assert "charge&lt;1&gt;" in rendered
    assert "/startransactions" in rendered


def test_parse_refund_star_payment_args():
    assert commands._parse_refund_star_payment_args(
        f"/refundstars {USER_ID} {CHARGE_ID} confirm"
    ) == (USER_ID, CHARGE_ID, True)
    assert commands._parse_refund_star_payment_args(
        f"/refundstars {USER_ID} {CHARGE_ID}"
    ) == (USER_ID, CHARGE_ID, False)
    assert commands._parse_refund_star_payment_args("/refundstars") is None
    assert commands._parse_refund_star_payment_args(
        f"/refundstars nope {CHARGE_ID}"
    ) is None
    assert commands._parse_refund_star_payment_args(
        f"/refundstars {USER_ID} {CHARGE_ID} maybe"
    ) is None


def _message(text: str = "/refundstars", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_refund_stars_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_refund_star_payment", AsyncMock())
    message = _message(text=f"/refundstars {USER_ID} {CHARGE_ID} confirm")

    await commands.cmd_refund_stars(message)

    commands.perform_refund_star_payment.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_refund_stars_requires_confirmation(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_refund_star_payment", AsyncMock())
    message = _message(text=f"/refundstars {USER_ID} {CHARGE_ID}")

    await commands.cmd_refund_stars(message)

    commands.perform_refund_star_payment.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "confirmation required" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_refund_stars_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_refund_star_payment", AsyncMock())
    message = _message(text="/refundstars")

    await commands.cmd_refund_stars(message)

    commands.perform_refund_star_payment.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "refundstars usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_refund_stars_refunds_confirmed_payment(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "_REFUNDED_STAR_PAYMENT_KEYS", set())
    monkeypatch.setattr(
        commands, "perform_refund_star_payment", AsyncMock(return_value=True)
    )
    message = _message(text=f"/refundstars {USER_ID} {CHARGE_ID} confirm")

    await commands.cmd_refund_stars(message)

    commands.perform_refund_star_payment.assert_awaited_once_with(
        message.bot,
        user_id=USER_ID,
        telegram_payment_charge_id=CHARGE_ID,
    )
    assert (USER_ID, CHARGE_ID) in commands._REFUNDED_STAR_PAYMENT_KEYS
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "refundStarPayment" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_refund_stars_is_idempotent_in_process(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "_REFUNDED_STAR_PAYMENT_KEYS", {(USER_ID, CHARGE_ID)})
    monkeypatch.setattr(commands, "perform_refund_star_payment", AsyncMock())
    message = _message(text=f"/refundstars {USER_ID} {CHARGE_ID} confirm")

    await commands.cmd_refund_stars(message)

    commands.perform_refund_star_payment.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "already recorded" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_refund_stars_reports_errors(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "_REFUNDED_STAR_PAYMENT_KEYS", set())
    monkeypatch.setattr(
        commands,
        "perform_refund_star_payment",
        AsyncMock(side_effect=RefundStarPaymentError("Bad Request")),
    )
    message = _message(text=f"/refundstars {USER_ID} {CHARGE_ID} confirm")

    await commands.cmd_refund_stars(message)

    assert commands._REFUNDED_STAR_PAYMENT_KEYS == set()
    message.answer.assert_awaited_once_with(
        "Could not refund the Stars payment: Bad Request"
    )
