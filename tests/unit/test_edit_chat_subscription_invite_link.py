from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import ChatInviteLink, User

from bot.handlers import commands
from bot.services import edit_chat_subscription_invite_link
from bot.services.edit_chat_subscription_invite_link import (
    EditChatSubscriptionInviteLinkError,
    format_edit_chat_subscription_invite_link_result,
    perform_edit_chat_subscription_invite_link,
)


class _FakeResponse:
    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data


class _FakeClient:
    def __init__(self, response):
        self._response = response
        self.posted = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, url, json):
        self.posted = {"url": url, "json": json}
        return self._response


def _message(text: str = "/editchatsubscriptioninvitelink", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


def _link(**overrides):
    data = {
        "invite_link": "https://t.me/+paid123",
        "creator": User(id=7, is_bot=True, first_name="Bot"),
        "creates_join_request": False,
        "is_primary": False,
        "is_revoked": False,
        "name": "Paid",
        "subscription_period": 2592000,
        "subscription_price": 100,
    }
    data.update(overrides)
    return ChatInviteLink(**data)


async def test_perform_edit_chat_subscription_invite_link_uses_typed_aiogram_api():
    bot = SimpleNamespace(
        edit_chat_subscription_invite_link=AsyncMock(return_value=_link())
    )

    result = await perform_edit_chat_subscription_invite_link(
        bot,
        chat_id=-100123,
        invite_link="https://t.me/+paid123",
        name="Paid",
    )

    assert result.invite_link == "https://t.me/+paid123"
    bot.edit_chat_subscription_invite_link.assert_awaited_once_with(
        chat_id=-100123,
        invite_link="https://t.me/+paid123",
        name="Paid",
    )


async def test_perform_edit_chat_subscription_invite_link_posts_raw_payload_when_typed_missing(
    monkeypatch,
):
    client = _FakeClient(
        _FakeResponse(
            {
                "ok": True,
                "result": {
                    "invite_link": "https://t.me/+paid123",
                    "creator": {"id": 7, "is_bot": True, "first_name": "Bot"},
                    "creates_join_request": False,
                    "is_primary": False,
                    "is_revoked": False,
                    "name": "Paid",
                    "subscription_period": 2592000,
                    "subscription_price": 100,
                },
            }
        )
    )
    monkeypatch.setattr(
        edit_chat_subscription_invite_link.httpx,
        "AsyncClient",
        lambda *args, **kwargs: client,
    )
    bot = SimpleNamespace(
        token="123:abc",
        session=SimpleNamespace(
            api=SimpleNamespace(
                api_url=lambda token, method: (
                    f"https://api.telegram.org/bot{token}/{method}"
                )
            )
        ),
    )

    result = await perform_edit_chat_subscription_invite_link(
        bot,
        chat_id=-100123,
        invite_link="https://t.me/+paid123",
        name="Paid",
    )

    assert result.name == "Paid"
    assert client.posted["url"] == (
        "https://api.telegram.org/bot123:abc/editChatSubscriptionInviteLink"
    )
    assert client.posted["json"] == {
        "chat_id": -100123,
        "invite_link": "https://t.me/+paid123",
        "name": "Paid",
    }


async def test_perform_edit_chat_subscription_invite_link_reraises_bad_request():
    error = TelegramBadRequest(
        method=None,
        message="Bad Request: not enough rights",
    )
    bot = SimpleNamespace(edit_chat_subscription_invite_link=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_edit_chat_subscription_invite_link(
            bot,
            chat_id=-100123,
            invite_link="https://t.me/+paid123",
        )


async def test_perform_edit_chat_subscription_invite_link_reraises_forbidden():
    error = TelegramForbiddenError(
        method=None,
        message="Forbidden: bot is not an administrator",
    )
    bot = SimpleNamespace(edit_chat_subscription_invite_link=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_edit_chat_subscription_invite_link(
            bot,
            chat_id=-100123,
            invite_link="https://t.me/+paid123",
        )


async def test_perform_edit_chat_subscription_invite_link_rejects_invalid_options():
    bot = SimpleNamespace(edit_chat_subscription_invite_link=AsyncMock())

    with pytest.raises(EditChatSubscriptionInviteLinkError):
        await perform_edit_chat_subscription_invite_link(
            bot,
            chat_id=-100123,
            invite_link="https://t.me/+paid123",
            name="x" * 33,
        )


def test_format_edit_chat_subscription_invite_link_result_escapes_values():
    text = format_edit_chat_subscription_invite_link_result(
        chat_id=-100123,
        link=_link(
            invite_link="https://t.me/+paid<&>",
            name="Paid <team>",
            expire_date=datetime.fromtimestamp(1893456000, tz=timezone.utc),
        ),
    )

    assert "editChatSubscriptionInviteLink" in text
    assert "https://t.me/+paid&lt;&amp;&gt;" in text
    assert "Paid &lt;team&gt;" in text
    assert "Subscription period: 2592000" in text
    assert "Subscription price: 100" in text
    assert "1893456000" in text


async def test_cmd_edit_chat_subscription_invite_link_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_edit_chat_subscription_invite_link", AsyncMock())
    message = _message(
        text="/editchatsubscriptioninvitelink -100123 https://t.me/+paid123",
        chat_id=42,
    )

    await commands.cmd_edit_chat_subscription_invite_link(message)

    commands.perform_edit_chat_subscription_invite_link.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_edit_chat_subscription_invite_link_shows_usage_without_args(
    monkeypatch,
):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_edit_chat_subscription_invite_link", AsyncMock())
    message = _message(text="/editchatsubscriptioninvitelink", chat_id=42)

    await commands.cmd_edit_chat_subscription_invite_link(message)

    commands.perform_edit_chat_subscription_invite_link.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "editchatsubscriptioninvitelink usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_edit_chat_subscription_invite_link_calls_service(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_edit_chat_subscription_invite_link",
        AsyncMock(return_value=_link()),
    )
    monkeypatch.setattr(
        commands,
        "format_edit_chat_subscription_invite_link_result",
        lambda **kwargs: "ok",
    )
    message = _message(
        text="/editchatsubscriptioninvitelink -100123 https://t.me/+paid123 name=Paid",
        chat_id=42,
    )

    await commands.cmd_edit_chat_subscription_invite_link(message)

    commands.perform_edit_chat_subscription_invite_link.assert_awaited_once_with(
        message.bot,
        chat_id=-100123,
        invite_link="https://t.me/+paid123",
        name="Paid",
    )
    args, kwargs = message.answer.await_args
    assert args[0] == "ok"
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_edit_chat_subscription_invite_link_reports_telegram_errors(
    monkeypatch,
):
    error = TelegramBadRequest(
        method=None,
        message="Bad Request: not enough rights",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_edit_chat_subscription_invite_link",
        AsyncMock(side_effect=error),
    )
    message = _message(
        text="/editchatsubscriptioninvitelink -100123 https://t.me/+paid123",
        chat_id=42,
    )

    await commands.cmd_edit_chat_subscription_invite_link(message)

    args, _kwargs = message.answer.await_args
    assert "Could not edit the chat subscription invite link" in args[0]


def test_parse_edit_chat_subscription_invite_link_args():
    assert commands._parse_edit_chat_subscription_invite_link_args(
        "/editchatsubscriptioninvitelink -100123 https://t.me/+paid123 name=Paid"
    ) == (-100123, "https://t.me/+paid123", "Paid")


def test_parse_edit_chat_subscription_invite_link_args_rejects_invalid_input():
    assert (
        commands._parse_edit_chat_subscription_invite_link_args(
            "/editchatsubscriptioninvitelink"
        )
        is None
    )
    assert (
        commands._parse_edit_chat_subscription_invite_link_args(
            "/editchatsubscriptioninvitelink nope https://t.me/+paid123"
        )
        is None
    )
    assert (
        commands._parse_edit_chat_subscription_invite_link_args(
            "/editchatsubscriptioninvitelink -100123 https://t.me/+paid123 bad=Paid"
        )
        is None
    )
    assert (
        commands._parse_edit_chat_subscription_invite_link_args(
            "/editchatsubscriptioninvitelink -100123 https://t.me/+paid123 "
            f"name={'x' * 33}"
        )
        is None
    )
