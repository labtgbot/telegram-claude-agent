from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import get_user_gifts
from bot.services.get_user_gifts import (
    GetUserGiftsError,
    format_user_gifts,
    perform_get_user_gifts,
)


USER_ID = 777
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
        get_user_gifts.httpx,
        "AsyncClient",
        lambda *a, **k: client,
    )


async def test_perform_get_user_gifts_posts_raw_payload(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": OWNED_GIFTS}))
    _install_client(monkeypatch, client)

    result = await perform_get_user_gifts(
        _bot(),
        user_id=USER_ID,
        exclude_unsaved=True,
        exclude_unique=True,
        sort_by_price=True,
        offset=" next-page ",
        limit=50,
    )

    assert result == OWNED_GIFTS
    assert client.posted["url"] == (
        "https://api.telegram.org/bot123:abc/getUserGifts"
    )
    assert client.posted["json"] == {
        "user_id": USER_ID,
        "exclude_unsaved": True,
        "exclude_unique": True,
        "sort_by_price": True,
        "offset": "next-page",
        "limit": 50,
    }


async def test_perform_get_user_gifts_rejects_invalid_args(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": OWNED_GIFTS}))
    _install_client(monkeypatch, client)

    invalid_cases = [
        {"user_id": 0},
        {"user_id": -1},
        {"user_id": True},
        {"user_id": USER_ID, "limit": 0},
        {"user_id": USER_ID, "limit": 101},
        {"user_id": USER_ID, "limit": True},
        {"user_id": USER_ID, "offset": ""},
        {"user_id": USER_ID, "exclude_saved": "true"},
    ]
    for kwargs in invalid_cases:
        with pytest.raises(GetUserGiftsError):
            await perform_get_user_gifts(_bot(), **kwargs)

    assert client.posted is None


async def test_perform_get_user_gifts_raises_on_telegram_error(monkeypatch):
    client = _FakeClient(
        response=_FakeResponse(
            {
                "ok": False,
                "error_code": 403,
                "description": "Forbidden: user gifts are unavailable",
            }
        )
    )
    _install_client(monkeypatch, client)

    with pytest.raises(GetUserGiftsError) as excinfo:
        await perform_get_user_gifts(_bot(), user_id=USER_ID)

    assert excinfo.value.error_code == 403
    assert "unavailable" in str(excinfo.value)


async def test_perform_get_user_gifts_raises_on_transport_error(monkeypatch):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(GetUserGiftsError):
        await perform_get_user_gifts(_bot(), user_id=USER_ID)


async def test_perform_get_user_gifts_rejects_unexpected_result(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    with pytest.raises(GetUserGiftsError):
        await perform_get_user_gifts(_bot(), user_id=USER_ID)


def test_format_user_gifts_escapes_values():
    rendered = format_user_gifts(
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
        user_id=USER_ID,
    )

    assert "<b>User gifts</b>" in rendered
    assert f"User: <code>{USER_ID}</code>" in rendered
    assert "<code>gift&lt;1&gt;</code>" in rendered
    assert "owned=<code>owned&lt;1&gt;</code>" in rendered
    assert "type=<code>regular&lt;gift&gt;</code>" in rendered
    assert "Next offset: <code>next&lt;page&gt;</code>" in rendered


def test_parse_get_user_gifts_args():
    assert commands._parse_get_user_gifts_args(
        "/usergifts 777 exclude_saved=true exclude_limited=false "
        "sort_by_price=true offset=abc limit=25"
    ) == (
        USER_ID,
        {
            "exclude_saved": True,
            "exclude_limited": False,
            "sort_by_price": True,
            "offset": "abc",
            "limit": 25,
        },
    )
    assert commands._parse_get_user_gifts_args("/usergifts 777") == (USER_ID, {})
    assert commands._parse_get_user_gifts_args("/usergifts") is None
    assert commands._parse_get_user_gifts_args("/usergifts bad") is None
    assert commands._parse_get_user_gifts_args("/usergifts 0") is None
    assert commands._parse_get_user_gifts_args(
        "/usergifts 777 exclude_saved=yes"
    ) is None
    assert commands._parse_get_user_gifts_args("/usergifts 777 limit=101") is None
    assert commands._parse_get_user_gifts_args("/usergifts 777 unknown=true") is None


def _message(text: str = "/usergifts", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_user_gifts_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_get_user_gifts", AsyncMock())
    message = _message(text="/usergifts 777", chat_id=42)

    await commands.cmd_user_gifts(message)

    commands.perform_get_user_gifts.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_user_gifts_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_get_user_gifts", AsyncMock())
    message = _message(text="/usergifts", chat_id=42)

    await commands.cmd_user_gifts(message)

    commands.perform_get_user_gifts.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "usergifts usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_user_gifts_fetches_and_formats(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_get_user_gifts",
        AsyncMock(return_value=OWNED_GIFTS),
    )
    message = _message(
        text="/usergifts 777 exclude_unsaved=true limit=25",
        chat_id=42,
    )

    await commands.cmd_user_gifts(message)

    commands.perform_get_user_gifts.assert_awaited_once_with(
        message.bot,
        user_id=USER_ID,
        exclude_unsaved=True,
        limit=25,
    )
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "User gifts" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_user_gifts_reports_errors(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_get_user_gifts",
        AsyncMock(side_effect=GetUserGiftsError("Forbidden: user unavailable")),
    )
    message = _message(text="/usergifts 777", chat_id=42)

    await commands.cmd_user_gifts(message)

    message.answer.assert_awaited_once_with(
        "Could not fetch the user gifts: Forbidden: user unavailable"
    )
