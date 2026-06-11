from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import verify_user
from bot.services.verify_user import VerifyUserError, perform_verify_user


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
    monkeypatch.setattr(verify_user.httpx, "AsyncClient", lambda *a, **k: client)


def _message(text: str = "/verifyuser", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_perform_verify_user_posts_payload(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    result = await perform_verify_user(_bot(), user_id=777, custom_description="VIP")

    assert result is True
    assert client.posted["url"] == "https://api.telegram.org/bot123:abc/verifyUser"
    assert client.posted["json"] == {"user_id": 777, "custom_description": "VIP"}


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"user_id": 0}, "user_id"),
        ({"user_id": 777, "custom_description": "x" * 71}, "custom_description"),
    ],
)
async def test_perform_verify_user_validates_payload(monkeypatch, kwargs, message):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    with pytest.raises(VerifyUserError) as excinfo:
        await perform_verify_user(_bot(), **kwargs)

    assert message in str(excinfo.value)
    assert client.posted is None


async def test_perform_verify_user_raises_on_telegram_error(monkeypatch):
    client = _FakeClient(
        response=_FakeResponse(
            {
                "ok": False,
                "error_code": 400,
                "description": "Bad Request: user can't be verified",
            }
        )
    )
    _install_client(monkeypatch, client)

    with pytest.raises(VerifyUserError) as excinfo:
        await perform_verify_user(_bot(), user_id=777)

    assert excinfo.value.error_code == 400
    assert "can't be verified" in str(excinfo.value)


async def test_perform_verify_user_raises_on_transport_error(monkeypatch):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(VerifyUserError):
        await perform_verify_user(_bot(), user_id=777)


async def test_perform_verify_user_rejects_unexpected_result(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": {}}))
    _install_client(monkeypatch, client)

    with pytest.raises(VerifyUserError):
        await perform_verify_user(_bot(), user_id=777)


def test_parse_verify_user_args_variants():
    assert commands._parse_verify_user_args("/verifyuser 777") == (777, False, None)
    assert commands._parse_verify_user_args("/verifyuser 777 confirm") == (
        777,
        True,
        None,
    )
    assert commands._parse_verify_user_args("/verifyuser 777 confirm trusted") == (
        777,
        True,
        "trusted",
    )
    assert commands._parse_verify_user_args("/verifyuser bad confirm") is None
    assert commands._parse_verify_user_args("/verifyuser 0 confirm") is None
    assert commands._parse_verify_user_args("/verifyuser 777 maybe") is None


async def test_cmd_verify_user_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_verify_user", AsyncMock())
    message = _message(text="/verifyuser 777 confirm", chat_id=42)

    await commands.cmd_verify_user(message)

    commands.perform_verify_user.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_verify_user_requires_confirmation(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_verify_user", AsyncMock())
    message = _message(text="/verifyuser 777", chat_id=42)

    await commands.cmd_verify_user(message)

    commands.perform_verify_user.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "confirmation required" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_verify_user_verifies_confirmed_user(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_verify_user", AsyncMock(return_value=True))
    message = _message(text="/verifyuser 777 confirm trusted", chat_id=42)

    await commands.cmd_verify_user(message)

    commands.perform_verify_user.assert_awaited_once_with(
        message.bot,
        user_id=777,
        custom_description="trusted",
    )
    message.answer.assert_awaited_once_with("Verified user 777.")


async def test_cmd_verify_user_rejects_too_long_description(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_verify_user", AsyncMock())
    description = "x" * (commands.VERIFY_USER_DESCRIPTION_LIMIT + 1)
    message = _message(text=f"/verifyuser 777 confirm {description}", chat_id=42)

    await commands.cmd_verify_user(message)

    commands.perform_verify_user.assert_not_awaited()
    args, _ = message.answer.await_args
    assert "Verification description is too long" in args[0]


async def test_cmd_verify_user_reports_errors(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_verify_user",
        AsyncMock(side_effect=VerifyUserError("Bad Request")),
    )
    message = _message(text="/verifyuser 777 confirm", chat_id=42)

    await commands.cmd_verify_user(message)

    message.answer.assert_awaited_once_with("Could not verify user. Please try again later.")
