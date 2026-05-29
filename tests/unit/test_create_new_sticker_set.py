from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import create_new_sticker_set
from bot.services.create_new_sticker_set import (
    CreateNewStickerSetError,
    format_create_new_sticker_set_result,
    perform_create_new_sticker_set,
    validate_sticker_type,
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
    text: str = (
        "/createnewstickerset 123 TestSet_by_bot regular static "
        "sticker-file-id 🙂,🚀 Test Set"
    ),
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
        create_new_sticker_set.httpx,
        "AsyncClient",
        lambda *a, **k: client,
    )


async def test_perform_create_new_sticker_set_posts_raw_payload(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    result = await perform_create_new_sticker_set(
        _bot(),
        user_id=123,
        name=" TestSet_by_bot ",
        title=" Test Set ",
        sticker_type=" Regular ",
        sticker_format=" Static ",
        sticker=" sticker-file-id ",
        emoji_list=["🙂", " 🚀 "],
    )

    assert result is True
    assert client.posted == {
        "url": "https://api.telegram.org/bot123:abc/createNewStickerSet",
        "json": {
            "user_id": 123,
            "name": "TestSet_by_bot",
            "title": "Test Set",
            "sticker_type": "regular",
            "stickers": [
                {
                    "sticker": "sticker-file-id",
                    "format": "static",
                    "emoji_list": ["🙂", "🚀"],
                }
            ],
        },
    }


async def test_perform_create_new_sticker_set_rejects_invalid_input(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    with pytest.raises(CreateNewStickerSetError):
        await perform_create_new_sticker_set(
            _bot(),
            user_id=0,
            name="TestSet_by_bot",
            title="Test Set",
            sticker_type="regular",
            sticker_format="static",
            sticker="sticker-file-id",
            emoji_list=["🙂"],
        )

    assert client.posted is None


async def test_perform_create_new_sticker_set_raises_on_telegram_error(monkeypatch):
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

    with pytest.raises(CreateNewStickerSetError) as excinfo:
        await perform_create_new_sticker_set(
            _bot(),
            user_id=123,
            name="bad",
            title="Bad",
            sticker_type="regular",
            sticker_format="static",
            sticker="sticker-file-id",
            emoji_list=["🙂"],
        )

    assert excinfo.value.error_code == 400
    assert "STICKERSET_INVALID" in str(excinfo.value)


async def test_perform_create_new_sticker_set_raises_on_transport_error(monkeypatch):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(CreateNewStickerSetError) as excinfo:
        await perform_create_new_sticker_set(
            _bot(),
            user_id=123,
            name="TestSet_by_bot",
            title="Test Set",
            sticker_type="regular",
            sticker_format="static",
            sticker="sticker-file-id",
            emoji_list=["🙂"],
        )

    assert "boom" in str(excinfo.value)


def test_validate_sticker_type_accepts_known_types():
    assert validate_sticker_type(" Regular ") == "regular"
    assert validate_sticker_type("mask") == "mask"
    assert validate_sticker_type("custom_emoji") == "custom_emoji"

    with pytest.raises(CreateNewStickerSetError):
        validate_sticker_type("photo")


def test_format_create_new_sticker_set_result_escapes_fields():
    text = format_create_new_sticker_set_result(
        user_id=123,
        name="Set<&>",
        title="Title <Set>",
        sticker_type="regular",
        sticker_format="static",
        sticker="file<&>",
        emoji_list=["<smile>"],
    )

    assert "createNewStickerSet" in text
    assert "Set&lt;&amp;&gt;" in text
    assert "Title &lt;Set&gt;" in text
    assert "file&lt;&amp;&gt;" in text
    assert "&lt;smile&gt;" in text


def test_parse_create_new_sticker_set_args():
    assert commands._parse_create_new_sticker_set_args("/createnewstickerset") is None
    assert commands._parse_create_new_sticker_set_args(
        "/createnewstickerset 123 TestSet_by_bot regular static file-id 🙂 Test Set"
    ) == (
        123,
        "TestSet_by_bot",
        "regular",
        "static",
        "file-id",
        ["🙂"],
        "Test Set",
    )
    assert commands._parse_create_new_sticker_set_args(
        "/createnewstickerset 123 TestSet_by_bot custom_emoji static file-id 🙂,🚀 Test Set"
    ) == (
        123,
        "TestSet_by_bot",
        "custom_emoji",
        "static",
        "file-id",
        ["🙂", "🚀"],
        "Test Set",
    )
    assert commands._parse_create_new_sticker_set_args(
        "/createnewstickerset bad TestSet_by_bot regular static file-id 🙂 Test Set"
    ) is None
    assert commands._parse_create_new_sticker_set_args(
        "/createnewstickerset 0 TestSet_by_bot regular static file-id 🙂 Test Set"
    ) is None


async def test_cmd_create_new_sticker_set_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_create_new_sticker_set", AsyncMock())
    message = _message(chat_id=42)

    await commands.cmd_create_new_sticker_set(message)

    commands.perform_create_new_sticker_set.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_create_new_sticker_set_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_create_new_sticker_set", AsyncMock())
    message = _message(text="/createnewstickerset", chat_id=42)

    await commands.cmd_create_new_sticker_set(message)

    commands.perform_create_new_sticker_set.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "createnewstickerset usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_create_new_sticker_set_calls_service(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_create_new_sticker_set",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(
        commands,
        "format_create_new_sticker_set_result",
        lambda **_: "ok",
    )
    message = _message(chat_id=42)

    await commands.cmd_create_new_sticker_set(message)

    commands.perform_create_new_sticker_set.assert_awaited_once_with(
        message.bot,
        user_id=123,
        name="TestSet_by_bot",
        title="Test Set",
        sticker_type="regular",
        sticker_format="static",
        sticker="sticker-file-id",
        emoji_list=["🙂", "🚀"],
    )
    message.answer.assert_awaited_once_with("ok", parse_mode="HTML")


async def test_cmd_create_new_sticker_set_reports_errors(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_create_new_sticker_set",
        AsyncMock(side_effect=CreateNewStickerSetError("boom")),
    )
    message = _message(chat_id=42)

    await commands.cmd_create_new_sticker_set(message)

    args, _kwargs = message.answer.await_args
    assert "Could not create the sticker set" in args[0]
