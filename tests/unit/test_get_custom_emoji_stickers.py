from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import get_custom_emoji_stickers
from bot.services.get_custom_emoji_stickers import (
    GetCustomEmojiStickersError,
    GetCustomEmojiStickersValidationError,
    format_custom_emoji_stickers,
    perform_get_custom_emoji_stickers,
    validate_custom_emoji_ids,
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


def _message(text: str = "/customemojistickers custom-emoji-id", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


def _install_client(monkeypatch, client):
    monkeypatch.setattr(
        get_custom_emoji_stickers.httpx,
        "AsyncClient",
        lambda *a, **k: client,
    )


def _sticker_payload(**overrides):
    payload = {
        "file_id": "sticker-file-id",
        "file_unique_id": "sticker-unique-id",
        "type": "custom_emoji",
        "width": 512,
        "height": 512,
        "is_animated": False,
        "is_video": False,
        "emoji": "⭐",
        "set_name": "CustomEmojiSet",
        "custom_emoji_id": "custom-emoji-id",
    }
    payload.update(overrides)
    return payload


async def test_perform_get_custom_emoji_stickers_posts_raw_payload(monkeypatch):
    client = _FakeClient(
        response=_FakeResponse({"ok": True, "result": [_sticker_payload()]})
    )
    _install_client(monkeypatch, client)

    stickers = await perform_get_custom_emoji_stickers(
        _bot(),
        custom_emoji_ids=[" custom-emoji-id "],
    )

    assert len(stickers) == 1
    assert stickers[0].custom_emoji_id == "custom-emoji-id"
    assert client.posted == {
        "url": "https://api.telegram.org/bot123:abc/getCustomEmojiStickers",
        "json": {"custom_emoji_ids": ["custom-emoji-id"]},
    }


async def test_perform_get_custom_emoji_stickers_raises_on_telegram_error(
    monkeypatch,
):
    client = _FakeClient(
        response=_FakeResponse(
            {
                "ok": False,
                "error_code": 400,
                "description": "Bad Request: invalid custom emoji identifier",
            }
        )
    )
    _install_client(monkeypatch, client)

    with pytest.raises(GetCustomEmojiStickersError) as excinfo:
        await perform_get_custom_emoji_stickers(
            _bot(),
            custom_emoji_ids=["bad-id"],
        )

    assert excinfo.value.error_code == 400
    assert "invalid custom emoji" in str(excinfo.value)


async def test_perform_get_custom_emoji_stickers_raises_on_transport_error(
    monkeypatch,
):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(GetCustomEmojiStickersError):
        await perform_get_custom_emoji_stickers(
            _bot(),
            custom_emoji_ids=["custom-emoji-id"],
        )


async def test_perform_get_custom_emoji_stickers_rejects_unexpected_result(
    monkeypatch,
):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    with pytest.raises(GetCustomEmojiStickersError):
        await perform_get_custom_emoji_stickers(
            _bot(),
            custom_emoji_ids=["custom-emoji-id"],
        )


def test_validate_custom_emoji_ids_limits_request_size():
    with pytest.raises(GetCustomEmojiStickersValidationError):
        validate_custom_emoji_ids([])

    with pytest.raises(GetCustomEmojiStickersValidationError):
        validate_custom_emoji_ids(["id"] * 201)

    assert validate_custom_emoji_ids([" id "]) == ["id"]


def test_format_custom_emoji_stickers_escapes_values():
    stickers = [
        SimpleNamespace(
            emoji="<star>",
            custom_emoji_id="id<&>",
            file_id="file<&>",
            set_name="Set <Name>",
        )
    ]

    text = format_custom_emoji_stickers(stickers)

    assert "getCustomEmojiStickers" in text
    assert "Stickers: 1" in text
    assert "&lt;star&gt;" in text
    assert "id&lt;&amp;&gt;" in text
    assert "file&lt;&amp;&gt;" in text
    assert "Set &lt;Name&gt;" in text


def test_parse_custom_emoji_stickers_args():
    assert commands._parse_custom_emoji_stickers_args("/customemojistickers") is None
    assert commands._parse_custom_emoji_stickers_args(
        "/customemojistickers id-1 id-2"
    ) == ["id-1", "id-2"]


async def test_cmd_custom_emoji_stickers_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_get_custom_emoji_stickers", AsyncMock())
    message = _message(chat_id=42)

    await commands.cmd_custom_emoji_stickers(message)

    commands.perform_get_custom_emoji_stickers.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_custom_emoji_stickers_shows_usage_without_ids(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_get_custom_emoji_stickers", AsyncMock())
    message = _message(text="/customemojistickers", chat_id=42)

    await commands.cmd_custom_emoji_stickers(message)

    commands.perform_get_custom_emoji_stickers.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "customemojistickers usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_custom_emoji_stickers_calls_service(monkeypatch):
    stickers = [SimpleNamespace(emoji="⭐", custom_emoji_id="id", file_id="file")]
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_get_custom_emoji_stickers",
        AsyncMock(return_value=stickers),
    )
    monkeypatch.setattr(commands, "format_custom_emoji_stickers", lambda result: "ok")
    message = _message(text="/customemojistickers id-1 id-2", chat_id=42)

    await commands.cmd_custom_emoji_stickers(message)

    commands.perform_get_custom_emoji_stickers.assert_awaited_once_with(
        message.bot,
        custom_emoji_ids=["id-1", "id-2"],
    )
    args, kwargs = message.answer.await_args
    assert args[0] == "ok"
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_custom_emoji_stickers_reports_validation_errors(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_get_custom_emoji_stickers",
        AsyncMock(
            side_effect=GetCustomEmojiStickersValidationError("At most 200 ids")
        ),
    )
    message = _message(chat_id=42)

    await commands.cmd_custom_emoji_stickers(message)

    message.answer.assert_awaited_once_with(
        "Custom emoji sticker requests must include 1 to 200 non-empty ids."
    )


async def test_cmd_custom_emoji_stickers_reports_telegram_errors(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_get_custom_emoji_stickers",
        AsyncMock(side_effect=GetCustomEmojiStickersError("boom")),
    )
    message = _message(chat_id=42)

    await commands.cmd_custom_emoji_stickers(message)

    args, _kwargs = message.answer.await_args
    assert "Could not get custom emoji stickers" in args[0]
