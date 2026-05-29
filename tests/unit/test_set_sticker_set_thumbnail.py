from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import set_sticker_set_thumbnail
from bot.services.set_sticker_set_thumbnail import (
    SetStickerSetThumbnailError,
    format_set_sticker_set_thumbnail_result,
    perform_set_sticker_set_thumbnail,
    validate_sticker_set_thumbnail,
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
    text: str = "/setstickersetthumbnail 123 TestSet_by_bot static thumbnail-file-id",
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
        set_sticker_set_thumbnail.httpx,
        "AsyncClient",
        lambda *a, **k: client,
    )


async def test_perform_set_sticker_set_thumbnail_posts_raw_payload(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    result = await perform_set_sticker_set_thumbnail(
        _bot(),
        user_id=123,
        name=" TestSet_by_bot ",
        sticker_format=" Static ",
        thumbnail=" thumbnail-file-id ",
    )

    assert result is True
    assert client.posted == {
        "url": "https://api.telegram.org/bot123:abc/setStickerSetThumbnail",
        "json": {
            "name": "TestSet_by_bot",
            "user_id": 123,
            "format": "static",
            "thumbnail": "thumbnail-file-id",
        },
    }


async def test_perform_set_sticker_set_thumbnail_clears_thumbnail(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    result = await perform_set_sticker_set_thumbnail(
        _bot(),
        user_id=123,
        name="TestSet_by_bot",
        sticker_format="video",
        thumbnail="-",
    )

    assert result is True
    assert client.posted["json"] == {
        "name": "TestSet_by_bot",
        "user_id": 123,
        "format": "video",
    }


async def test_perform_set_sticker_set_thumbnail_rejects_invalid_input(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    with pytest.raises(SetStickerSetThumbnailError):
        await perform_set_sticker_set_thumbnail(
            _bot(),
            user_id=0,
            name="TestSet_by_bot",
            sticker_format="static",
            thumbnail="thumbnail-file-id",
        )

    with pytest.raises(SetStickerSetThumbnailError):
        await perform_set_sticker_set_thumbnail(
            _bot(),
            user_id=123,
            name=" ",
            sticker_format="static",
            thumbnail="thumbnail-file-id",
        )

    with pytest.raises(SetStickerSetThumbnailError):
        await perform_set_sticker_set_thumbnail(
            _bot(),
            user_id=123,
            name="TestSet_by_bot",
            sticker_format="photo",
            thumbnail="thumbnail-file-id",
        )

    with pytest.raises(SetStickerSetThumbnailError):
        await perform_set_sticker_set_thumbnail(
            _bot(),
            user_id=123,
            name="TestSet_by_bot",
            sticker_format="static",
            thumbnail=" ",
        )

    assert client.posted is None


async def test_perform_set_sticker_set_thumbnail_raises_on_telegram_error(
    monkeypatch,
):
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

    with pytest.raises(SetStickerSetThumbnailError) as excinfo:
        await perform_set_sticker_set_thumbnail(
            _bot(),
            user_id=123,
            name="bad",
            sticker_format="static",
            thumbnail="thumbnail-file-id",
        )

    assert excinfo.value.error_code == 400
    assert "STICKERSET_INVALID" in str(excinfo.value)


async def test_perform_set_sticker_set_thumbnail_raises_on_transport_error(
    monkeypatch,
):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(SetStickerSetThumbnailError) as excinfo:
        await perform_set_sticker_set_thumbnail(
            _bot(),
            user_id=123,
            name="TestSet_by_bot",
            sticker_format="static",
            thumbnail="thumbnail-file-id",
        )

    assert "boom" in str(excinfo.value)


def test_validate_sticker_set_thumbnail_trims_or_clears_value():
    assert validate_sticker_set_thumbnail(" file-id ") == "file-id"
    assert validate_sticker_set_thumbnail("-") is None
    assert validate_sticker_set_thumbnail(None) is None

    with pytest.raises(SetStickerSetThumbnailError):
        validate_sticker_set_thumbnail(" ")


def test_format_set_sticker_set_thumbnail_result_escapes_fields():
    text = format_set_sticker_set_thumbnail_result(
        user_id=123,
        name="Set<&>",
        sticker_format="static<&>",
        thumbnail="file<&>",
    )

    assert "setStickerSetThumbnail" in text
    assert "Set&lt;&amp;&gt;" in text
    assert "static&lt;&amp;&gt;" in text
    assert "file&lt;&amp;&gt;" in text

    cleared = format_set_sticker_set_thumbnail_result(
        user_id=123,
        name="Set",
        sticker_format="static",
        thumbnail="-",
    )
    assert "Thumbnail: cleared" in cleared


def test_parse_set_sticker_set_thumbnail_args():
    assert commands._parse_set_sticker_set_thumbnail_args(
        "/setstickersetthumbnail"
    ) is None
    assert commands._parse_set_sticker_set_thumbnail_args(
        "/setstickersetthumbnail 123 TestSet_by_bot static file-id"
    ) == (123, "TestSet_by_bot", "static", "file-id")
    assert commands._parse_set_sticker_set_thumbnail_args(
        "/setstickersetthumbnail 123 TestSet_by_bot static -"
    ) == (123, "TestSet_by_bot", "static", "-")
    assert commands._parse_set_sticker_set_thumbnail_args(
        "/setstickersetthumbnail bad TestSet_by_bot static file-id"
    ) is None
    assert commands._parse_set_sticker_set_thumbnail_args(
        "/setstickersetthumbnail 0 TestSet_by_bot static file-id"
    ) is None


async def test_cmd_set_sticker_set_thumbnail_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_set_sticker_set_thumbnail", AsyncMock())
    message = _message(chat_id=42)

    await commands.cmd_set_sticker_set_thumbnail(message)

    commands.perform_set_sticker_set_thumbnail.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_set_sticker_set_thumbnail_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_set_sticker_set_thumbnail", AsyncMock())
    message = _message(text="/setstickersetthumbnail", chat_id=42)

    await commands.cmd_set_sticker_set_thumbnail(message)

    commands.perform_set_sticker_set_thumbnail.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "setstickersetthumbnail usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_set_sticker_set_thumbnail_calls_service(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_set_sticker_set_thumbnail",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(
        commands,
        "format_set_sticker_set_thumbnail_result",
        lambda **_: "ok",
    )
    message = _message(chat_id=42)

    await commands.cmd_set_sticker_set_thumbnail(message)

    commands.perform_set_sticker_set_thumbnail.assert_awaited_once_with(
        message.bot,
        user_id=123,
        name="TestSet_by_bot",
        sticker_format="static",
        thumbnail="thumbnail-file-id",
    )
    message.answer.assert_awaited_once_with("ok", parse_mode="HTML")


async def test_cmd_set_sticker_set_thumbnail_reports_errors(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_set_sticker_set_thumbnail",
        AsyncMock(side_effect=SetStickerSetThumbnailError("boom")),
    )
    message = _message(chat_id=42)

    await commands.cmd_set_sticker_set_thumbnail(message)

    args, _kwargs = message.answer.await_args
    assert "Could not set the sticker set thumbnail" in args[0]
