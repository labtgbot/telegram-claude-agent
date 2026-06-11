from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import remove_user_verification
from bot.services.remove_user_verification import (
    RemoveUserVerificationError,
    perform_remove_user_verification,
)


class _FakeResponse:
    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data


class _FakeClient:
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
        remove_user_verification.httpx, "AsyncClient", lambda *a, **k: client
    )


def _message(text: str = "/removeuserverification", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_perform_remove_user_verification_posts_payload(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    result = await perform_remove_user_verification(_bot(), user_id=777)

    assert result is True
    assert (
        client.posted["url"]
        == "https://api.telegram.org/bot123:abc/removeUserVerification"
    )
    assert client.posted["json"] == {"user_id": 777}


async def test_perform_remove_user_verification_validates_user_id(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    with pytest.raises(RemoveUserVerificationError) as excinfo:
        await perform_remove_user_verification(_bot(), user_id=0)

    assert "user_id" in str(excinfo.value)
    assert client.posted is None


async def test_perform_remove_user_verification_raises_on_telegram_error(monkeypatch):
    client = _FakeClient(
        response=_FakeResponse(
            {
                "ok": False,
                "error_code": 400,
                "description": "Bad Request: user is not verified",
            }
        )
    )
    _install_client(monkeypatch, client)

    with pytest.raises(RemoveUserVerificationError) as excinfo:
        await perform_remove_user_verification(_bot(), user_id=777)

    assert excinfo.value.error_code == 400
    assert "not verified" in str(excinfo.value)


async def test_perform_remove_user_verification_raises_on_transport_error(monkeypatch):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(RemoveUserVerificationError):
        await perform_remove_user_verification(_bot(), user_id=777)


async def test_perform_remove_user_verification_rejects_unexpected_result(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": {}}))
    _install_client(monkeypatch, client)

    with pytest.raises(RemoveUserVerificationError):
        await perform_remove_user_verification(_bot(), user_id=777)


def test_parse_remove_user_verification_args_variants():
    assert commands._parse_remove_user_verification_args(
        "/removeuserverification 777"
    ) == (777, False)
    assert commands._parse_remove_user_verification_args(
        "/removeuserverification 777 confirm"
    ) == (777, True)
    assert commands._parse_remove_user_verification_args(
        "/removeuserverification bad confirm"
    ) is None
    assert commands._parse_remove_user_verification_args(
        "/removeuserverification 0 confirm"
    ) is None
    assert commands._parse_remove_user_verification_args(
        "/removeuserverification 777 maybe"
    ) is None
    assert commands._parse_remove_user_verification_args(
        "/removeuserverification 777 confirm extra"
    ) is None


async def test_cmd_remove_user_verification_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_remove_user_verification", AsyncMock())
    message = _message(text="/removeuserverification 777 confirm", chat_id=42)

    await commands.cmd_remove_user_verification(message)

    commands.perform_remove_user_verification.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_remove_user_verification_requires_confirmation(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_remove_user_verification", AsyncMock())
    message = _message(text="/removeuserverification 777", chat_id=42)

    await commands.cmd_remove_user_verification(message)

    commands.perform_remove_user_verification.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "confirmation required" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_remove_user_verification_removes_confirmed_user(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_remove_user_verification", AsyncMock(return_value=True)
    )
    message = _message(text="/removeuserverification 777 confirm", chat_id=42)

    await commands.cmd_remove_user_verification(message)

    commands.perform_remove_user_verification.assert_awaited_once_with(
        message.bot,
        user_id=777,
    )
    message.answer.assert_awaited_once_with("Removed verification from user 777.")


async def test_cmd_remove_user_verification_reports_errors(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_remove_user_verification",
        AsyncMock(side_effect=RemoveUserVerificationError("Bad Request")),
    )
    message = _message(text="/removeuserverification 777 confirm", chat_id=42)

    await commands.cmd_remove_user_verification(message)

    message.answer.assert_awaited_once_with(
        "Could not remove user verification. Please try again later."
    )
