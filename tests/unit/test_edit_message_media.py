import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import edit_message_media
from bot.services.edit_message_media import (
    EDIT_MESSAGE_MEDIA_CAPTION_LIMIT,
    EditMessageMediaError,
    perform_edit_message_media,
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
    monkeypatch.setattr(edit_message_media.httpx, "AsyncClient", lambda *a, **k: client)


async def test_perform_edit_message_media_posts_raw_chat_payload(monkeypatch):
    client = _FakeClient(
        response=_FakeResponse({"ok": True, "result": {"message_id": 55}})
    )
    _install_client(monkeypatch, client)

    result = await perform_edit_message_media(
        _bot(),
        chat_id=-100123,
        message_id=55,
        media_type="photo",
        media="https://example.com/new.jpg",
        caption="updated caption",
        parse_mode="HTML",
        show_caption_above_media=True,
        has_spoiler=True,
    )

    assert result == {"message_id": 55}
    assert client.posted["url"] == "https://api.telegram.org/bot123:abc/editMessageMedia"
    assert client.posted["json"]["chat_id"] == -100123
    assert client.posted["json"]["message_id"] == 55
    assert json.loads(client.posted["json"]["media"]) == {
        "type": "photo",
        "media": "https://example.com/new.jpg",
        "caption": "updated caption",
        "parse_mode": "HTML",
        "show_caption_above_media": True,
        "has_spoiler": True,
    }


async def test_perform_edit_message_media_posts_inline_payload(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    result = await perform_edit_message_media(
        _bot(),
        inline_message_id=" inline-1 ",
        media_type="video",
        media="file-id",
        caption_entities=[{"type": "bold", "offset": 0, "length": 4}],
        reply_markup={"inline_keyboard": []},
    )

    assert result is True
    assert client.posted["json"]["inline_message_id"] == "inline-1"
    assert json.loads(client.posted["json"]["media"]) == {
        "type": "video",
        "media": "file-id",
        "caption_entities": [{"type": "bold", "offset": 0, "length": 4}],
    }
    assert client.posted["json"]["reply_markup"] == json.dumps({"inline_keyboard": []})


@pytest.mark.parametrize(
    "kwargs",
    [
        {"media_type": "photo", "media": "file-id", "chat_id": -100123},
        {"media_type": "photo", "media": "file-id", "message_id": 55},
        {"media_type": "photo", "media": "file-id", "chat_id": -100123, "message_id": 0},
        {
            "media_type": "photo",
            "media": "file-id",
            "chat_id": -100123,
            "message_id": 55,
            "inline_message_id": "inline-1",
        },
        {"media_type": "sticker", "media": "file-id", "chat_id": -100123, "message_id": 55},
        {"media_type": "photo", "media": "", "chat_id": -100123, "message_id": 55},
        {
            "media_type": "photo",
            "media": "file-id",
            "chat_id": -100123,
            "message_id": 55,
            "caption": "x" * (EDIT_MESSAGE_MEDIA_CAPTION_LIMIT + 1),
        },
    ],
)
async def test_perform_edit_message_media_validates_before_request(monkeypatch, kwargs):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    with pytest.raises(EditMessageMediaError):
        await perform_edit_message_media(_bot(), **kwargs)

    assert client.posted is None


async def test_perform_edit_message_media_raises_on_telegram_error(monkeypatch):
    client = _FakeClient(
        response=_FakeResponse(
            {
                "ok": False,
                "error_code": 400,
                "description": "Bad Request: message can't be edited",
            }
        )
    )
    _install_client(monkeypatch, client)

    with pytest.raises(EditMessageMediaError) as excinfo:
        await perform_edit_message_media(
            _bot(),
            chat_id=-100123,
            message_id=55,
            media_type="photo",
            media="file-id",
        )

    assert excinfo.value.error_code == 400
    assert "can't be edited" in str(excinfo.value)


async def test_perform_edit_message_media_raises_on_transport_error(monkeypatch):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(EditMessageMediaError):
        await perform_edit_message_media(
            _bot(),
            chat_id=-100123,
            message_id=55,
            media_type="photo",
            media="file-id",
        )


def test_parse_edit_message_media_args_chat_target():
    assert commands._parse_edit_message_media_args(
        "/editmedia -100123 55 photo file-id hello world parse_mode=HTML above=true spoiler=true"
    ) == (
        {"chat_id": -100123, "message_id": 55},
        "photo",
        "file-id",
        "hello world",
        {"parse_mode": "HTML", "show_caption_above_media": True, "has_spoiler": True},
    )


def test_parse_edit_message_media_args_inline_target_without_caption():
    assert commands._parse_edit_message_media_args(
        "/editmedia inline=abc123 video file-id spoiler=false"
    ) == (
        {"inline_message_id": "abc123"},
        "video",
        "file-id",
        None,
        {"has_spoiler": False},
    )


def test_parse_edit_message_media_args_rejects_invalid_input():
    assert commands._parse_edit_message_media_args("/editmedia") is None
    assert commands._parse_edit_message_media_args("/editmedia nope 55 photo file") is None
    assert commands._parse_edit_message_media_args("/editmedia -100123 0 photo file") is None
    assert commands._parse_edit_message_media_args("/editmedia -100123 55 sticker file") is None
    assert commands._parse_edit_message_media_args("/editmedia inline= photo file") is None


def _message(text: str = "/editmedia", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_edit_message_media_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_edit_message_media", AsyncMock())
    message = _message(text="/editmedia -100123 55 photo file-id", chat_id=42)

    await commands.cmd_edit_message_media(message)

    commands.perform_edit_message_media.assert_not_awaited()
    message.answer.assert_awaited_once_with("This command is restricted to admin chats.")


async def test_cmd_edit_message_media_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_edit_message_media", AsyncMock())
    message = _message(chat_id=42)

    await commands.cmd_edit_message_media(message)

    commands.perform_edit_message_media.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        commands.EDIT_MESSAGE_MEDIA_USAGE, parse_mode="HTML"
    )


async def test_cmd_edit_message_media_calls_service(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_edit_message_media",
        AsyncMock(return_value={"message_id": 55}),
    )
    message = _message(
        text="/editmedia -100123 55 photo file-id updated parse_mode=HTML",
        chat_id=42,
    )

    await commands.cmd_edit_message_media(message)

    commands.perform_edit_message_media.assert_awaited_once_with(
        message.bot,
        media_type="photo",
        media="file-id",
        caption="updated",
        chat_id=-100123,
        message_id=55,
        parse_mode="HTML",
    )
    message.answer.assert_awaited_once_with("Edited media for message 55.")


async def test_cmd_edit_message_media_reports_service_errors(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_edit_message_media",
        AsyncMock(side_effect=EditMessageMediaError("boom")),
    )
    message = _message(text="/editmedia -100123 55 photo file-id", chat_id=42)

    await commands.cmd_edit_message_media(message)

    message.answer.assert_awaited_once_with("Could not edit the message media: boom")
