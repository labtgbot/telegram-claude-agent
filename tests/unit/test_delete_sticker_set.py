from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import delete_sticker_set
from bot.services.delete_sticker_set import (
    DeleteStickerSetError,
    format_delete_sticker_set_result,
    perform_delete_sticker_set,
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


def _message(
    text: str = "/deletestickerset TestSet_by_bot",
    chat_id: int = 42,
):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


def _install_client(monkeypatch, client):
    monkeypatch.setattr(
        delete_sticker_set.httpx,
        "AsyncClient",
        lambda *a, **k: client,
    )


async def test_perform_delete_sticker_set_posts_raw_payload(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    result = await perform_delete_sticker_set(_bot(), name=" TestSet_by_bot ")

    assert result is True
    assert client.posted == {
        "url": "https://api.telegram.org/bot123:abc/deleteStickerSet",
        "json": {"name": "TestSet_by_bot"},
    }


async def test_perform_delete_sticker_set_rejects_invalid_input(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    with pytest.raises(DeleteStickerSetError):
        await perform_delete_sticker_set(_bot(), name=" ")

    assert client.posted is None


async def test_perform_delete_sticker_set_raises_on_telegram_error(monkeypatch):
    client = _FakeClient(
        response=_FakeResponse(
            {
                "ok": False,
                "error_code": 400,
                "description": "Bad Request: STICKERSET_INVALID",
            }
        )
    )
    _install_client(monkeypatch, client)

    with pytest.raises(DeleteStickerSetError) as excinfo:
        await perform_delete_sticker_set(_bot(), name="bad")

    assert excinfo.value.error_code == 400
    assert "STICKERSET_INVALID" in str(excinfo.value)


async def test_perform_delete_sticker_set_raises_on_transport_error(monkeypatch):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(DeleteStickerSetError) as excinfo:
        await perform_delete_sticker_set(_bot(), name="TestSet_by_bot")

    assert "boom" in str(excinfo.value)


def test_format_delete_sticker_set_result_escapes_fields():
    text = format_delete_sticker_set_result(name="set<&>")

    assert "deleteStickerSet" in text
    assert "set&lt;&amp;&gt;" in text


def test_parse_delete_sticker_set_args():
    assert commands._parse_delete_sticker_set_args("/deletestickerset") is None
    assert commands._parse_delete_sticker_set_args(
        "/deletestickerset TestSet_by_bot"
    ) == "TestSet_by_bot"
    assert (
        commands._parse_delete_sticker_set_args(
            "/deletestickerset TestSet_by_bot extra"
        )
        is None
    )


async def test_cmd_delete_sticker_set_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_delete_sticker_set", AsyncMock())
    message = _message(chat_id=42)

    await commands.cmd_delete_sticker_set(message)

    commands.perform_delete_sticker_set.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_delete_sticker_set_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_delete_sticker_set", AsyncMock())
    message = _message(text="/deletestickerset", chat_id=42)

    await commands.cmd_delete_sticker_set(message)

    commands.perform_delete_sticker_set.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "deletestickerset usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_delete_sticker_set_calls_service(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_delete_sticker_set",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(commands, "format_delete_sticker_set_result", lambda **_: "ok")
    message = _message(chat_id=42)

    await commands.cmd_delete_sticker_set(message)

    commands.perform_delete_sticker_set.assert_awaited_once_with(
        message.bot,
        name="TestSet_by_bot",
    )
    message.answer.assert_awaited_once_with("ok", parse_mode="HTML")


async def test_cmd_delete_sticker_set_reports_errors(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_delete_sticker_set",
        AsyncMock(side_effect=DeleteStickerSetError("boom")),
    )
    message = _message(chat_id=42)

    await commands.cmd_delete_sticker_set(message)

    args, _kwargs = message.answer.await_args
    assert "Could not delete the sticker set" in args[0]
