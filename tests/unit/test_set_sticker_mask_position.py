from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import set_sticker_mask_position
from bot.services.set_sticker_mask_position import (
    SetStickerMaskPositionError,
    format_set_sticker_mask_position_result,
    perform_set_sticker_mask_position,
    validate_mask_position,
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
    text: str = "/setstickermaskposition file-id eyes -0.1 0.2 1.5",
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
        set_sticker_mask_position.httpx,
        "AsyncClient",
        lambda *a, **k: client,
    )


async def test_perform_set_sticker_mask_position_posts_raw_payload(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    result = await perform_set_sticker_mask_position(
        _bot(),
        sticker=" file-id ",
        mask_position={
            "point": " Eyes ",
            "x_shift": "-0.1",
            "y_shift": 0.2,
            "scale": 1.5,
        },
    )

    assert result is True
    assert client.posted == {
        "url": "https://api.telegram.org/bot123:abc/setStickerMaskPosition",
        "json": {
            "sticker": "file-id",
            "mask_position": {
                "point": "eyes",
                "x_shift": -0.1,
                "y_shift": 0.2,
                "scale": 1.5,
            },
        },
    }


async def test_perform_set_sticker_mask_position_omits_mask_position_to_clear(
    monkeypatch,
):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    result = await perform_set_sticker_mask_position(
        _bot(),
        sticker="file-id",
        mask_position=None,
    )

    assert result is True
    assert client.posted["json"] == {"sticker": "file-id"}


async def test_perform_set_sticker_mask_position_rejects_invalid_input(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    with pytest.raises(SetStickerMaskPositionError):
        await perform_set_sticker_mask_position(
            _bot(),
            sticker=" ",
            mask_position=None,
        )

    with pytest.raises(SetStickerMaskPositionError):
        await perform_set_sticker_mask_position(
            _bot(),
            sticker="file-id",
            mask_position={
                "point": "nose",
                "x_shift": 0,
                "y_shift": 0,
                "scale": 1,
            },
        )

    assert client.posted is None


async def test_perform_set_sticker_mask_position_raises_on_telegram_error(
    monkeypatch,
):
    client = _FakeClient(
        response=_FakeResponse(
            {
                "ok": False,
                "error_code": 400,
                "description": "Bad Request: STICKER_INVALID",
            }
        )
    )
    _install_client(monkeypatch, client)

    with pytest.raises(SetStickerMaskPositionError) as excinfo:
        await perform_set_sticker_mask_position(
            _bot(),
            sticker="bad",
            mask_position=None,
        )

    assert excinfo.value.error_code == 400
    assert "STICKER_INVALID" in str(excinfo.value)


async def test_perform_set_sticker_mask_position_raises_on_transport_error(
    monkeypatch,
):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(SetStickerMaskPositionError) as excinfo:
        await perform_set_sticker_mask_position(
            _bot(),
            sticker="file-id",
            mask_position=None,
        )

    assert "boom" in str(excinfo.value)


def test_validate_mask_position_trims_point_and_requires_positive_scale():
    assert validate_mask_position(" Forehead ", 0.0, 0.0, 1.0) == {
        "point": "forehead",
        "x_shift": 0.0,
        "y_shift": 0.0,
        "scale": 1.0,
    }

    with pytest.raises(SetStickerMaskPositionError):
        validate_mask_position("nose", 0, 0, 1)

    with pytest.raises(SetStickerMaskPositionError):
        validate_mask_position("eyes", 0, 0, 0)


def test_format_set_sticker_mask_position_result_escapes_fields():
    text = format_set_sticker_mask_position_result(
        sticker="file<&>",
        mask_position={
            "point": "eyes<&>",
            "x_shift": -0.1,
            "y_shift": 0.2,
            "scale": 1.5,
        },
    )

    assert "setStickerMaskPosition" in text
    assert "file&lt;&amp;&gt;" in text
    assert "eyes&lt;&amp;&gt;" in text
    assert "1.5" in text

    cleared = format_set_sticker_mask_position_result(
        sticker="file-id",
        mask_position=None,
    )
    assert "cleared" in cleared


def test_parse_set_sticker_mask_position_args():
    assert commands._parse_set_sticker_mask_position_args(
        "/setstickermaskposition"
    ) is None
    assert commands._parse_set_sticker_mask_position_args(
        "/setstickermaskposition file-id -"
    ) == ("file-id", None)
    assert commands._parse_set_sticker_mask_position_args(
        "/setstickermaskposition file-id eyes -0.1 0.2 1.5"
    ) == (
        "file-id",
        {
            "point": "eyes",
            "x_shift": -0.1,
            "y_shift": 0.2,
            "scale": 1.5,
        },
    )
    assert commands._parse_set_sticker_mask_position_args(
        "/setstickermaskposition file-id eyes 0 0 0"
    ) is None
    assert commands._parse_set_sticker_mask_position_args(
        "/setstickermaskposition file-id eyes x 0 1"
    ) is None


async def test_cmd_set_sticker_mask_position_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_set_sticker_mask_position", AsyncMock())
    message = _message(chat_id=42)

    await commands.cmd_set_sticker_mask_position(message)

    commands.perform_set_sticker_mask_position.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_set_sticker_mask_position_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_set_sticker_mask_position", AsyncMock())
    message = _message(text="/setstickermaskposition", chat_id=42)

    await commands.cmd_set_sticker_mask_position(message)

    commands.perform_set_sticker_mask_position.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "setstickermaskposition usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_set_sticker_mask_position_calls_service(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_set_sticker_mask_position",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(
        commands,
        "format_set_sticker_mask_position_result",
        lambda **_: "ok",
    )
    message = _message(chat_id=42)

    await commands.cmd_set_sticker_mask_position(message)

    commands.perform_set_sticker_mask_position.assert_awaited_once_with(
        message.bot,
        sticker="file-id",
        mask_position={
            "point": "eyes",
            "x_shift": -0.1,
            "y_shift": 0.2,
            "scale": 1.5,
        },
    )
    message.answer.assert_awaited_once_with("ok", parse_mode="HTML")


async def test_cmd_set_sticker_mask_position_reports_errors(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_set_sticker_mask_position",
        AsyncMock(side_effect=SetStickerMaskPositionError("boom")),
    )
    message = _message(chat_id=42)

    await commands.cmd_set_sticker_mask_position(message)

    args, _kwargs = message.answer.await_args
    assert "Could not set the sticker mask position" in args[0]
