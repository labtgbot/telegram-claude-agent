from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import get_sticker_set
from bot.services.get_sticker_set import (
    GetStickerSetError,
    format_sticker_set,
    perform_get_sticker_set,
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


def _message(text: str = "/getstickerset TestSet", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


def _install_client(monkeypatch, client):
    monkeypatch.setattr(
        get_sticker_set.httpx,
        "AsyncClient",
        lambda *a, **k: client,
    )


def _sticker_payload(**overrides):
    payload = {
        "file_id": "sticker-file-id",
        "file_unique_id": "sticker-unique-id",
        "type": "regular",
        "width": 512,
        "height": 512,
        "is_animated": False,
        "is_video": False,
        "emoji": "🙂",
    }
    payload.update(overrides)
    return payload


def _sticker_set_payload(**overrides):
    payload = {
        "name": "TestSet",
        "title": "Test <Set>",
        "sticker_type": "regular",
        "is_animated": False,
        "is_video": False,
        "stickers": [_sticker_payload()],
    }
    payload.update(overrides)
    return payload


async def test_perform_get_sticker_set_posts_raw_payload(monkeypatch):
    client = _FakeClient(
        response=_FakeResponse({"ok": True, "result": _sticker_set_payload()})
    )
    _install_client(monkeypatch, client)

    sticker_set = await perform_get_sticker_set(_bot(), name="TestSet")

    assert sticker_set.name == "TestSet"
    assert len(sticker_set.stickers) == 1
    assert client.posted == {
        "url": "https://api.telegram.org/bot123:abc/getStickerSet",
        "json": {"name": "TestSet"},
    }


async def test_perform_get_sticker_set_raises_on_telegram_error(monkeypatch):
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

    with pytest.raises(GetStickerSetError) as excinfo:
        await perform_get_sticker_set(_bot(), name="bad")

    assert excinfo.value.error_code == 400
    assert "STICKERSET_INVALID" in str(excinfo.value)


async def test_perform_get_sticker_set_raises_on_transport_error(monkeypatch):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(GetStickerSetError):
        await perform_get_sticker_set(_bot(), name="TestSet")


def test_format_sticker_set_escapes_values():
    sticker_set = SimpleNamespace(
        name="Set<&>",
        title="Title <Set>",
        sticker_type="regular",
        stickers=[
            SimpleNamespace(emoji="<smile>", file_id="file<&>"),
        ],
    )

    text = format_sticker_set(sticker_set)

    assert "getStickerSet" in text
    assert "Set&lt;&amp;&gt;" in text
    assert "Title &lt;Set&gt;" in text
    assert "&lt;smile&gt;" in text
    assert "file&lt;&amp;&gt;" in text


async def test_cmd_get_sticker_set_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_get_sticker_set", AsyncMock())
    message = _message(chat_id=42)

    await commands.cmd_get_sticker_set(message)

    commands.perform_get_sticker_set.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_get_sticker_set_shows_usage_without_name(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_get_sticker_set", AsyncMock())
    message = _message(text="/getstickerset", chat_id=42)

    await commands.cmd_get_sticker_set(message)

    commands.perform_get_sticker_set.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "getstickerset usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_get_sticker_set_calls_service(monkeypatch):
    sticker_set = SimpleNamespace(
        name="TestSet",
        title="Test Set",
        sticker_type="regular",
        stickers=[],
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_get_sticker_set",
        AsyncMock(return_value=sticker_set),
    )
    monkeypatch.setattr(commands, "format_sticker_set", lambda result: "ok")
    message = _message(chat_id=42)

    await commands.cmd_get_sticker_set(message)

    commands.perform_get_sticker_set.assert_awaited_once_with(
        message.bot,
        name="TestSet",
    )
    args, kwargs = message.answer.await_args
    assert args[0] == "ok"
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_get_sticker_set_reports_errors(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_get_sticker_set",
        AsyncMock(side_effect=GetStickerSetError("boom")),
    )
    message = _message(chat_id=42)

    await commands.cmd_get_sticker_set(message)

    args, _kwargs = message.answer.await_args
    assert "Could not get the sticker set" in args[0]
