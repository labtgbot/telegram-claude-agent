import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import send_paid_media
from bot.services.send_paid_media import SendPaidMediaError, perform_send_paid_media

PHOTO_URL = "https://example.com/teaser.jpg"
PHOTO_ID = "paid-photo-file-id"
MEDIA = [{"type": "photo", "media": PHOTO_URL}]


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
        send_paid_media.httpx, "AsyncClient", lambda *a, **k: client
    )


async def test_perform_send_paid_media_posts_raw_payload(monkeypatch):
    client = _FakeClient(
        response=_FakeResponse({"ok": True, "result": {"message_id": 555}})
    )
    _install_client(monkeypatch, client)

    result = await perform_send_paid_media(
        _bot(),
        chat_id=42,
        star_count=50,
        media=MEDIA,
        caption="hello",
    )

    assert result == {"message_id": 555}
    assert client.posted["url"] == (
        "https://api.telegram.org/bot123:abc/sendPaidMedia"
    )
    assert client.posted["json"] == {
        "chat_id": 42,
        "star_count": 50,
        "media": json.dumps(MEDIA),
        "caption": "hello",
    }
    # The media array must be JSON-serialized into the request body.
    assert json.loads(client.posted["json"]["media"]) == MEDIA


async def test_perform_send_paid_media_omits_unset_optionals(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": {}}))
    _install_client(monkeypatch, client)

    await perform_send_paid_media(
        _bot(),
        chat_id=7,
        star_count=10,
        media=MEDIA,
    )

    assert client.posted["json"] == {
        "chat_id": 7,
        "star_count": 10,
        "media": json.dumps(MEDIA),
    }


async def test_perform_send_paid_media_raises_on_telegram_error(monkeypatch):
    client = _FakeClient(
        response=_FakeResponse(
            {
                "ok": False,
                "error_code": 400,
                "description": "Bad Request: not enough rights to send paid media",
            }
        )
    )
    _install_client(monkeypatch, client)

    with pytest.raises(SendPaidMediaError) as excinfo:
        await perform_send_paid_media(
            _bot(), chat_id=1, star_count=10, media=MEDIA
        )

    assert excinfo.value.error_code == 400
    assert "not enough rights" in str(excinfo.value)


async def test_perform_send_paid_media_raises_on_transport_error(monkeypatch):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(SendPaidMediaError):
        await perform_send_paid_media(
            _bot(), chat_id=1, star_count=10, media=MEDIA
        )


def test_parse_paid_media_args_variants():
    assert commands._parse_paid_media_args(
        f"/paidmedia 50 {PHOTO_URL}"
    ) == (50, PHOTO_URL, None)
    assert commands._parse_paid_media_args(
        f"/paidmedia 50 {PHOTO_URL} a paid teaser"
    ) == (50, PHOTO_URL, "a paid teaser")
    # Missing the media reference -> usage.
    assert commands._parse_paid_media_args("/paidmedia 50") is None
    assert commands._parse_paid_media_args("/paidmedia") is None
    # A non-integer star price -> usage.
    assert commands._parse_paid_media_args(f"/paidmedia free {PHOTO_URL}") is None


def _message(text: str = "/paidmedia", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_paid_media_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_paid_media", AsyncMock())
    message = _message(text=f"/paidmedia 50 {PHOTO_URL}", chat_id=42)

    await commands.cmd_paid_media(message)

    commands.perform_send_paid_media.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_paid_media_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_paid_media", AsyncMock())
    message = _message(text="/paidmedia", chat_id=42)

    await commands.cmd_paid_media(message)

    commands.perform_send_paid_media.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "paidmedia usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


@pytest.mark.parametrize("star_count", [0, commands.PAID_MEDIA_MAX_STARS + 1])
async def test_cmd_paid_media_rejects_out_of_range_stars(monkeypatch, star_count):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_paid_media", AsyncMock())
    message = _message(text=f"/paidmedia {star_count} {PHOTO_URL}", chat_id=42)

    await commands.cmd_paid_media(message)

    commands.perform_send_paid_media.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Star count must be between" in args[0]


async def test_cmd_paid_media_rejects_too_long_caption(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_paid_media", AsyncMock())
    long_caption = "x" * (commands.PAID_MEDIA_CAPTION_LIMIT + 1)
    message = _message(
        text=f"/paidmedia 50 {PHOTO_URL} {long_caption}", chat_id=42
    )

    await commands.cmd_paid_media(message)

    commands.perform_send_paid_media.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Caption is too long" in args[0]


async def test_cmd_paid_media_sends_with_caption(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_send_paid_media", AsyncMock(return_value={})
    )
    message = _message(
        text=f"/paidmedia 50 {PHOTO_URL} a paid teaser", chat_id=42
    )

    await commands.cmd_paid_media(message)

    commands.perform_send_paid_media.assert_awaited_once_with(
        message.bot,
        chat_id=42,
        star_count=50,
        media=[{"type": "photo", "media": PHOTO_URL}],
        caption="a paid teaser",
    )
    args, _ = message.answer.await_args
    assert "Sent paid media with caption." in args[0]


async def test_cmd_paid_media_sends_without_caption(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_send_paid_media", AsyncMock(return_value={})
    )
    message = _message(text=f"/paidmedia 50 {PHOTO_ID}", chat_id=42)

    await commands.cmd_paid_media(message)

    commands.perform_send_paid_media.assert_awaited_once_with(
        message.bot,
        chat_id=42,
        star_count=50,
        media=[{"type": "photo", "media": PHOTO_ID}],
        caption=None,
    )
    args, _ = message.answer.await_args
    assert args[0] == "Sent paid media."


async def test_cmd_paid_media_reports_send_errors(monkeypatch):
    error = SendPaidMediaError(
        "Bad Request: not enough rights to send paid media", error_code=400
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_send_paid_media", AsyncMock(side_effect=error)
    )
    message = _message(text=f"/paidmedia 50 {PHOTO_URL}", chat_id=42)

    await commands.cmd_paid_media(message)

    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Could not send the paid media" in args[0]
