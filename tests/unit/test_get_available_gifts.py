from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import get_available_gifts
from bot.services.get_available_gifts import (
    GetAvailableGiftsError,
    format_available_gifts,
    perform_get_available_gifts,
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
        get_available_gifts.httpx,
        "AsyncClient",
        lambda *a, **k: client,
    )


def _message(text: str = "/availablegifts", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_perform_get_available_gifts_posts_empty_raw_payload(monkeypatch):
    payload = {"gifts": [{"id": "gift-1", "star_count": 15}]}
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": payload}))
    _install_client(monkeypatch, client)

    result = await perform_get_available_gifts(_bot())

    assert result == payload
    assert client.posted["url"] == (
        "https://api.telegram.org/bot123:abc/getAvailableGifts"
    )
    assert client.posted["json"] == {}


async def test_perform_get_available_gifts_raises_on_telegram_error(monkeypatch):
    client = _FakeClient(
        response=_FakeResponse(
            {
                "ok": False,
                "error_code": 429,
                "description": "Too Many Requests: retry later",
            }
        )
    )
    _install_client(monkeypatch, client)

    with pytest.raises(GetAvailableGiftsError) as excinfo:
        await perform_get_available_gifts(_bot())

    assert excinfo.value.error_code == 429
    assert "retry later" in str(excinfo.value)


async def test_perform_get_available_gifts_raises_on_transport_error(monkeypatch):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(GetAvailableGiftsError):
        await perform_get_available_gifts(_bot())


async def test_perform_get_available_gifts_rejects_unexpected_result(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    with pytest.raises(GetAvailableGiftsError):
        await perform_get_available_gifts(_bot())


def test_format_available_gifts_renders_catalog_summary():
    rendered = format_available_gifts(
        {
            "gifts": [
                {
                    "id": "gift-1",
                    "star_count": 15,
                    "total_count": 100,
                    "remaining_count": 7,
                }
            ]
        }
    )

    assert "<b>Available gifts</b>" in rendered
    assert "Count: <code>1</code>" in rendered
    assert "<code>gift-1</code>" in rendered
    assert "stars=<code>15</code>" in rendered
    assert "remaining=<code>7</code>" in rendered


def test_parse_available_gifts_args_requires_confirm_keyword():
    assert commands._parse_available_gifts_args("/availablegifts") is False
    assert commands._parse_available_gifts_args("/availablegifts confirm") is True
    assert commands._parse_available_gifts_args("/availablegifts nope") is None
    assert commands._parse_available_gifts_args("/availablegifts confirm extra") is None


async def test_cmd_available_gifts_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_get_available_gifts", AsyncMock())
    message = _message(text="/availablegifts confirm", chat_id=42)

    await commands.cmd_available_gifts(message)

    commands.perform_get_available_gifts.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_available_gifts_requires_confirmation(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_get_available_gifts", AsyncMock())
    message = _message(text="/availablegifts", chat_id=42)

    await commands.cmd_available_gifts(message)

    commands.perform_get_available_gifts.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "confirmation required" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_available_gifts_fetches_and_formats(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_get_available_gifts",
        AsyncMock(return_value={"gifts": [{"id": "gift-1", "star_count": 15}]}),
    )
    message = _message(text="/availablegifts confirm", chat_id=42)

    await commands.cmd_available_gifts(message)

    commands.perform_get_available_gifts.assert_awaited_once_with(message.bot)
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "Available gifts" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_available_gifts_reports_errors(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_get_available_gifts",
        AsyncMock(side_effect=GetAvailableGiftsError("Too Many Requests")),
    )
    message = _message(text="/availablegifts confirm", chat_id=42)

    await commands.cmd_available_gifts(message)

    message.answer.assert_awaited_once_with(
        "Could not fetch available gifts: Too Many Requests"
    )
