from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import set_sticker_keywords
from bot.services.set_sticker_keywords import (
    SET_STICKER_KEYWORDS_LIMIT,
    SetStickerKeywordsError,
    format_set_sticker_keywords_result,
    perform_set_sticker_keywords,
    validate_sticker_keywords,
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
    text: str = "/setstickerkeywords file-id cat, funny",
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
        set_sticker_keywords.httpx,
        "AsyncClient",
        lambda *a, **k: client,
    )


async def test_perform_set_sticker_keywords_posts_raw_payload(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    result = await perform_set_sticker_keywords(
        _bot(),
        sticker=" file-id ",
        keywords=[" cat ", "funny"],
    )

    assert result is True
    assert client.posted == {
        "url": "https://api.telegram.org/bot123:abc/setStickerKeywords",
        "json": {
            "sticker": "file-id",
            "keywords": ["cat", "funny"],
        },
    }


async def test_perform_set_sticker_keywords_allows_clearing_keywords(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    result = await perform_set_sticker_keywords(
        _bot(),
        sticker="file-id",
        keywords=[],
    )

    assert result is True
    assert client.posted["json"] == {"sticker": "file-id", "keywords": []}


async def test_perform_set_sticker_keywords_rejects_invalid_input(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    with pytest.raises(SetStickerKeywordsError):
        await perform_set_sticker_keywords(
            _bot(),
            sticker=" ",
            keywords=["cat"],
        )

    with pytest.raises(SetStickerKeywordsError):
        await perform_set_sticker_keywords(
            _bot(),
            sticker="file-id",
            keywords=[str(index) for index in range(SET_STICKER_KEYWORDS_LIMIT + 1)],
        )

    assert client.posted is None


async def test_perform_set_sticker_keywords_raises_on_telegram_error(monkeypatch):
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

    with pytest.raises(SetStickerKeywordsError) as excinfo:
        await perform_set_sticker_keywords(
            _bot(),
            sticker="bad",
            keywords=["cat"],
        )

    assert excinfo.value.error_code == 400
    assert "STICKER_INVALID" in str(excinfo.value)


async def test_perform_set_sticker_keywords_raises_on_transport_error(monkeypatch):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(SetStickerKeywordsError) as excinfo:
        await perform_set_sticker_keywords(
            _bot(),
            sticker="file-id",
            keywords=["cat"],
        )

    assert "boom" in str(excinfo.value)


def test_validate_sticker_keywords_trims_and_limits_values():
    assert validate_sticker_keywords([" cat ", "", "funny"]) == ["cat", "funny"]
    assert validate_sticker_keywords([" "]) == []

    with pytest.raises(SetStickerKeywordsError):
        validate_sticker_keywords(
            [str(index) for index in range(SET_STICKER_KEYWORDS_LIMIT + 1)]
        )


def test_format_set_sticker_keywords_result_escapes_fields():
    text = format_set_sticker_keywords_result(
        sticker="file<&>",
        keywords=["cat<&>"],
    )

    assert "setStickerKeywords" in text
    assert "file&lt;&amp;&gt;" in text
    assert "cat&lt;&amp;&gt;" in text


def test_parse_set_sticker_keywords_args():
    assert commands._parse_set_sticker_keywords_args("/setstickerkeywords") is None
    assert commands._parse_set_sticker_keywords_args(
        "/setstickerkeywords file-id cat, funny"
    ) == ("file-id", ["cat", "funny"])
    assert commands._parse_set_sticker_keywords_args(
        "/setstickerkeywords file-id -"
    ) == ("file-id", [])
    assert commands._parse_set_sticker_keywords_args(
        "/setstickerkeywords file-id"
    ) is None


async def test_cmd_set_sticker_keywords_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_set_sticker_keywords", AsyncMock())
    message = _message(chat_id=42)

    await commands.cmd_set_sticker_keywords(message)

    commands.perform_set_sticker_keywords.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_set_sticker_keywords_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_set_sticker_keywords", AsyncMock())
    message = _message(text="/setstickerkeywords", chat_id=42)

    await commands.cmd_set_sticker_keywords(message)

    commands.perform_set_sticker_keywords.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "setstickerkeywords usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_set_sticker_keywords_calls_service(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_set_sticker_keywords",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(
        commands,
        "format_set_sticker_keywords_result",
        lambda **_: "ok",
    )
    message = _message(chat_id=42)

    await commands.cmd_set_sticker_keywords(message)

    commands.perform_set_sticker_keywords.assert_awaited_once_with(
        message.bot,
        sticker="file-id",
        keywords=["cat", "funny"],
    )
    message.answer.assert_awaited_once_with("ok", parse_mode="HTML")


async def test_cmd_set_sticker_keywords_reports_errors(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_set_sticker_keywords",
        AsyncMock(side_effect=SetStickerKeywordsError("boom")),
    )
    message = _message(chat_id=42)

    await commands.cmd_set_sticker_keywords(message)

    args, _kwargs = message.answer.await_args
    assert "Could not set the sticker keywords" in args[0]
