from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import get_business_account_gifts
from bot.services.get_business_account_gifts import (
    GetBusinessAccountGiftsError,
    format_business_account_gifts,
    perform_get_business_account_gifts,
)


BUSINESS_CONNECTION_ID = "bizconn-123"
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
        get_business_account_gifts.httpx,
        "AsyncClient",
        lambda *a, **k: client,
    )


async def test_perform_get_business_account_gifts_posts_raw_payload(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": OWNED_GIFTS}))
    _install_client(monkeypatch, client)

    result = await perform_get_business_account_gifts(
        _bot(),
        business_connection_id=f" {BUSINESS_CONNECTION_ID} ",
        exclude_unsaved=True,
        exclude_unique=True,
        sort_by_price=True,
        offset=" next-page ",
        limit=50,
    )

    assert result == OWNED_GIFTS
    assert client.posted["url"] == (
        "https://api.telegram.org/bot123:abc/getBusinessAccountGifts"
    )
    assert client.posted["json"] == {
        "business_connection_id": BUSINESS_CONNECTION_ID,
        "exclude_unsaved": True,
        "exclude_unique": True,
        "sort_by_price": True,
        "offset": "next-page",
        "limit": 50,
    }


async def test_perform_get_business_account_gifts_rejects_invalid_args(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": OWNED_GIFTS}))
    _install_client(monkeypatch, client)

    invalid_cases = [
        {"business_connection_id": ""},
        {"business_connection_id": BUSINESS_CONNECTION_ID, "limit": 0},
        {"business_connection_id": BUSINESS_CONNECTION_ID, "limit": 101},
        {"business_connection_id": BUSINESS_CONNECTION_ID, "limit": True},
        {"business_connection_id": BUSINESS_CONNECTION_ID, "offset": ""},
        {
            "business_connection_id": BUSINESS_CONNECTION_ID,
            "exclude_saved": "true",
        },
    ]
    for kwargs in invalid_cases:
        with pytest.raises(GetBusinessAccountGiftsError):
            await perform_get_business_account_gifts(_bot(), **kwargs)

    assert client.posted is None


async def test_perform_get_business_account_gifts_raises_on_telegram_error(
    monkeypatch,
):
    client = _FakeClient(
        response=_FakeResponse(
            {
                "ok": False,
                "error_code": 403,
                "description": "Forbidden: bot lacks can_view_gifts_and_stars right",
            }
        )
    )
    _install_client(monkeypatch, client)

    with pytest.raises(GetBusinessAccountGiftsError) as excinfo:
        await perform_get_business_account_gifts(
            _bot(), business_connection_id=BUSINESS_CONNECTION_ID
        )

    assert excinfo.value.error_code == 403
    assert "can_view_gifts_and_stars" in str(excinfo.value)


async def test_perform_get_business_account_gifts_raises_on_transport_error(
    monkeypatch,
):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(GetBusinessAccountGiftsError):
        await perform_get_business_account_gifts(
            _bot(), business_connection_id=BUSINESS_CONNECTION_ID
        )


async def test_perform_get_business_account_gifts_rejects_unexpected_result(
    monkeypatch,
):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    with pytest.raises(GetBusinessAccountGiftsError):
        await perform_get_business_account_gifts(
            _bot(), business_connection_id=BUSINESS_CONNECTION_ID
        )


def test_format_business_account_gifts_escapes_values():
    rendered = format_business_account_gifts(
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
        business_connection_id="biz<conn>",
    )

    assert "<b>Business account gifts</b>" in rendered
    assert "Business connection: <code>biz&lt;conn&gt;</code>" in rendered
    assert "<code>gift&lt;1&gt;</code>" in rendered
    assert "owned=<code>owned&lt;1&gt;</code>" in rendered
    assert "type=<code>regular&lt;gift&gt;</code>" in rendered
    assert "Next offset: <code>next&lt;page&gt;</code>" in rendered


def test_parse_get_business_account_gifts_args():
    assert commands._parse_get_business_account_gifts_args(
        "/businessgifts "
        f"{BUSINESS_CONNECTION_ID} exclude_saved=true exclude_limited=false "
        "sort_by_price=true offset=abc limit=25"
    ) == (
        BUSINESS_CONNECTION_ID,
        {
            "exclude_saved": True,
            "exclude_limited": False,
            "sort_by_price": True,
            "offset": "abc",
            "limit": 25,
        },
    )
    assert commands._parse_get_business_account_gifts_args(
        f"/businessgifts {BUSINESS_CONNECTION_ID}"
    ) == (BUSINESS_CONNECTION_ID, {})
    assert commands._parse_get_business_account_gifts_args("/businessgifts") is None
    assert commands._parse_get_business_account_gifts_args(
        f"/businessgifts {BUSINESS_CONNECTION_ID} exclude_saved=yes"
    ) is None
    assert commands._parse_get_business_account_gifts_args(
        f"/businessgifts {BUSINESS_CONNECTION_ID} limit=101"
    ) is None
    assert commands._parse_get_business_account_gifts_args(
        f"/businessgifts {BUSINESS_CONNECTION_ID} unknown=true"
    ) is None


def _message(text: str = "/businessgifts", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_business_gifts_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_get_business_account_gifts", AsyncMock())
    message = _message(text=f"/businessgifts {BUSINESS_CONNECTION_ID}", chat_id=42)

    await commands.cmd_business_gifts(message)

    commands.perform_get_business_account_gifts.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_business_gifts_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_get_business_account_gifts", AsyncMock())
    message = _message(text="/businessgifts", chat_id=42)

    await commands.cmd_business_gifts(message)

    commands.perform_get_business_account_gifts.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "businessgifts usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_business_gifts_fetches_and_formats(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_get_business_account_gifts",
        AsyncMock(return_value=OWNED_GIFTS),
    )
    message = _message(
        text=(
            f"/businessgifts {BUSINESS_CONNECTION_ID} "
            "exclude_unsaved=true limit=25"
        ),
        chat_id=42,
    )

    await commands.cmd_business_gifts(message)

    commands.perform_get_business_account_gifts.assert_awaited_once_with(
        message.bot,
        business_connection_id=BUSINESS_CONNECTION_ID,
        exclude_unsaved=True,
        limit=25,
    )
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "Business account gifts" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_business_gifts_reports_errors(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_get_business_account_gifts",
        AsyncMock(
            side_effect=GetBusinessAccountGiftsError(
                "Forbidden: bot lacks can_view_gifts_and_stars right"
            )
        ),
    )
    message = _message(text=f"/businessgifts {BUSINESS_CONNECTION_ID}", chat_id=42)

    await commands.cmd_business_gifts(message)

    message.answer.assert_awaited_once_with(
        "Could not fetch the business account gifts. Please try again later."
    )
