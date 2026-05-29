from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import transfer_business_account_stars
from bot.services.transfer_business_account_stars import (
    TransferBusinessAccountStarsError,
    format_transfer_business_account_stars_result,
    perform_transfer_business_account_stars,
)


BUSINESS_CONNECTION_ID = "bizconn-123"


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
        transfer_business_account_stars.httpx,
        "AsyncClient",
        lambda *a, **k: client,
    )


async def test_perform_transfer_business_account_stars_posts_raw_payload(
    monkeypatch,
):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    result = await perform_transfer_business_account_stars(
        _bot(), business_connection_id=f" {BUSINESS_CONNECTION_ID} ", star_count=25
    )

    assert result is True
    assert client.posted["url"] == (
        "https://api.telegram.org/bot123:abc/transferBusinessAccountStars"
    )
    assert client.posted["json"] == {
        "business_connection_id": BUSINESS_CONNECTION_ID,
        "star_count": 25,
    }


async def test_perform_transfer_business_account_stars_rejects_invalid_args(
    monkeypatch,
):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    invalid_cases = [
        {"business_connection_id": "", "star_count": 1},
        {"business_connection_id": BUSINESS_CONNECTION_ID, "star_count": 0},
        {"business_connection_id": BUSINESS_CONNECTION_ID, "star_count": -1},
        {"business_connection_id": BUSINESS_CONNECTION_ID, "star_count": "1"},
    ]
    for kwargs in invalid_cases:
        with pytest.raises(TransferBusinessAccountStarsError):
            await perform_transfer_business_account_stars(_bot(), **kwargs)

    assert client.posted is None


async def test_perform_transfer_business_account_stars_raises_on_telegram_error(
    monkeypatch,
):
    client = _FakeClient(
        response=_FakeResponse(
            {
                "ok": False,
                "error_code": 403,
                "description": "Forbidden: bot lacks can_transfer_stars right",
            }
        )
    )
    _install_client(monkeypatch, client)

    with pytest.raises(TransferBusinessAccountStarsError) as excinfo:
        await perform_transfer_business_account_stars(
            _bot(), business_connection_id=BUSINESS_CONNECTION_ID, star_count=25
        )

    assert excinfo.value.error_code == 403
    assert "can_transfer_stars" in str(excinfo.value)


async def test_perform_transfer_business_account_stars_raises_on_transport_error(
    monkeypatch,
):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(TransferBusinessAccountStarsError):
        await perform_transfer_business_account_stars(
            _bot(), business_connection_id=BUSINESS_CONNECTION_ID, star_count=25
        )


async def test_perform_transfer_business_account_stars_rejects_unexpected_result(
    monkeypatch,
):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": {}}))
    _install_client(monkeypatch, client)

    with pytest.raises(TransferBusinessAccountStarsError):
        await perform_transfer_business_account_stars(
            _bot(), business_connection_id=BUSINESS_CONNECTION_ID, star_count=25
        )


def test_format_transfer_business_account_stars_result_escapes_connection_id():
    rendered = format_transfer_business_account_stars_result(
        business_connection_id="biz<conn>",
        star_count=25,
    )

    assert "<b>transferBusinessAccountStars</b>" in rendered
    assert "Business connection: <code>biz&lt;conn&gt;</code>" in rendered
    assert "Transferred Stars: <code>25</code>" in rendered
    assert "cannot be reversed" in rendered


def test_parse_transfer_business_account_stars_args():
    assert commands._parse_transfer_business_account_stars_args(
        f"/transferbusinessstars {BUSINESS_CONNECTION_ID} 25 confirm"
    ) == (BUSINESS_CONNECTION_ID, 25, True)
    assert commands._parse_transfer_business_account_stars_args(
        f"/transferbusinessstars {BUSINESS_CONNECTION_ID} 25"
    ) == (BUSINESS_CONNECTION_ID, 25, False)
    assert commands._parse_transfer_business_account_stars_args(
        "/transferbusinessstars"
    ) is None
    assert commands._parse_transfer_business_account_stars_args(
        f"/transferbusinessstars {BUSINESS_CONNECTION_ID} 0 confirm"
    ) is None
    assert commands._parse_transfer_business_account_stars_args(
        f"/transferbusinessstars {BUSINESS_CONNECTION_ID} nope confirm"
    ) is None


def _message(text: str = "/transferbusinessstars", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_transfer_business_stars_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_transfer_business_account_stars", AsyncMock()
    )
    message = _message(
        text=f"/transferbusinessstars {BUSINESS_CONNECTION_ID} 25 confirm",
        chat_id=42,
    )

    await commands.cmd_transfer_business_stars(message)

    commands.perform_transfer_business_account_stars.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_transfer_business_stars_requires_confirmation(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_transfer_business_account_stars", AsyncMock()
    )
    message = _message(
        text=f"/transferbusinessstars {BUSINESS_CONNECTION_ID} 25",
        chat_id=42,
    )

    await commands.cmd_transfer_business_stars(message)

    commands.perform_transfer_business_account_stars.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "confirmation required" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_transfer_business_stars_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_transfer_business_account_stars", AsyncMock()
    )
    message = _message(text="/transferbusinessstars", chat_id=42)

    await commands.cmd_transfer_business_stars(message)

    commands.perform_transfer_business_account_stars.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "transferbusinessstars usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_transfer_business_stars_transfers_and_formats(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_transfer_business_account_stars", AsyncMock()
    )
    message = _message(
        text=f"/transferbusinessstars {BUSINESS_CONNECTION_ID} 25 confirm",
        chat_id=42,
    )

    await commands.cmd_transfer_business_stars(message)

    commands.perform_transfer_business_account_stars.assert_awaited_once_with(
        message.bot,
        business_connection_id=BUSINESS_CONNECTION_ID,
        star_count=25,
    )
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "Transferred Stars: <code>25</code>" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_transfer_business_stars_reports_service_error(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_transfer_business_account_stars",
        AsyncMock(side_effect=TransferBusinessAccountStarsError("Forbidden")),
    )
    message = _message(
        text=f"/transferbusinessstars {BUSINESS_CONNECTION_ID} 25 confirm",
        chat_id=42,
    )

    await commands.cmd_transfer_business_stars(message)

    message.answer.assert_awaited_once_with(
        "Could not transfer the business account Stars: Forbidden"
    )
