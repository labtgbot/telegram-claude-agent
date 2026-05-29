from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import gift_premium_subscription
from bot.services.gift_premium_subscription import (
    GiftPremiumSubscriptionError,
    perform_gift_premium_subscription,
)


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
        gift_premium_subscription.httpx,
        "AsyncClient",
        lambda *a, **k: client,
    )


def _message(text: str = "/giftpremium", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_perform_gift_premium_subscription_posts_payload(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    result = await perform_gift_premium_subscription(
        _bot(),
        user_id=777,
        month_count=3,
        star_count=1000,
        text="thanks",
        text_parse_mode="HTML",
    )

    assert result is True
    assert (
        client.posted["url"]
        == "https://api.telegram.org/bot123:abc/giftPremiumSubscription"
    )
    assert client.posted["json"] == {
        "user_id": 777,
        "month_count": 3,
        "star_count": 1000,
        "text": "thanks",
        "text_parse_mode": "HTML",
    }


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"user_id": 0, "month_count": 3, "star_count": 1000}, "user_id"),
        ({"user_id": 777, "month_count": 2, "star_count": 1000}, "month_count"),
        ({"user_id": 777, "month_count": 13, "star_count": 1000}, "month_count"),
        ({"user_id": 777, "month_count": 3, "star_count": 0}, "star_count"),
    ],
)
async def test_perform_gift_premium_subscription_validates_payload(
    monkeypatch, kwargs, message
):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    with pytest.raises(GiftPremiumSubscriptionError) as excinfo:
        await perform_gift_premium_subscription(_bot(), **kwargs)

    assert message in str(excinfo.value)
    assert client.posted is None


async def test_perform_gift_premium_subscription_raises_on_telegram_error(
    monkeypatch,
):
    client = _FakeClient(
        response=_FakeResponse(
            {
                "ok": False,
                "error_code": 400,
                "description": "Bad Request: not enough Stars",
            }
        )
    )
    _install_client(monkeypatch, client)

    with pytest.raises(GiftPremiumSubscriptionError) as excinfo:
        await perform_gift_premium_subscription(
            _bot(), user_id=777, month_count=3, star_count=1000
        )

    assert excinfo.value.error_code == 400
    assert "not enough Stars" in str(excinfo.value)


async def test_perform_gift_premium_subscription_raises_on_transport_error(
    monkeypatch,
):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(GiftPremiumSubscriptionError):
        await perform_gift_premium_subscription(
            _bot(), user_id=777, month_count=3, star_count=1000
        )


async def test_perform_gift_premium_subscription_rejects_unexpected_result(
    monkeypatch,
):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": {}}))
    _install_client(monkeypatch, client)

    with pytest.raises(GiftPremiumSubscriptionError):
        await perform_gift_premium_subscription(
            _bot(), user_id=777, month_count=3, star_count=1000
        )


def test_parse_gift_premium_args_variants():
    assert commands._parse_gift_premium_args("/giftpremium 777 3 1000") == (
        777,
        3,
        1000,
        False,
        None,
    )
    assert commands._parse_gift_premium_args(
        "/giftpremium 777 12 2500 confirm thanks"
    ) == (777, 12, 2500, True, "thanks")
    assert commands._parse_gift_premium_args("/giftpremium bad 3 1000") is None
    assert commands._parse_gift_premium_args("/giftpremium 777 2 1000") is None
    assert commands._parse_gift_premium_args("/giftpremium 777 13 1000") is None
    assert commands._parse_gift_premium_args("/giftpremium 777 3 0") is None
    assert commands._parse_gift_premium_args(
        "/giftpremium 777 3 1000 maybe"
    ) is None


async def test_cmd_gift_premium_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_gift_premium_subscription", AsyncMock())
    message = _message(text="/giftpremium 777 3 1000 confirm", chat_id=42)

    await commands.cmd_gift_premium(message)

    commands.perform_gift_premium_subscription.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_gift_premium_requires_confirmation(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_gift_premium_subscription", AsyncMock())
    message = _message(text="/giftpremium 777 3 1000", chat_id=42)

    await commands.cmd_gift_premium(message)

    commands.perform_gift_premium_subscription.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "confirmation required" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_gift_premium_sends_confirmed_subscription(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_gift_premium_subscription",
        AsyncMock(return_value=True),
    )
    message = _message(text="/giftpremium 777 3 1000 confirm thanks", chat_id=42)

    await commands.cmd_gift_premium(message)

    commands.perform_gift_premium_subscription.assert_awaited_once_with(
        message.bot,
        user_id=777,
        month_count=3,
        star_count=1000,
        text="thanks",
        text_parse_mode="HTML",
    )
    message.answer.assert_awaited_once_with("Gifted Premium subscription.")


async def test_cmd_gift_premium_rejects_too_long_text(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_gift_premium_subscription", AsyncMock())
    text = "x" * (commands.GIFT_PREMIUM_TEXT_LIMIT + 1)
    message = _message(text=f"/giftpremium 777 3 1000 confirm {text}", chat_id=42)

    await commands.cmd_gift_premium(message)

    commands.perform_gift_premium_subscription.assert_not_awaited()
    args, _ = message.answer.await_args
    assert "Premium gift text is too long" in args[0]


async def test_cmd_gift_premium_reports_errors(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_gift_premium_subscription",
        AsyncMock(side_effect=GiftPremiumSubscriptionError("Bad Request")),
    )
    message = _message(text="/giftpremium 777 3 1000 confirm", chat_id=42)

    await commands.cmd_gift_premium(message)

    message.answer.assert_awaited_once_with(
        "Could not gift Premium subscription: Bad Request"
    )
