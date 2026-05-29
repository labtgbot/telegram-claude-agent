from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import edit_user_star_subscription
from bot.services.edit_user_star_subscription import (
    EditUserStarSubscriptionError,
    format_edit_user_star_subscription_result,
    perform_edit_user_star_subscription,
)


USER_ID = 777
CHARGE_ID = "tg-subscription-charge-1"


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
        edit_user_star_subscription.httpx,
        "AsyncClient",
        lambda *a, **k: client,
    )


async def test_perform_edit_user_star_subscription_posts_raw_payload(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    result = await perform_edit_user_star_subscription(
        _bot(),
        user_id=USER_ID,
        telegram_payment_charge_id=f" {CHARGE_ID} ",
        is_canceled=True,
    )

    assert result is True
    assert client.posted == [
        {
            "url": "https://api.telegram.org/bot123:abc/editUserStarSubscription",
            "json": {
                "user_id": USER_ID,
                "telegram_payment_charge_id": CHARGE_ID,
                "is_canceled": True,
            },
        }
    ]


async def test_perform_edit_user_star_subscription_rejects_invalid_args(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    invalid_cases = [
        {"user_id": 0, "telegram_payment_charge_id": CHARGE_ID, "is_canceled": True},
        {"user_id": -1, "telegram_payment_charge_id": CHARGE_ID, "is_canceled": True},
        {
            "user_id": True,
            "telegram_payment_charge_id": CHARGE_ID,
            "is_canceled": True,
        },
        {
            "user_id": "777",
            "telegram_payment_charge_id": CHARGE_ID,
            "is_canceled": True,
        },
        {"user_id": USER_ID, "telegram_payment_charge_id": "", "is_canceled": True},
        {
            "user_id": USER_ID,
            "telegram_payment_charge_id": CHARGE_ID,
            "is_canceled": "true",
        },
    ]
    for kwargs in invalid_cases:
        with pytest.raises(EditUserStarSubscriptionError):
            await perform_edit_user_star_subscription(_bot(), **kwargs)

    assert client.posted == []


async def test_perform_edit_user_star_subscription_raises_on_telegram_error(
    monkeypatch,
):
    client = _FakeClient(
        response=_FakeResponse(
            {
                "ok": False,
                "error_code": 400,
                "description": "Bad Request: subscription is not found",
            }
        )
    )
    _install_client(monkeypatch, client)

    with pytest.raises(EditUserStarSubscriptionError) as excinfo:
        await perform_edit_user_star_subscription(
            _bot(),
            user_id=USER_ID,
            telegram_payment_charge_id=CHARGE_ID,
            is_canceled=True,
        )

    assert excinfo.value.error_code == 400
    assert "not found" in str(excinfo.value)


async def test_perform_edit_user_star_subscription_raises_on_transport_error(
    monkeypatch,
):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(EditUserStarSubscriptionError):
        await perform_edit_user_star_subscription(
            _bot(),
            user_id=USER_ID,
            telegram_payment_charge_id=CHARGE_ID,
            is_canceled=True,
        )


async def test_perform_edit_user_star_subscription_rejects_unexpected_result(
    monkeypatch,
):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": {}}))
    _install_client(monkeypatch, client)

    with pytest.raises(EditUserStarSubscriptionError):
        await perform_edit_user_star_subscription(
            _bot(),
            user_id=USER_ID,
            telegram_payment_charge_id=CHARGE_ID,
            is_canceled=True,
        )


def test_format_edit_user_star_subscription_result_escapes_values():
    rendered = format_edit_user_star_subscription_result(
        user_id=USER_ID,
        telegram_payment_charge_id="charge<1>",
        is_canceled=True,
    )

    assert "<b>editUserStarSubscription</b>" in rendered
    assert "User id: <code>777</code>" in rendered
    assert "charge&lt;1&gt;" in rendered
    assert "Target state: <code>canceled</code>" in rendered


def test_parse_edit_user_star_subscription_args():
    assert commands._parse_edit_user_star_subscription_args(
        f"/edituserstarsubscription {USER_ID} {CHARGE_ID} canceled confirm"
    ) == (USER_ID, CHARGE_ID, True, True)
    assert commands._parse_edit_user_star_subscription_args(
        f"/edituserstarsubscription {USER_ID} {CHARGE_ID} active"
    ) == (USER_ID, CHARGE_ID, False, False)
    assert commands._parse_edit_user_star_subscription_args(
        "/edituserstarsubscription"
    ) is None
    assert commands._parse_edit_user_star_subscription_args(
        f"/edituserstarsubscription nope {CHARGE_ID} canceled"
    ) is None
    assert commands._parse_edit_user_star_subscription_args(
        f"/edituserstarsubscription {USER_ID} {CHARGE_ID} paused"
    ) is None
    assert commands._parse_edit_user_star_subscription_args(
        f"/edituserstarsubscription {USER_ID} {CHARGE_ID} canceled maybe"
    ) is None


def _message(text: str = "/edituserstarsubscription", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_edit_user_star_subscription_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_edit_user_star_subscription", AsyncMock())
    message = _message(
        text=f"/edituserstarsubscription {USER_ID} {CHARGE_ID} canceled confirm"
    )

    await commands.cmd_edit_user_star_subscription(message)

    commands.perform_edit_user_star_subscription.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_edit_user_star_subscription_requires_confirmation(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_edit_user_star_subscription", AsyncMock())
    message = _message(
        text=f"/edituserstarsubscription {USER_ID} {CHARGE_ID} canceled"
    )

    await commands.cmd_edit_user_star_subscription(message)

    commands.perform_edit_user_star_subscription.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "confirmation required" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_edit_user_star_subscription_updates_subscription(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_edit_user_star_subscription",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(commands, "_EDITED_USER_STAR_SUBSCRIPTION_KEYS", set())
    message = _message(
        text=f"/edituserstarsubscription {USER_ID} {CHARGE_ID} canceled confirm"
    )

    await commands.cmd_edit_user_star_subscription(message)

    commands.perform_edit_user_star_subscription.assert_awaited_once_with(
        message.bot,
        user_id=USER_ID,
        telegram_payment_charge_id=CHARGE_ID,
        is_canceled=True,
    )
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "editUserStarSubscription" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_edit_user_star_subscription_is_idempotent(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_edit_user_star_subscription", AsyncMock())
    monkeypatch.setattr(
        commands,
        "_EDITED_USER_STAR_SUBSCRIPTION_KEYS",
        {(USER_ID, CHARGE_ID, True)},
    )
    message = _message(
        text=f"/edituserstarsubscription {USER_ID} {CHARGE_ID} canceled confirm"
    )

    await commands.cmd_edit_user_star_subscription(message)

    commands.perform_edit_user_star_subscription.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "already recorded" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_edit_user_star_subscription_reports_service_error(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_edit_user_star_subscription",
        AsyncMock(side_effect=EditUserStarSubscriptionError("Bad Request")),
    )
    monkeypatch.setattr(commands, "_EDITED_USER_STAR_SUBSCRIPTION_KEYS", set())
    message = _message(
        text=f"/edituserstarsubscription {USER_ID} {CHARGE_ID} canceled confirm"
    )

    await commands.cmd_edit_user_star_subscription(message)

    message.answer.assert_awaited_once_with(
        "Could not edit the Stars subscription: Bad Request"
    )
