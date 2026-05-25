from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import send_live_photo
from bot.services.send_live_photo import SendLivePhotoError, perform_send_live_photo

LIVE_PHOTO_ID = "live-photo-file-id"
PHOTO_ID = "cover-photo-file-id"


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
        send_live_photo.httpx, "AsyncClient", lambda *a, **k: client
    )


async def test_perform_send_live_photo_posts_raw_payload(monkeypatch):
    client = _FakeClient(
        response=_FakeResponse({"ok": True, "result": {"message_id": 555}})
    )
    _install_client(monkeypatch, client)

    result = await perform_send_live_photo(
        _bot(),
        chat_id=42,
        live_photo=LIVE_PHOTO_ID,
        photo=PHOTO_ID,
        caption="hello",
    )

    assert result == {"message_id": 555}
    assert client.posted["url"] == (
        "https://api.telegram.org/bot123:abc/sendLivePhoto"
    )
    assert client.posted["json"] == {
        "chat_id": 42,
        "live_photo": LIVE_PHOTO_ID,
        "photo": PHOTO_ID,
        "caption": "hello",
    }


async def test_perform_send_live_photo_omits_unset_optionals(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": {}}))
    _install_client(monkeypatch, client)

    await perform_send_live_photo(
        _bot(),
        chat_id=7,
        live_photo=LIVE_PHOTO_ID,
        photo=PHOTO_ID,
    )

    assert client.posted["json"] == {
        "chat_id": 7,
        "live_photo": LIVE_PHOTO_ID,
        "photo": PHOTO_ID,
    }


async def test_perform_send_live_photo_raises_on_telegram_error(monkeypatch):
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

    with pytest.raises(SendLivePhotoError) as excinfo:
        await perform_send_live_photo(
            _bot(), chat_id=1, live_photo=LIVE_PHOTO_ID, photo=PHOTO_ID
        )

    assert excinfo.value.error_code == 400
    assert "PHOTO_INVALID_DIMENSIONS" in str(excinfo.value)


async def test_perform_send_live_photo_raises_on_transport_error(monkeypatch):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(SendLivePhotoError):
        await perform_send_live_photo(
            _bot(), chat_id=1, live_photo=LIVE_PHOTO_ID, photo=PHOTO_ID
        )


def test_parse_live_photo_args_variants():
    assert commands._parse_live_photo_args(
        f"/livephoto {LIVE_PHOTO_ID} {PHOTO_ID}"
    ) == (LIVE_PHOTO_ID, PHOTO_ID, None)
    assert commands._parse_live_photo_args(
        f"/livephoto {LIVE_PHOTO_ID} {PHOTO_ID} a nice clip"
    ) == (LIVE_PHOTO_ID, PHOTO_ID, "a nice clip")
    # Missing the static photo reference -> usage.
    assert commands._parse_live_photo_args(f"/livephoto {LIVE_PHOTO_ID}") is None
    assert commands._parse_live_photo_args("/livephoto") is None


def _message(text: str = "/livephoto", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_live_photo_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_live_photo", AsyncMock())
    message = _message(text=f"/livephoto {LIVE_PHOTO_ID} {PHOTO_ID}", chat_id=42)

    await commands.cmd_live_photo(message)

    commands.perform_send_live_photo.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_live_photo_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_live_photo", AsyncMock())
    message = _message(text="/livephoto", chat_id=42)

    await commands.cmd_live_photo(message)

    commands.perform_send_live_photo.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "livephoto usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_live_photo_rejects_too_long_caption(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_live_photo", AsyncMock())
    long_caption = "x" * (commands.LIVE_PHOTO_CAPTION_LIMIT + 1)
    message = _message(
        text=f"/livephoto {LIVE_PHOTO_ID} {PHOTO_ID} {long_caption}", chat_id=42
    )

    await commands.cmd_live_photo(message)

    commands.perform_send_live_photo.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Caption is too long" in args[0]


async def test_cmd_live_photo_sends_with_caption(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_send_live_photo", AsyncMock(return_value={})
    )
    message = _message(
        text=f"/livephoto {LIVE_PHOTO_ID} {PHOTO_ID} a nice clip", chat_id=42
    )

    await commands.cmd_live_photo(message)

    commands.perform_send_live_photo.assert_awaited_once_with(
        message.bot,
        chat_id=42,
        live_photo=LIVE_PHOTO_ID,
        photo=PHOTO_ID,
        caption="a nice clip",
    )
    args, _ = message.answer.await_args
    assert "Sent live photo with caption." in args[0]


async def test_cmd_live_photo_sends_without_caption(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_send_live_photo", AsyncMock(return_value={})
    )
    message = _message(text=f"/livephoto {LIVE_PHOTO_ID} {PHOTO_ID}", chat_id=42)

    await commands.cmd_live_photo(message)

    commands.perform_send_live_photo.assert_awaited_once_with(
        message.bot,
        chat_id=42,
        live_photo=LIVE_PHOTO_ID,
        photo=PHOTO_ID,
        caption=None,
    )
    args, _ = message.answer.await_args
    assert args[0] == "Sent live photo."


async def test_cmd_live_photo_reports_send_errors(monkeypatch):
    error = SendLivePhotoError("Bad Request: PHOTO_INVALID_DIMENSIONS", error_code=400)
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_send_live_photo", AsyncMock(side_effect=error)
    )
    message = _message(text=f"/livephoto {LIVE_PHOTO_ID} {PHOTO_ID}", chat_id=42)

    await commands.cmd_live_photo(message)

    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Could not send the live photo" in args[0]
