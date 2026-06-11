from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import get_chat_gifts
from bot.services.get_chat_gifts import (
    GetChatGiftsError,
    format_chat_gifts,
    perform_get_chat_gifts,
)


CHAT_ID = "@channel"
OWNED_GIFTS = {
    "gifts": [
        {
            "type": "regular",
            "owned_gift_id": "owned-1",
            "gift": {"id": "gift-1", "star_count": 25},
            "is_saved": True,
        }
    ],
    "next_offset": "next-page",
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
        get_chat_gifts.httpx,
        "AsyncClient",
        lambda *a, **k: client,
    )


async def test_perform_get_chat_gifts_posts_raw_payload(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": OWNED_GIFTS}))
    _install_client(monkeypatch, client)

    result = await perform_get_chat_gifts(
        _bot(),
        chat_id=" @channel ",
        exclude_unsaved=True,
        exclude_limited_upgradable=True,
        exclude_from_blockchain=True,
        sort_by_price=True,
        offset=" next-page ",
        limit=50,
    )

    assert result == OWNED_GIFTS
    assert client.posted["url"] == (
        "https://api.telegram.org/bot123:abc/getChatGifts"
    )
    assert client.posted["json"] == {
        "chat_id": CHAT_ID,
        "exclude_unsaved": True,
        "exclude_limited_upgradable": True,
        "exclude_from_blockchain": True,
        "sort_by_price": True,
        "offset": "next-page",
        "limit": 50,
    }


async def test_perform_get_chat_gifts_rejects_invalid_args(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": OWNED_GIFTS}))
    _install_client(monkeypatch, client)

    invalid_cases = [
        {"chat_id": ""},
        {"chat_id": "   "},
        {"chat_id": True},
        {"chat_id": object()},
        {"chat_id": CHAT_ID, "limit": 0},
        {"chat_id": CHAT_ID, "limit": 101},
        {"chat_id": CHAT_ID, "limit": True},
        {"chat_id": CHAT_ID, "offset": ""},
        {"chat_id": CHAT_ID, "exclude_saved": "true"},
    ]
    for kwargs in invalid_cases:
        with pytest.raises(GetChatGiftsError):
            await perform_get_chat_gifts(_bot(), **kwargs)

    assert client.posted is None


async def test_perform_get_chat_gifts_raises_on_telegram_error(monkeypatch):
    client = _FakeClient(
        response=_FakeResponse(
            {
                "ok": False,
                "error_code": 403,
                "description": "Forbidden: not enough rights",
            }
        )
    )
    _install_client(monkeypatch, client)

    with pytest.raises(GetChatGiftsError) as excinfo:
        await perform_get_chat_gifts(_bot(), chat_id=CHAT_ID)

    assert excinfo.value.error_code == 403
    assert "not enough rights" in str(excinfo.value)


async def test_perform_get_chat_gifts_raises_on_transport_error(monkeypatch):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(GetChatGiftsError):
        await perform_get_chat_gifts(_bot(), chat_id=CHAT_ID)


async def test_perform_get_chat_gifts_rejects_unexpected_result(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    with pytest.raises(GetChatGiftsError):
        await perform_get_chat_gifts(_bot(), chat_id=CHAT_ID)


def test_format_chat_gifts_escapes_values():
    rendered = format_chat_gifts(
        {
            "gifts": [
                {
                    "type": "regular<gift>",
                    "owned_gift_id": "owned<1>",
                    "gift": {"id": "gift<1>"},
                    "is_saved": False,
                }
            ],
            "next_offset": "next<page>",
        },
        chat_id="@channel<test>",
    )

    assert "<b>Chat gifts</b>" in rendered
    assert "Chat: <code>@channel&lt;test&gt;</code>" in rendered
    assert "<code>gift&lt;1&gt;</code>" in rendered
    assert "owned=<code>owned&lt;1&gt;</code>" in rendered
    assert "type=<code>regular&lt;gift&gt;</code>" in rendered
    assert "Next offset: <code>next&lt;page&gt;</code>" in rendered


def test_parse_get_chat_gifts_args():
    assert commands._parse_get_chat_gifts_args(
        "/chatgifts @channel exclude_saved=true "
        "exclude_limited_non_upgradable=false sort_by_price=true "
        "offset=abc limit=25"
    ) == (
        CHAT_ID,
        {
            "exclude_saved": True,
            "exclude_limited_non_upgradable": False,
            "sort_by_price": True,
            "offset": "abc",
            "limit": 25,
        },
    )
    assert commands._parse_get_chat_gifts_args("/chatgifts -100123") == (
        -100123,
        {},
    )
    assert commands._parse_get_chat_gifts_args("/chatgifts") is None
    assert commands._parse_get_chat_gifts_args("/chatgifts ") is None
    assert commands._parse_get_chat_gifts_args("/chatgifts 0") is None
    assert commands._parse_get_chat_gifts_args(
        "/chatgifts @channel exclude_saved=yes"
    ) is None
    assert commands._parse_get_chat_gifts_args("/chatgifts @channel limit=101") is None
    assert (
        commands._parse_get_chat_gifts_args("/chatgifts @channel unknown=true")
        is None
    )


def _message(text: str = "/chatgifts", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_chat_gifts_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_get_chat_gifts", AsyncMock())
    message = _message(text="/chatgifts @channel", chat_id=42)

    await commands.cmd_chat_gifts(message)

    commands.perform_get_chat_gifts.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_chat_gifts_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_get_chat_gifts", AsyncMock())
    message = _message(text="/chatgifts", chat_id=42)

    await commands.cmd_chat_gifts(message)

    commands.perform_get_chat_gifts.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "chatgifts usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_chat_gifts_fetches_and_formats(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_get_chat_gifts",
        AsyncMock(return_value=OWNED_GIFTS),
    )
    message = _message(
        text="/chatgifts @channel exclude_unsaved=true limit=25",
        chat_id=42,
    )

    await commands.cmd_chat_gifts(message)

    commands.perform_get_chat_gifts.assert_awaited_once_with(
        message.bot,
        chat_id=CHAT_ID,
        exclude_unsaved=True,
        limit=25,
    )
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "Chat gifts" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_chat_gifts_reports_errors(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_get_chat_gifts",
        AsyncMock(side_effect=GetChatGiftsError("Forbidden: not enough rights")),
    )
    message = _message(text="/chatgifts @channel", chat_id=42)

    await commands.cmd_chat_gifts(message)

    message.answer.assert_awaited_once_with(
        "Could not fetch the chat gifts. Please try again later."
    )
