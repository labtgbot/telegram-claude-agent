from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import remove_my_profile_photo
from bot.services.remove_my_profile_photo import (
    RemoveMyProfilePhotoError,
    format_remove_my_profile_photo_result,
    perform_remove_my_profile_photo,
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

    async def post(self, url):
        self.posted = {"url": url}
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


def _message(text: str = "/removemyprofilephoto", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


def _install_client(monkeypatch, client):
    monkeypatch.setattr(
        remove_my_profile_photo.httpx,
        "AsyncClient",
        lambda *a, **k: client,
    )


async def test_perform_remove_my_profile_photo_posts_empty_request(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    result = await perform_remove_my_profile_photo(_bot())

    assert result is True
    assert client.posted == {
        "url": "https://api.telegram.org/bot123:abc/removeMyProfilePhoto",
    }


async def test_perform_remove_my_profile_photo_raises_on_telegram_error(monkeypatch):
    client = _FakeClient(
        response=_FakeResponse(
            {
                "ok": False,
                "error_code": 400,
                "description": "Bad Request: profile photo cannot be removed",
            }
        )
    )
    _install_client(monkeypatch, client)

    with pytest.raises(RemoveMyProfilePhotoError) as excinfo:
        await perform_remove_my_profile_photo(_bot())

    assert excinfo.value.error_code == 400
    assert "profile photo cannot be removed" in str(excinfo.value)


async def test_perform_remove_my_profile_photo_raises_on_transport_error(monkeypatch):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(RemoveMyProfilePhotoError) as excinfo:
        await perform_remove_my_profile_photo(_bot())

    assert "boom" in str(excinfo.value)


def test_format_remove_my_profile_photo_result():
    text = format_remove_my_profile_photo_result()

    assert "removeMyProfilePhoto" in text
    assert "bot profile photo removed" in text
    assert "Rollback" in text


async def test_cmd_remove_my_profile_photo_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_remove_my_profile_photo", AsyncMock())
    message = _message(chat_id=42)

    await commands.cmd_remove_my_profile_photo(message)

    commands.perform_remove_my_profile_photo.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_remove_my_profile_photo_requires_confirm(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_remove_my_profile_photo", AsyncMock())
    message = _message(text="/removemyprofilephoto", chat_id=42)

    await commands.cmd_remove_my_profile_photo(message)

    commands.perform_remove_my_profile_photo.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "removemyprofilephoto usage" in args[0]
    assert "confirm" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_remove_my_profile_photo_calls_service(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_remove_my_profile_photo", AsyncMock(return_value=True)
    )
    monkeypatch.setattr(commands, "format_remove_my_profile_photo_result", lambda: "ok")
    message = _message(text="/removemyprofilephoto confirm", chat_id=42)

    await commands.cmd_remove_my_profile_photo(message)

    commands.perform_remove_my_profile_photo.assert_awaited_once_with(message.bot)
    message.answer.assert_awaited_once_with("ok", parse_mode="HTML")


async def test_cmd_remove_my_profile_photo_reports_telegram_errors(monkeypatch):
    error = RemoveMyProfilePhotoError("Bad Request: profile photo cannot be removed")
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_remove_my_profile_photo", AsyncMock(side_effect=error)
    )
    message = _message(text="/removemyprofilephoto confirm", chat_id=42)

    await commands.cmd_remove_my_profile_photo(message)

    args, _ = message.answer.await_args
    assert "Could not remove the bot profile photo" in args[0]
    assert "profile photo cannot be removed" in args[0]


def test_parse_remove_my_profile_photo_confirm():
    assert commands._parse_remove_my_profile_photo_args(
        "/removemyprofilephoto confirm"
    )


def test_parse_remove_my_profile_photo_rejects_missing_confirm():
    assert not commands._parse_remove_my_profile_photo_args("/removemyprofilephoto")


def test_parse_remove_my_profile_photo_rejects_unknown_args():
    assert not commands._parse_remove_my_profile_photo_args(
        "/removemyprofilephoto now"
    )
