import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import edit_message_caption
from bot.services.edit_message_caption import (
    EDIT_MESSAGE_CAPTION_LIMIT,
    EditMessageCaptionError,
    perform_edit_message_caption,
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
    monkeypatch.setattr(
        edit_message_caption.httpx, "AsyncClient", lambda *a, **k: client
    )


async def test_perform_edit_message_caption_posts_raw_chat_payload(monkeypatch):
    client = _FakeClient(
        response=_FakeResponse({"ok": True, "result": {"message_id": 55}})
    )
    _install_client(monkeypatch, client)

    result = await perform_edit_message_caption(
        _bot(),
        chat_id=-100123,
        message_id=55,
        caption="updated caption",
        parse_mode="HTML",
        show_caption_above_media=True,
    )

    assert result == {"message_id": 55}
    assert client.posted["url"] == (
        "https://api.telegram.org/bot123:abc/editMessageCaption"
    )
    assert client.posted["json"] == {
        "chat_id": -100123,
        "message_id": 55,
        "caption": "updated caption",
        "parse_mode": "HTML",
        "show_caption_above_media": True,
    }


async def test_perform_edit_message_caption_posts_inline_payload(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    result = await perform_edit_message_caption(
        _bot(),
        inline_message_id=" inline-1 ",
        caption="",
        caption_entities=[{"type": "bold", "offset": 0, "length": 4}],
        reply_markup={"inline_keyboard": []},
    )

    assert result is True
    assert client.posted["json"] == {
        "inline_message_id": "inline-1",
        "caption": "",
        "caption_entities": json.dumps([{"type": "bold", "offset": 0, "length": 4}]),
        "reply_markup": json.dumps({"inline_keyboard": []}),
    }


@pytest.mark.parametrize(
    "kwargs",
    [
        {"chat_id": -100123},
        {"message_id": 55},
        {"chat_id": -100123, "message_id": 0},
        {
            "chat_id": -100123,
            "message_id": 55,
            "inline_message_id": "inline-1",
        },
        {
            "chat_id": -100123,
            "message_id": 55,
            "caption": "x" * (EDIT_MESSAGE_CAPTION_LIMIT + 1),
        },
    ],
)
async def test_perform_edit_message_caption_validates_before_request(
    monkeypatch, kwargs
):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    with pytest.raises(EditMessageCaptionError):
        await perform_edit_message_caption(_bot(), **kwargs)

    assert client.posted is None


async def test_perform_edit_message_caption_raises_on_telegram_error(monkeypatch):
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

    with pytest.raises(EditMessageCaptionError) as excinfo:
        await perform_edit_message_caption(
            _bot(),
            chat_id=-100123,
            message_id=55,
            caption="updated",
        )

    assert excinfo.value.error_code == 400
    assert "can't be edited" in str(excinfo.value)


async def test_perform_edit_message_caption_raises_on_transport_error(monkeypatch):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(EditMessageCaptionError):
        await perform_edit_message_caption(
            _bot(),
            chat_id=-100123,
            message_id=55,
            caption="updated",
        )


def test_parse_edit_message_caption_args_chat_target():
    assert commands._parse_edit_message_caption_args(
        "/editcaption -100123 55 hello world parse_mode=HTML above=true"
    ) == (
        {"chat_id": -100123, "message_id": 55},
        "hello world",
        {"parse_mode": "HTML", "show_caption_above_media": True},
    )


def test_parse_edit_message_caption_args_inline_target_and_clear_caption():
    assert commands._parse_edit_message_caption_args(
        "/editcaption inline=abc123 above=false"
    ) == (
        {"inline_message_id": "abc123"},
        None,
        {"show_caption_above_media": False},
    )


def test_parse_edit_message_caption_args_rejects_invalid_input():
    assert commands._parse_edit_message_caption_args("/editcaption") is None
    assert commands._parse_edit_message_caption_args("/editcaption nope 55") is None
    assert commands._parse_edit_message_caption_args("/editcaption -100123 0") is None
    assert commands._parse_edit_message_caption_args("/editcaption inline=") is None


def _message(text: str = "/editcaption", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_edit_message_caption_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_edit_message_caption", AsyncMock())
    message = _message(text="/editcaption -100123 55 updated", chat_id=42)

    await commands.cmd_edit_message_caption(message)

    commands.perform_edit_message_caption.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_edit_message_caption_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_edit_message_caption", AsyncMock())
    message = _message(text="/editcaption", chat_id=42)

    await commands.cmd_edit_message_caption(message)

    commands.perform_edit_message_caption.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "editcaption usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_edit_message_caption_calls_service(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_edit_message_caption",
        AsyncMock(return_value={"message_id": 55}),
    )
    message = _message(
        text="/editcaption -100123 55 updated caption parse_mode=HTML",
        chat_id=42,
    )

    await commands.cmd_edit_message_caption(message)

    commands.perform_edit_message_caption.assert_awaited_once_with(
        message.bot,
        chat_id=-100123,
        message_id=55,
        caption="updated caption",
        parse_mode="HTML",
    )
    message.answer.assert_awaited_once_with("Edited caption for message 55.")


async def test_cmd_edit_message_caption_reports_service_errors(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_edit_message_caption",
        AsyncMock(side_effect=EditMessageCaptionError("message can't be edited")),
    )
    message = _message(text="/editcaption -100123 55 updated", chat_id=42)

    await commands.cmd_edit_message_caption(message)

    args, _ = message.answer.await_args
    assert "Could not edit the message caption" in args[0]
    assert "can't be edited" not in args[0]
    assert "Please try again later" in args[0]
