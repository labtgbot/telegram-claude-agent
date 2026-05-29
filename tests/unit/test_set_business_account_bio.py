from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import set_business_account_bio
from bot.services.set_business_account_bio import (
    MAX_BUSINESS_ACCOUNT_BIO_LENGTH,
    SetBusinessAccountBioError,
    perform_set_business_account_bio,
)


BUSINESS_CONNECTION_ID = "bizconn-123"
BIO = "Open daily from 10:00 to 20:00"


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
        set_business_account_bio.httpx, "AsyncClient", lambda *a, **k: client
    )


async def test_perform_set_business_account_bio_posts_raw_payload(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    result = await perform_set_business_account_bio(
        _bot(),
        business_connection_id=f" {BUSINESS_CONNECTION_ID} ",
        bio=f" {BIO} ",
    )

    assert result is True
    assert client.posted["url"] == (
        "https://api.telegram.org/bot123:abc/setBusinessAccountBio"
    )
    assert client.posted["json"] == {
        "business_connection_id": BUSINESS_CONNECTION_ID,
        "bio": BIO,
    }


async def test_perform_set_business_account_bio_can_clear_bio(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    await perform_set_business_account_bio(
        _bot(),
        business_connection_id=BUSINESS_CONNECTION_ID,
        bio="",
    )

    assert client.posted["json"] == {
        "business_connection_id": BUSINESS_CONNECTION_ID,
        "bio": "",
    }


async def test_perform_set_business_account_bio_omits_missing_bio(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    await perform_set_business_account_bio(
        _bot(),
        business_connection_id=BUSINESS_CONNECTION_ID,
    )

    assert client.posted["json"] == {"business_connection_id": BUSINESS_CONNECTION_ID}


async def test_perform_set_business_account_bio_rejects_invalid_args(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    invalid_cases = [
        {"business_connection_id": "", "bio": BIO},
        {
            "business_connection_id": BUSINESS_CONNECTION_ID,
            "bio": "x" * (MAX_BUSINESS_ACCOUNT_BIO_LENGTH + 1),
        },
    ]
    for kwargs in invalid_cases:
        with pytest.raises(SetBusinessAccountBioError):
            await perform_set_business_account_bio(_bot(), **kwargs)

    assert client.posted is None


async def test_perform_set_business_account_bio_raises_on_telegram_error(monkeypatch):
    client = _FakeClient(
        response=_FakeResponse(
            {
                "ok": False,
                "error_code": 403,
                "description": "Forbidden: bot lacks can_change_bio right",
            }
        )
    )
    _install_client(monkeypatch, client)

    with pytest.raises(SetBusinessAccountBioError) as excinfo:
        await perform_set_business_account_bio(
            _bot(),
            business_connection_id=BUSINESS_CONNECTION_ID,
            bio=BIO,
        )

    assert excinfo.value.error_code == 403
    assert "can_change_bio" in str(excinfo.value)


async def test_perform_set_business_account_bio_raises_on_transport_error(
    monkeypatch,
):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(SetBusinessAccountBioError):
        await perform_set_business_account_bio(
            _bot(),
            business_connection_id=BUSINESS_CONNECTION_ID,
            bio=BIO,
        )


def test_parse_set_business_account_bio_args():
    assert commands._parse_set_business_account_bio_args(
        f"/setbusinessaccountbio {BUSINESS_CONNECTION_ID} {BIO}"
    ) == (BUSINESS_CONNECTION_ID, BIO)
    assert commands._parse_set_business_account_bio_args(
        f"/setbusinessaccountbio {BUSINESS_CONNECTION_ID} clear"
    ) == (BUSINESS_CONNECTION_ID, "")
    assert commands._parse_set_business_account_bio_args(
        "/setbusinessaccountbio"
    ) is None
    assert commands._parse_set_business_account_bio_args(
        f"/setbusinessaccountbio {BUSINESS_CONNECTION_ID}"
    ) is None
    assert commands._parse_set_business_account_bio_args(
        f"/setbusinessaccountbio {BUSINESS_CONNECTION_ID} "
        f"{'x' * (MAX_BUSINESS_ACCOUNT_BIO_LENGTH + 1)}"
    ) is None


def _message(text: str = "/setbusinessaccountbio", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_set_business_account_bio_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_set_business_account_bio", AsyncMock())
    message = _message(
        text=f"/setbusinessaccountbio {BUSINESS_CONNECTION_ID} {BIO}",
        chat_id=42,
    )

    await commands.cmd_set_business_account_bio(message)

    commands.perform_set_business_account_bio.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_set_business_account_bio_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_set_business_account_bio", AsyncMock())
    message = _message(text="/setbusinessaccountbio", chat_id=42)

    await commands.cmd_set_business_account_bio(message)

    commands.perform_set_business_account_bio.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "setbusinessaccountbio usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_set_business_account_bio_sets_bio(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_set_business_account_bio",
        AsyncMock(return_value=True),
    )
    message = _message(
        text=f"/setbusinessaccountbio {BUSINESS_CONNECTION_ID} {BIO}",
        chat_id=42,
    )

    await commands.cmd_set_business_account_bio(message)

    commands.perform_set_business_account_bio.assert_awaited_once_with(
        message.bot,
        business_connection_id=BUSINESS_CONNECTION_ID,
        bio=BIO,
    )
    message.answer.assert_awaited_once_with(
        f"Set business account bio for {BUSINESS_CONNECTION_ID}."
    )


async def test_cmd_set_business_account_bio_clears_bio(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_set_business_account_bio",
        AsyncMock(return_value=True),
    )
    message = _message(
        text=f"/setbusinessaccountbio {BUSINESS_CONNECTION_ID} clear",
        chat_id=42,
    )

    await commands.cmd_set_business_account_bio(message)

    commands.perform_set_business_account_bio.assert_awaited_once_with(
        message.bot,
        business_connection_id=BUSINESS_CONNECTION_ID,
        bio="",
    )
    message.answer.assert_awaited_once_with(
        f"Cleared business account bio for {BUSINESS_CONNECTION_ID}."
    )


async def test_cmd_set_business_account_bio_reports_errors(monkeypatch):
    error = SetBusinessAccountBioError(
        "Forbidden: bot lacks can_change_bio right", error_code=403
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_set_business_account_bio", AsyncMock(side_effect=error)
    )
    message = _message(
        text=f"/setbusinessaccountbio {BUSINESS_CONNECTION_ID} {BIO}",
        chat_id=42,
    )

    await commands.cmd_set_business_account_bio(message)

    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Could not set the business account bio" in args[0]
