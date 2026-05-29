from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import set_sticker_set_title
from bot.services.set_sticker_set_title import (
    SET_STICKER_SET_TITLE_LIMIT,
    SetStickerSetTitleError,
    format_set_sticker_set_title_result,
    perform_set_sticker_set_title,
    validate_sticker_set_title,
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
    text: str = "/setstickersettitle TestSet_by_bot New Title",
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
        set_sticker_set_title.httpx,
        "AsyncClient",
        lambda *a, **k: client,
    )


async def test_perform_set_sticker_set_title_posts_raw_payload(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    result = await perform_set_sticker_set_title(
        _bot(),
        name=" TestSet_by_bot ",
        title=" New Title ",
    )

    assert result is True
    assert client.posted == {
        "url": "https://api.telegram.org/bot123:abc/setStickerSetTitle",
        "json": {
            "name": "TestSet_by_bot",
            "title": "New Title",
        },
    }


async def test_perform_set_sticker_set_title_rejects_invalid_input(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    with pytest.raises(SetStickerSetTitleError):
        await perform_set_sticker_set_title(
            _bot(),
            name=" ",
            title="New Title",
        )

    with pytest.raises(SetStickerSetTitleError):
        await perform_set_sticker_set_title(
            _bot(),
            name="TestSet_by_bot",
            title="x" * (SET_STICKER_SET_TITLE_LIMIT + 1),
        )

    assert client.posted is None


async def test_perform_set_sticker_set_title_raises_on_telegram_error(monkeypatch):
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

    with pytest.raises(SetStickerSetTitleError) as excinfo:
        await perform_set_sticker_set_title(
            _bot(),
            name="bad",
            title="New Title",
        )

    assert excinfo.value.error_code == 400
    assert "STICKERSET_INVALID" in str(excinfo.value)


async def test_perform_set_sticker_set_title_raises_on_transport_error(monkeypatch):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(SetStickerSetTitleError) as excinfo:
        await perform_set_sticker_set_title(
            _bot(),
            name="TestSet_by_bot",
            title="New Title",
        )

    assert "boom" in str(excinfo.value)


def test_validate_sticker_set_title_trims_and_limits_value():
    assert validate_sticker_set_title(" New Title ") == "New Title"

    with pytest.raises(SetStickerSetTitleError):
        validate_sticker_set_title(" ")

    with pytest.raises(SetStickerSetTitleError):
        validate_sticker_set_title("x" * (SET_STICKER_SET_TITLE_LIMIT + 1))


def test_format_set_sticker_set_title_result_escapes_fields():
    text = format_set_sticker_set_title_result(
        name="set<&>",
        title="title<&>",
    )

    assert "setStickerSetTitle" in text
    assert "set&lt;&amp;&gt;" in text
    assert "title&lt;&amp;&gt;" in text


def test_parse_set_sticker_set_title_args():
    assert commands._parse_set_sticker_set_title_args("/setstickersettitle") is None
    assert commands._parse_set_sticker_set_title_args(
        "/setstickersettitle TestSet_by_bot New Title"
    ) == ("TestSet_by_bot", "New Title")
    assert commands._parse_set_sticker_set_title_args(
        "/setstickersettitle TestSet_by_bot"
    ) is None
    assert commands._parse_set_sticker_set_title_args(
        "/setstickersettitle TestSet_by_bot   "
    ) is None


async def test_cmd_set_sticker_set_title_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_set_sticker_set_title", AsyncMock())
    message = _message(chat_id=42)

    await commands.cmd_set_sticker_set_title(message)

    commands.perform_set_sticker_set_title.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_set_sticker_set_title_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_set_sticker_set_title", AsyncMock())
    message = _message(text="/setstickersettitle", chat_id=42)

    await commands.cmd_set_sticker_set_title(message)

    commands.perform_set_sticker_set_title.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "setstickersettitle usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_set_sticker_set_title_calls_service(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_set_sticker_set_title",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(
        commands,
        "format_set_sticker_set_title_result",
        lambda **_: "ok",
    )
    message = _message(chat_id=42)

    await commands.cmd_set_sticker_set_title(message)

    commands.perform_set_sticker_set_title.assert_awaited_once_with(
        message.bot,
        name="TestSet_by_bot",
        title="New Title",
    )
    message.answer.assert_awaited_once_with("ok", parse_mode="HTML")


async def test_cmd_set_sticker_set_title_reports_errors(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_set_sticker_set_title",
        AsyncMock(side_effect=SetStickerSetTitleError("boom")),
    )
    message = _message(chat_id=42)

    await commands.cmd_set_sticker_set_title(message)

    args, _kwargs = message.answer.await_args
    assert "Could not set the sticker set title" in args[0]
