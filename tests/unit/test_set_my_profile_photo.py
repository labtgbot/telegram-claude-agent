from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import set_my_profile_photo
from bot.services.set_my_profile_photo import (
    SetMyProfilePhotoError,
    format_set_my_profile_photo_result,
    perform_set_my_profile_photo,
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

    async def post(self, url, files):
        photo = files["photo"]
        self.posted = {
            "url": url,
            "filename": photo[0],
            "content": photo[1].read(),
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


def _message(text: str = "/setmyprofilephoto", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


def _install_client(monkeypatch, client):
    monkeypatch.setattr(
        set_my_profile_photo.httpx,
        "AsyncClient",
        lambda *a, **k: client,
    )


def _photo(tmp_path: Path) -> Path:
    path = tmp_path / "bot-photo.jpg"
    path.write_bytes(b"fake image bytes")
    return path


async def test_perform_set_my_profile_photo_posts_multipart_upload(
    monkeypatch, tmp_path
):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)
    photo_path = _photo(tmp_path)

    result = await perform_set_my_profile_photo(_bot(), photo_path=str(photo_path))

    assert result is True
    assert client.posted == {
        "url": "https://api.telegram.org/bot123:abc/setMyProfilePhoto",
        "filename": "bot-photo.jpg",
        "content": b"fake image bytes",
    }


async def test_perform_set_my_profile_photo_rejects_missing_file(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    with pytest.raises(SetMyProfilePhotoError) as excinfo:
        await perform_set_my_profile_photo(_bot(), photo_path="/tmp/missing.jpg")

    assert "does not exist" in str(excinfo.value)
    assert client.posted is None


async def test_perform_set_my_profile_photo_raises_on_telegram_error(
    monkeypatch, tmp_path
):
    client = _FakeClient(
        response=_FakeResponse(
            {
                "ok": False,
                "error_code": 400,
                "description": "Bad Request: PHOTO_INVALID_DIMENSIONS",
            }
        )
    )
    _install_client(monkeypatch, client)

    with pytest.raises(SetMyProfilePhotoError) as excinfo:
        await perform_set_my_profile_photo(
            _bot(),
            photo_path=str(_photo(tmp_path)),
        )

    assert excinfo.value.error_code == 400
    assert "PHOTO_INVALID_DIMENSIONS" in str(excinfo.value)


async def test_perform_set_my_profile_photo_raises_on_transport_error(
    monkeypatch, tmp_path
):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(SetMyProfilePhotoError) as excinfo:
        await perform_set_my_profile_photo(
            _bot(),
            photo_path=str(_photo(tmp_path)),
        )

    assert "boom" in str(excinfo.value)


def test_format_set_my_profile_photo_result_escapes_fields():
    text = format_set_my_profile_photo_result(photo_path="/tmp/photo<&>.jpg")

    assert "setMyProfilePhoto" in text
    assert "/tmp/photo&lt;&amp;&gt;.jpg" in text
    assert "bot profile photo updated" in text


async def test_cmd_set_my_profile_photo_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_set_my_profile_photo", AsyncMock())
    message = _message(text="/setmyprofilephoto /tmp/photo.jpg", chat_id=42)

    await commands.cmd_set_my_profile_photo(message)

    commands.perform_set_my_profile_photo.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_set_my_profile_photo_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_set_my_profile_photo", AsyncMock())
    message = _message(text="/setmyprofilephoto", chat_id=42)

    await commands.cmd_set_my_profile_photo(message)

    commands.perform_set_my_profile_photo.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "setmyprofilephoto usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_set_my_profile_photo_calls_service(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_set_my_profile_photo", AsyncMock(return_value=True)
    )
    monkeypatch.setattr(
        commands, "format_set_my_profile_photo_result", lambda **_: "ok"
    )
    message = _message(text="/setmyprofilephoto /tmp/photo.jpg", chat_id=42)

    await commands.cmd_set_my_profile_photo(message)

    commands.perform_set_my_profile_photo.assert_awaited_once_with(
        message.bot,
        photo_path="/tmp/photo.jpg",
    )
    message.answer.assert_awaited_once_with("ok", parse_mode="HTML")


async def test_cmd_set_my_profile_photo_reports_telegram_errors(monkeypatch):
    error = SetMyProfilePhotoError("Bad Request: PHOTO_INVALID_DIMENSIONS")
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_set_my_profile_photo", AsyncMock(side_effect=error)
    )
    message = _message(text="/setmyprofilephoto /tmp/photo.jpg", chat_id=42)

    await commands.cmd_set_my_profile_photo(message)

    args, _ = message.answer.await_args
    assert "Could not set the bot profile photo" in args[0]
    assert "PHOTO_INVALID_DIMENSIONS" in args[0]


def test_parse_set_my_profile_photo_args_required_path():
    assert commands._parse_set_my_profile_photo_args(
        "/setmyprofilephoto /tmp/photo.jpg"
    ) == "/tmp/photo.jpg"


def test_parse_set_my_profile_photo_args_allows_spaces_in_path():
    assert commands._parse_set_my_profile_photo_args(
        "/setmyprofilephoto /tmp/bot photo.jpg"
    ) == "/tmp/bot photo.jpg"


def test_parse_set_my_profile_photo_args_rejects_missing_path():
    assert commands._parse_set_my_profile_photo_args("/setmyprofilephoto") is None
