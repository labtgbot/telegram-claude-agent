from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import set_business_account_profile_photo
from bot.services.set_business_account_profile_photo import (
    SetBusinessAccountProfilePhotoError,
    format_set_business_account_profile_photo_result,
    perform_set_business_account_profile_photo,
)


BUSINESS_CONNECTION_ID = "bizconn-123"


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
        photo = files["photo"]
        self.posted = {
            "url": url,
            "data": data,
            "filename": photo[0],
            "content": photo[1].read(),
            "content_type": photo[2],
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


def _install_client(monkeypatch, client):
    monkeypatch.setattr(
        set_business_account_profile_photo.httpx,
        "AsyncClient",
        lambda *a, **k: client,
    )


def _photo(tmp_path: Path) -> Path:
    path = tmp_path / "business photo.jpg"
    path.write_bytes(b"fake jpg bytes")
    return path


async def test_perform_set_business_account_profile_photo_posts_multipart(
    monkeypatch, tmp_path
):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)
    photo_path = _photo(tmp_path)

    result = await perform_set_business_account_profile_photo(
        _bot(),
        business_connection_id=f" {BUSINESS_CONNECTION_ID} ",
        photo_path=str(photo_path),
        is_public=True,
    )

    assert result is True
    assert client.posted == {
        "url": "https://api.telegram.org/bot123:abc/setBusinessAccountProfilePhoto",
        "data": {
            "business_connection_id": BUSINESS_CONNECTION_ID,
            "photo": '{"type":"static","photo":"attach://photo"}',
            "is_public": "true",
        },
        "filename": "business photo.jpg",
        "content": b"fake jpg bytes",
        "content_type": "image/jpeg",
    }


async def test_perform_set_business_account_profile_photo_omits_false_public_flag(
    monkeypatch, tmp_path
):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    await perform_set_business_account_profile_photo(
        _bot(),
        business_connection_id=BUSINESS_CONNECTION_ID,
        photo_path=str(_photo(tmp_path)),
    )

    assert "is_public" not in client.posted["data"]


async def test_perform_set_business_account_profile_photo_rejects_invalid_args(
    monkeypatch,
):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    invalid_cases = [
        {"business_connection_id": "", "photo_path": "/tmp/missing.jpg"},
        {"business_connection_id": BUSINESS_CONNECTION_ID, "photo_path": "/tmp/missing.jpg"},
    ]
    for kwargs in invalid_cases:
        with pytest.raises(SetBusinessAccountProfilePhotoError):
            await perform_set_business_account_profile_photo(_bot(), **kwargs)

    assert client.posted is None


async def test_perform_set_business_account_profile_photo_raises_on_telegram_error(
    monkeypatch, tmp_path
):
    client = _FakeClient(
        response=_FakeResponse(
            {
                "ok": False,
                "error_code": 403,
                "description": "Forbidden: bot lacks can_edit_profile_photo right",
            }
        )
    )
    _install_client(monkeypatch, client)

    with pytest.raises(SetBusinessAccountProfilePhotoError) as excinfo:
        await perform_set_business_account_profile_photo(
            _bot(),
            business_connection_id=BUSINESS_CONNECTION_ID,
            photo_path=str(_photo(tmp_path)),
        )

    assert excinfo.value.error_code == 403
    assert "can_edit_profile_photo" in str(excinfo.value)


async def test_perform_set_business_account_profile_photo_raises_on_transport_error(
    monkeypatch, tmp_path
):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(SetBusinessAccountProfilePhotoError) as excinfo:
        await perform_set_business_account_profile_photo(
            _bot(),
            business_connection_id=BUSINESS_CONNECTION_ID,
            photo_path=str(_photo(tmp_path)),
        )

    assert "boom" in str(excinfo.value)


def test_format_set_business_account_profile_photo_result_escapes_fields():
    text = format_set_business_account_profile_photo_result(
        business_connection_id="biz<&>",
        photo_path="/tmp/photo<&>.jpg",
        is_public=True,
    )

    assert "setBusinessAccountProfilePhoto" in text
    assert "biz&lt;&amp;&gt;" in text
    assert "/tmp/photo&lt;&amp;&gt;.jpg" in text
    assert "public fallback photo" in text


def test_parse_set_business_account_profile_photo_args():
    assert commands._parse_set_business_account_profile_photo_args(
        f"/setbusinessaccountprofilephoto {BUSINESS_CONNECTION_ID} /tmp/photo.jpg"
    ) == (BUSINESS_CONNECTION_ID, "/tmp/photo.jpg", False)
    assert commands._parse_set_business_account_profile_photo_args(
        f"/setbusinessaccountprofilephoto {BUSINESS_CONNECTION_ID} /tmp/photo.jpg public=true"
    ) == (BUSINESS_CONNECTION_ID, "/tmp/photo.jpg", True)
    assert commands._parse_set_business_account_profile_photo_args(
        f"/setbusinessaccountprofilephoto {BUSINESS_CONNECTION_ID} /tmp/photo with spaces.jpg"
    ) == (BUSINESS_CONNECTION_ID, "/tmp/photo with spaces.jpg", False)
    assert (
        commands._parse_set_business_account_profile_photo_args(
            f"/setbusinessaccountprofilephoto {BUSINESS_CONNECTION_ID} /tmp/photo.jpg public=maybe"
        )
        is None
    )
    assert commands._parse_set_business_account_profile_photo_args(
        "/setbusinessaccountprofilephoto"
    ) is None


def _message(text: str = "/setbusinessaccountprofilephoto", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_set_business_account_profile_photo_rejects_unlisted_chat(
    monkeypatch,
):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_set_business_account_profile_photo",
        AsyncMock(),
    )
    message = _message(
        text=f"/setbusinessaccountprofilephoto {BUSINESS_CONNECTION_ID} /tmp/photo.jpg",
        chat_id=42,
    )

    await commands.cmd_set_business_account_profile_photo(message)

    commands.perform_set_business_account_profile_photo.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_set_business_account_profile_photo_shows_usage_without_args(
    monkeypatch,
):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_set_business_account_profile_photo",
        AsyncMock(),
    )
    message = _message(text="/setbusinessaccountprofilephoto", chat_id=42)

    await commands.cmd_set_business_account_profile_photo(message)

    commands.perform_set_business_account_profile_photo.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "setbusinessaccountprofilephoto usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_set_business_account_profile_photo_calls_service(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_set_business_account_profile_photo",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(
        commands,
        "format_set_business_account_profile_photo_result",
        lambda **_: "ok",
    )
    message = _message(
        text=(
            f"/setbusinessaccountprofilephoto {BUSINESS_CONNECTION_ID} "
            "/tmp/photo.jpg public=true"
        ),
        chat_id=42,
    )

    await commands.cmd_set_business_account_profile_photo(message)

    commands.perform_set_business_account_profile_photo.assert_awaited_once_with(
        message.bot,
        business_connection_id=BUSINESS_CONNECTION_ID,
        photo_path="/tmp/photo.jpg",
        is_public=True,
    )
    message.answer.assert_awaited_once_with("ok", parse_mode="HTML")


async def test_cmd_set_business_account_profile_photo_reports_errors(monkeypatch):
    error = SetBusinessAccountProfilePhotoError(
        "Forbidden: bot lacks can_edit_profile_photo right",
        error_code=403,
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_set_business_account_profile_photo",
        AsyncMock(side_effect=error),
    )
    message = _message(
        text=f"/setbusinessaccountprofilephoto {BUSINESS_CONNECTION_ID} /tmp/photo.jpg",
        chat_id=42,
    )

    await commands.cmd_set_business_account_profile_photo(message)

    args, _ = message.answer.await_args
    assert "Could not set the business account profile photo" in args[0]
    assert "can_edit_profile_photo" not in args[0]
    assert "Please try again later" in args[0]
