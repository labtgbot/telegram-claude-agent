from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import upload_sticker_file
from bot.services.upload_sticker_file import (
    UploadStickerFileError,
    format_upload_sticker_file_result,
    perform_upload_sticker_file,
    validate_sticker_format,
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

    async def post(self, url, data, files):
        sticker = files["sticker"]
        self.posted = {
            "url": url,
            "data": data,
            "filename": sticker[0],
            "content": sticker[1].read(),
        }
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
    text: str = "/uploadstickerfile 123 static /tmp/sticker.webp",
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
        upload_sticker_file.httpx,
        "AsyncClient",
        lambda *a, **k: client,
    )


def _sticker(tmp_path: Path) -> Path:
    path = tmp_path / "sticker.webp"
    path.write_bytes(b"fake sticker bytes")
    return path


async def test_perform_upload_sticker_file_posts_multipart_upload(
    monkeypatch, tmp_path
):
    client = _FakeClient(
        response=_FakeResponse(
            {
                "ok": True,
                "result": {
                    "file_id": "uploaded-file-id",
                    "file_unique_id": "uploaded-unique-id",
                    "file_size": 128,
                },
            }
        )
    )
    _install_client(monkeypatch, client)
    sticker_path = _sticker(tmp_path)

    file = await perform_upload_sticker_file(
        _bot(),
        user_id=123,
        sticker_path=str(sticker_path),
        sticker_format=" Static ",
    )

    assert file.file_id == "uploaded-file-id"
    assert client.posted == {
        "url": "https://api.telegram.org/bot123:abc/uploadStickerFile",
        "data": {"user_id": "123", "sticker_format": "static"},
        "filename": "sticker.webp",
        "content": b"fake sticker bytes",
    }


async def test_perform_upload_sticker_file_rejects_missing_file(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": {}}))
    _install_client(monkeypatch, client)

    with pytest.raises(UploadStickerFileError) as excinfo:
        await perform_upload_sticker_file(
            _bot(),
            user_id=123,
            sticker_path="/tmp/missing.webp",
            sticker_format="static",
        )

    assert "does not exist" in str(excinfo.value)
    assert client.posted is None


async def test_perform_upload_sticker_file_raises_on_telegram_error(
    monkeypatch, tmp_path
):
    client = _FakeClient(
        response=_FakeResponse(
            {
                "ok": False,
                "error_code": 400,
                "description": "Bad Request: STICKER_FILE_INVALID",
            }
        )
    )
    _install_client(monkeypatch, client)

    with pytest.raises(UploadStickerFileError) as excinfo:
        await perform_upload_sticker_file(
            _bot(),
            user_id=123,
            sticker_path=str(_sticker(tmp_path)),
            sticker_format="video",
        )

    assert excinfo.value.error_code == 400
    assert "STICKER_FILE_INVALID" in str(excinfo.value)


async def test_perform_upload_sticker_file_raises_on_transport_error(
    monkeypatch, tmp_path
):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(UploadStickerFileError) as excinfo:
        await perform_upload_sticker_file(
            _bot(),
            user_id=123,
            sticker_path=str(_sticker(tmp_path)),
            sticker_format="animated",
        )

    assert "boom" in str(excinfo.value)


async def test_perform_upload_sticker_file_rejects_unexpected_result(
    monkeypatch, tmp_path
):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    with pytest.raises(UploadStickerFileError):
        await perform_upload_sticker_file(
            _bot(),
            user_id=123,
            sticker_path=str(_sticker(tmp_path)),
            sticker_format="static",
        )


def test_validate_sticker_format_accepts_known_formats():
    assert validate_sticker_format(" Static ") == "static"
    assert validate_sticker_format("animated") == "animated"
    assert validate_sticker_format("video") == "video"

    with pytest.raises(UploadStickerFileError):
        validate_sticker_format("photo")


def test_format_upload_sticker_file_result_escapes_fields():
    file = SimpleNamespace(
        file_id="file<&>",
        file_unique_id="unique<&>",
        file_size=128,
    )

    text = format_upload_sticker_file_result(
        user_id=123,
        sticker_path="/tmp/sticker<&>.webp",
        sticker_format="static",
        file=file,
    )

    assert "uploadStickerFile" in text
    assert "/tmp/sticker&lt;&amp;&gt;.webp" in text
    assert "file&lt;&amp;&gt;" in text
    assert "unique&lt;&amp;&gt;" in text


def test_parse_upload_sticker_file_args():
    assert commands._parse_upload_sticker_file_args("/uploadstickerfile") is None
    assert commands._parse_upload_sticker_file_args(
        "/uploadstickerfile 123 static /tmp/sticker.webp"
    ) == (123, "static", "/tmp/sticker.webp")
    assert commands._parse_upload_sticker_file_args(
        "/uploadstickerfile 123 video /tmp/video sticker.webm"
    ) == (123, "video", "/tmp/video sticker.webm")
    assert commands._parse_upload_sticker_file_args(
        "/uploadstickerfile bad static /tmp/sticker.webp"
    ) is None
    assert commands._parse_upload_sticker_file_args(
        "/uploadstickerfile 0 static /tmp/sticker.webp"
    ) is None


async def test_cmd_upload_sticker_file_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_upload_sticker_file", AsyncMock())
    message = _message(chat_id=42)

    await commands.cmd_upload_sticker_file(message)

    commands.perform_upload_sticker_file.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_upload_sticker_file_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_upload_sticker_file", AsyncMock())
    message = _message(text="/uploadstickerfile", chat_id=42)

    await commands.cmd_upload_sticker_file(message)

    commands.perform_upload_sticker_file.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "uploadstickerfile usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_upload_sticker_file_calls_service(monkeypatch):
    file = SimpleNamespace(file_id="file-id")
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_upload_sticker_file",
        AsyncMock(return_value=file),
    )
    monkeypatch.setattr(commands, "format_upload_sticker_file_result", lambda **_: "ok")
    message = _message(
        text="/uploadstickerfile 123 static /tmp/sticker.webp",
        chat_id=42,
    )

    await commands.cmd_upload_sticker_file(message)

    commands.perform_upload_sticker_file.assert_awaited_once_with(
        message.bot,
        user_id=123,
        sticker_format="static",
        sticker_path="/tmp/sticker.webp",
    )
    message.answer.assert_awaited_once_with("ok", parse_mode="HTML")


async def test_cmd_upload_sticker_file_reports_upload_errors(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_upload_sticker_file",
        AsyncMock(side_effect=UploadStickerFileError("boom")),
    )
    message = _message(chat_id=42)

    await commands.cmd_upload_sticker_file(message)

    args, _kwargs = message.answer.await_args
    assert "Could not upload the sticker file" in args[0]
