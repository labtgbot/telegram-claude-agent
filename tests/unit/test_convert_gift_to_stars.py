from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import convert_gift_to_stars
from bot.services.convert_gift_to_stars import (
    ConvertGiftToStarsError,
    format_convert_gift_to_stars_result,
    perform_convert_gift_to_stars,
)


BUSINESS_CONNECTION_ID = "bizconn-123"
OWNED_GIFT_ID = "owned-gift-1"


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
        convert_gift_to_stars.httpx,
        "AsyncClient",
        lambda *a, **k: client,
    )


async def test_perform_convert_gift_to_stars_posts_raw_payload(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    result = await perform_convert_gift_to_stars(
        _bot(),
        business_connection_id=f" {BUSINESS_CONNECTION_ID} ",
        owned_gift_id=f" {OWNED_GIFT_ID} ",
    )

    assert result is True
    assert client.posted["url"] == (
        "https://api.telegram.org/bot123:abc/convertGiftToStars"
    )
    assert client.posted["json"] == {
        "business_connection_id": BUSINESS_CONNECTION_ID,
        "owned_gift_id": OWNED_GIFT_ID,
    }


async def test_perform_convert_gift_to_stars_rejects_invalid_args(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    invalid_cases = [
        {"business_connection_id": "", "owned_gift_id": OWNED_GIFT_ID},
        {"business_connection_id": BUSINESS_CONNECTION_ID, "owned_gift_id": ""},
    ]
    for kwargs in invalid_cases:
        with pytest.raises(ConvertGiftToStarsError):
            await perform_convert_gift_to_stars(_bot(), **kwargs)

    assert client.posted is None


async def test_perform_convert_gift_to_stars_raises_on_telegram_error(monkeypatch):
    client = _FakeClient(
        response=_FakeResponse(
            {
                "ok": False,
                "error_code": 403,
                "description": "Forbidden: bot lacks can_convert_gifts_to_stars right",
            }
        )
    )
    _install_client(monkeypatch, client)

    with pytest.raises(ConvertGiftToStarsError) as excinfo:
        await perform_convert_gift_to_stars(
            _bot(),
            business_connection_id=BUSINESS_CONNECTION_ID,
            owned_gift_id=OWNED_GIFT_ID,
        )

    assert excinfo.value.error_code == 403
    assert "can_convert_gifts_to_stars" in str(excinfo.value)


async def test_perform_convert_gift_to_stars_raises_on_transport_error(monkeypatch):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(ConvertGiftToStarsError):
        await perform_convert_gift_to_stars(
            _bot(),
            business_connection_id=BUSINESS_CONNECTION_ID,
            owned_gift_id=OWNED_GIFT_ID,
        )


async def test_perform_convert_gift_to_stars_rejects_unexpected_result(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": {}}))
    _install_client(monkeypatch, client)

    with pytest.raises(ConvertGiftToStarsError):
        await perform_convert_gift_to_stars(
            _bot(),
            business_connection_id=BUSINESS_CONNECTION_ID,
            owned_gift_id=OWNED_GIFT_ID,
        )


def test_format_convert_gift_to_stars_result_escapes_values():
    rendered = format_convert_gift_to_stars_result(
        business_connection_id="biz<conn>",
        owned_gift_id="owned<gift>",
    )

    assert "<b>convertGiftToStars</b>" in rendered
    assert "Business connection: <code>biz&lt;conn&gt;</code>" in rendered
    assert "Owned gift: <code>owned&lt;gift&gt;</code>" in rendered
    assert "cannot be reversed" in rendered


def test_parse_convert_gift_to_stars_args():
    assert commands._parse_convert_gift_to_stars_args(
        f"/convertgiftstars {BUSINESS_CONNECTION_ID} {OWNED_GIFT_ID} confirm"
    ) == (BUSINESS_CONNECTION_ID, OWNED_GIFT_ID, True)
    assert commands._parse_convert_gift_to_stars_args(
        f"/convertgiftstars {BUSINESS_CONNECTION_ID} {OWNED_GIFT_ID}"
    ) == (BUSINESS_CONNECTION_ID, OWNED_GIFT_ID, False)
    assert commands._parse_convert_gift_to_stars_args(
        "/convertgiftstars"
    ) is None
    assert commands._parse_convert_gift_to_stars_args(
        f"/convertgiftstars {BUSINESS_CONNECTION_ID} {OWNED_GIFT_ID} maybe"
    ) is None


def _message(text: str = "/convertgiftstars", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_convert_gift_stars_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_convert_gift_to_stars", AsyncMock())
    message = _message(
        text=f"/convertgiftstars {BUSINESS_CONNECTION_ID} {OWNED_GIFT_ID} confirm",
        chat_id=42,
    )

    await commands.cmd_convert_gift_stars(message)

    commands.perform_convert_gift_to_stars.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_convert_gift_stars_requires_confirmation(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_convert_gift_to_stars", AsyncMock())
    message = _message(
        text=f"/convertgiftstars {BUSINESS_CONNECTION_ID} {OWNED_GIFT_ID}",
        chat_id=42,
    )

    await commands.cmd_convert_gift_stars(message)

    commands.perform_convert_gift_to_stars.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "confirmation required" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_convert_gift_stars_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_convert_gift_to_stars", AsyncMock())
    message = _message(text="/convertgiftstars", chat_id=42)

    await commands.cmd_convert_gift_stars(message)

    commands.perform_convert_gift_to_stars.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "convertgiftstars usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_convert_gift_stars_converts_confirmed_gift(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_convert_gift_to_stars", AsyncMock(return_value=True)
    )
    message = _message(
        text=f"/convertgiftstars {BUSINESS_CONNECTION_ID} {OWNED_GIFT_ID} confirm",
        chat_id=42,
    )

    await commands.cmd_convert_gift_stars(message)

    commands.perform_convert_gift_to_stars.assert_awaited_once_with(
        message.bot,
        business_connection_id=BUSINESS_CONNECTION_ID,
        owned_gift_id=OWNED_GIFT_ID,
    )
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "convertGiftToStars" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_convert_gift_stars_reports_errors(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_convert_gift_to_stars",
        AsyncMock(side_effect=ConvertGiftToStarsError("Bad Request")),
    )
    message = _message(
        text=f"/convertgiftstars {BUSINESS_CONNECTION_ID} {OWNED_GIFT_ID} confirm",
        chat_id=42,
    )

    await commands.cmd_convert_gift_stars(message)

    message.answer.assert_awaited_once_with(
        "Could not convert the gift to Stars: Bad Request"
    )
