from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import RevokeChatInviteLink
from aiogram.types import ChatInviteLink, User

from bot.handlers import commands
from bot.services import revoke_chat_invite_link
from bot.services.revoke_chat_invite_link import (
    RevokeChatInviteLinkError,
    format_revoke_chat_invite_link_result,
    perform_revoke_chat_invite_link,
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


def _message(text: str = "/revokechatinvitelink", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


def _link(**overrides):
    data = {
        "invite_link": "https://t.me/+abc123",
        "creator": User(id=7, is_bot=True, first_name="Bot"),
        "creates_join_request": False,
        "is_primary": False,
        "is_revoked": True,
        "name": "Ops",
    }
    data.update(overrides)
    return ChatInviteLink(**data)


async def test_perform_revoke_chat_invite_link_uses_typed_aiogram_api():
    bot = SimpleNamespace(revoke_chat_invite_link=AsyncMock(return_value=_link()))

    result = await perform_revoke_chat_invite_link(
        bot,
        chat_id=-100123,
        invite_link="https://t.me/+abc123",
    )

    assert result.invite_link == "https://t.me/+abc123"
    assert result.is_revoked is True
    bot.revoke_chat_invite_link.assert_awaited_once_with(
        chat_id=-100123,
        invite_link="https://t.me/+abc123",
    )


async def test_perform_revoke_chat_invite_link_posts_raw_payload_when_typed_missing(
    monkeypatch,
):
    client = _FakeClient(
        _FakeResponse(
            {
                "ok": True,
                "result": {
                    "invite_link": "https://t.me/+abc123",
                    "creator": {"id": 7, "is_bot": True, "first_name": "Bot"},
                    "creates_join_request": False,
                    "is_primary": False,
                    "is_revoked": True,
                    "name": "Ops",
                },
            }
        )
    )
    monkeypatch.setattr(
        revoke_chat_invite_link.httpx,
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

    result = await perform_revoke_chat_invite_link(
        bot,
        chat_id=-100123,
        invite_link="https://t.me/+abc123",
    )

    assert result.is_revoked is True
    assert client.posted["url"] == (
        "https://api.telegram.org/bot123:abc/revokeChatInviteLink"
    )
    assert client.posted["json"] == {
        "chat_id": -100123,
        "invite_link": "https://t.me/+abc123",
    }


async def test_perform_revoke_chat_invite_link_reraises_bad_request():
    error = TelegramBadRequest(
        method=RevokeChatInviteLink(
            chat_id=-100123,
            invite_link="https://t.me/+abc123",
        ),
        message="Bad Request: not enough rights",
    )
    bot = SimpleNamespace(revoke_chat_invite_link=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_revoke_chat_invite_link(
            bot,
            chat_id=-100123,
            invite_link="https://t.me/+abc123",
        )


async def test_perform_revoke_chat_invite_link_reraises_forbidden():
    error = TelegramForbiddenError(
        method=RevokeChatInviteLink(
            chat_id=-100123,
            invite_link="https://t.me/+abc123",
        ),
        message="Forbidden: bot is not an administrator",
    )
    bot = SimpleNamespace(revoke_chat_invite_link=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_revoke_chat_invite_link(
            bot,
            chat_id=-100123,
            invite_link="https://t.me/+abc123",
        )


async def test_perform_revoke_chat_invite_link_rejects_missing_invite_link():
    bot = SimpleNamespace(revoke_chat_invite_link=AsyncMock())

    with pytest.raises(RevokeChatInviteLinkError):
        await perform_revoke_chat_invite_link(
            bot,
            chat_id=-100123,
            invite_link="",
        )


async def test_perform_revoke_chat_invite_link_raises_raw_error(monkeypatch):
    client = _FakeClient(
        _FakeResponse(
            {
                "ok": False,
                "error_code": 400,
                "description": "Bad Request: invite link not found",
            }
        )
    )
    monkeypatch.setattr(
        revoke_chat_invite_link.httpx,
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

    with pytest.raises(RevokeChatInviteLinkError) as exc_info:
        await perform_revoke_chat_invite_link(
            bot,
            chat_id=-100123,
            invite_link="https://t.me/+missing",
        )

    assert exc_info.value.error_code == 400
    assert "invite link not found" in exc_info.value.message


def test_format_revoke_chat_invite_link_result_escapes_values():
    text = format_revoke_chat_invite_link_result(
        chat_id=-100123,
        link=_link(
            invite_link="https://t.me/+abc<&>",
            name="Ops <team>",
            expire_date=datetime.fromtimestamp(1893456000, tz=timezone.utc),
            member_limit=10,
        ),
    )

    assert "revokeChatInviteLink" in text
    assert "https://t.me/+abc&lt;&amp;&gt;" in text
    assert "Ops &lt;team&gt;" in text
    assert "Is revoked: True" in text
    assert "1893456000" in text
    assert "Member limit: 10" in text


async def test_cmd_revoke_chat_invite_link_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_revoke_chat_invite_link", AsyncMock())
    message = _message(
        text="/revokechatinvitelink -100123 https://t.me/+abc123",
        chat_id=42,
    )

    await commands.cmd_revoke_chat_invite_link(message)

    commands.perform_revoke_chat_invite_link.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_revoke_chat_invite_link_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_revoke_chat_invite_link", AsyncMock())
    message = _message(text="/revokechatinvitelink", chat_id=42)

    await commands.cmd_revoke_chat_invite_link(message)

    commands.perform_revoke_chat_invite_link.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "revokechatinvitelink usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_revoke_chat_invite_link_calls_service(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_revoke_chat_invite_link",
        AsyncMock(return_value=_link()),
    )
    monkeypatch.setattr(
        commands,
        "format_revoke_chat_invite_link_result",
        lambda **kwargs: "ok",
    )
    message = _message(
        text="/revokechatinvitelink -100123 https://t.me/+abc123",
        chat_id=42,
    )

    await commands.cmd_revoke_chat_invite_link(message)

    commands.perform_revoke_chat_invite_link.assert_awaited_once_with(
        message.bot,
        chat_id=-100123,
        invite_link="https://t.me/+abc123",
    )
    message.answer.assert_awaited_once_with("ok", parse_mode="HTML")


async def test_cmd_revoke_chat_invite_link_reports_service_error(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_revoke_chat_invite_link",
        AsyncMock(side_effect=RevokeChatInviteLinkError("invite link not found")),
    )
    message = _message(
        text="/revokechatinvitelink -100123 https://t.me/+abc123",
        chat_id=42,
    )

    await commands.cmd_revoke_chat_invite_link(message)

    args, _kwargs = message.answer.await_args
    assert "Could not revoke the chat invite link" in args[0]
    assert "invite link not found" in args[0]


def test_parse_revoke_chat_invite_link_args():
    assert commands._parse_revoke_chat_invite_link_args(
        "/revokechatinvitelink -100123 https://t.me/+abc123"
    ) == (-100123, "https://t.me/+abc123")


def test_parse_revoke_chat_invite_link_args_rejects_invalid_input():
    assert commands._parse_revoke_chat_invite_link_args("/revokechatinvitelink") is None
    assert (
        commands._parse_revoke_chat_invite_link_args(
            "/revokechatinvitelink nope https://t.me/+abc123"
        )
        is None
    )
    assert (
        commands._parse_revoke_chat_invite_link_args(
            "/revokechatinvitelink -100123 https://t.me/+abc123 extra"
        )
        is None
    )
