from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import delete_sticker_from_set
from bot.services.delete_sticker_from_set import (
    DeleteStickerFromSetError,
    format_delete_sticker_from_set_result,
    perform_delete_sticker_from_set,
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
    text: str = "/deletestickerfromset file-id",
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
        delete_sticker_from_set.httpx,
        "AsyncClient",
        lambda *a, **k: client,
    )


async def test_perform_delete_sticker_from_set_posts_raw_payload(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    result = await perform_delete_sticker_from_set(_bot(), sticker=" file-id ")

    assert result is True
    assert client.posted == {
        "url": "https://api.telegram.org/bot123:abc/deleteStickerFromSet",
        "json": {"sticker": "file-id"},
    }


async def test_perform_delete_sticker_from_set_rejects_invalid_input(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    with pytest.raises(DeleteStickerFromSetError):
        await perform_delete_sticker_from_set(_bot(), sticker=" ")

    assert client.posted is None


async def test_perform_delete_sticker_from_set_raises_on_telegram_error(monkeypatch):
    client = _FakeClient(
        response=_FakeResponse(
            {
                "ok": False,
                "error_code": 400,
                "description": "Bad Request: STICKER_INVALID",
            }
        )
    )
    _install_client(monkeypatch, client)

    with pytest.raises(DeleteStickerFromSetError) as excinfo:
        await perform_delete_sticker_from_set(_bot(), sticker="bad")

    assert excinfo.value.error_code == 400
    assert "STICKER_INVALID" in str(excinfo.value)


async def test_perform_delete_sticker_from_set_raises_on_transport_error(monkeypatch):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(DeleteStickerFromSetError) as excinfo:
        await perform_delete_sticker_from_set(_bot(), sticker="file-id")

    assert "boom" in str(excinfo.value)


def test_format_delete_sticker_from_set_result_escapes_fields():
    text = format_delete_sticker_from_set_result(sticker="file<&>")

    assert "deleteStickerFromSet" in text
    assert "file&lt;&amp;&gt;" in text


def test_parse_delete_sticker_from_set_args():
    assert commands._parse_delete_sticker_from_set_args("/deletestickerfromset") is None
    assert commands._parse_delete_sticker_from_set_args(
        "/deletestickerfromset file-id"
    ) == "file-id"
    assert (
        commands._parse_delete_sticker_from_set_args(
            "/deletestickerfromset file-id extra"
        )
        is None
    )


async def test_cmd_delete_sticker_from_set_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_delete_sticker_from_set", AsyncMock())
    message = _message(chat_id=42)

    await commands.cmd_delete_sticker_from_set(message)

    commands.perform_delete_sticker_from_set.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_delete_sticker_from_set_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_delete_sticker_from_set", AsyncMock())
    message = _message(text="/deletestickerfromset", chat_id=42)

    await commands.cmd_delete_sticker_from_set(message)

    commands.perform_delete_sticker_from_set.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "deletestickerfromset usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_delete_sticker_from_set_calls_service(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_delete_sticker_from_set",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(commands, "format_delete_sticker_from_set_result", lambda **_: "ok")
    message = _message(chat_id=42)

    await commands.cmd_delete_sticker_from_set(message)

    commands.perform_delete_sticker_from_set.assert_awaited_once_with(
        message.bot,
        sticker="file-id",
    )
    message.answer.assert_awaited_once_with("ok", parse_mode="HTML")


async def test_cmd_delete_sticker_from_set_reports_errors(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_delete_sticker_from_set",
        AsyncMock(side_effect=DeleteStickerFromSetError("boom")),
    )
    message = _message(chat_id=42)

    await commands.cmd_delete_sticker_from_set(message)

    args, _kwargs = message.answer.await_args
    assert "Could not delete the sticker from its set" in args[0]
