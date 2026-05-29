from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import replace_sticker_in_set
from bot.services.replace_sticker_in_set import (
    ReplaceStickerInSetError,
    format_replace_sticker_in_set_result,
    perform_replace_sticker_in_set,
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
    text: str = (
        "/replacestickerinset 123 TestSet_by_bot old-file-id "
        "static new-file-id 🙂,🚀"
    ),
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
        replace_sticker_in_set.httpx,
        "AsyncClient",
        lambda *a, **k: client,
    )


async def test_perform_replace_sticker_in_set_posts_raw_payload(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    result = await perform_replace_sticker_in_set(
        _bot(),
        user_id=123,
        name=" TestSet_by_bot ",
        old_sticker=" old-file-id ",
        sticker_format=" Static ",
        sticker=" new-file-id ",
        emoji_list=["🙂", " 🚀 "],
    )

    assert result is True
    assert client.posted == {
        "url": "https://api.telegram.org/bot123:abc/replaceStickerInSet",
        "json": {
            "user_id": 123,
            "name": "TestSet_by_bot",
            "old_sticker": "old-file-id",
            "sticker": {
                "sticker": "new-file-id",
                "format": "static",
                "emoji_list": ["🙂", "🚀"],
            },
        },
    }


async def test_perform_replace_sticker_in_set_rejects_invalid_input(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    with pytest.raises(ReplaceStickerInSetError):
        await perform_replace_sticker_in_set(
            _bot(),
            user_id=0,
            name="TestSet_by_bot",
            old_sticker="old-file-id",
            sticker_format="static",
            sticker="new-file-id",
            emoji_list=["🙂"],
        )

    assert client.posted is None


async def test_perform_replace_sticker_in_set_raises_on_telegram_error(monkeypatch):
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

    with pytest.raises(ReplaceStickerInSetError) as excinfo:
        await perform_replace_sticker_in_set(
            _bot(),
            user_id=123,
            name="bad",
            old_sticker="old-file-id",
            sticker_format="static",
            sticker="new-file-id",
            emoji_list=["🙂"],
        )

    assert excinfo.value.error_code == 400
    assert "STICKER_INVALID" in str(excinfo.value)


async def test_perform_replace_sticker_in_set_raises_on_transport_error(monkeypatch):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(ReplaceStickerInSetError) as excinfo:
        await perform_replace_sticker_in_set(
            _bot(),
            user_id=123,
            name="TestSet_by_bot",
            old_sticker="old-file-id",
            sticker_format="static",
            sticker="new-file-id",
            emoji_list=["🙂"],
        )

    assert "boom" in str(excinfo.value)


def test_format_replace_sticker_in_set_result_escapes_fields():
    text = format_replace_sticker_in_set_result(
        user_id=123,
        name="Set<&>",
        old_sticker="old<&>",
        sticker_format="static",
        sticker="new<&>",
        emoji_list=["<smile>"],
    )

    assert "replaceStickerInSet" in text
    assert "Set&lt;&amp;&gt;" in text
    assert "old&lt;&amp;&gt;" in text
    assert "new&lt;&amp;&gt;" in text
    assert "&lt;smile&gt;" in text


def test_parse_replace_sticker_in_set_args():
    assert commands._parse_replace_sticker_in_set_args("/replacestickerinset") is None
    assert commands._parse_replace_sticker_in_set_args(
        "/replacestickerinset 123 TestSet_by_bot old-file-id static new-file-id 🙂"
    ) == (123, "TestSet_by_bot", "old-file-id", "static", "new-file-id", ["🙂"])
    assert commands._parse_replace_sticker_in_set_args(
        "/replacestickerinset 123 TestSet_by_bot old-file-id static new-file-id 🙂,🚀"
    ) == (
        123,
        "TestSet_by_bot",
        "old-file-id",
        "static",
        "new-file-id",
        ["🙂", "🚀"],
    )
    assert commands._parse_replace_sticker_in_set_args(
        "/replacestickerinset bad TestSet_by_bot old-file-id static new-file-id 🙂"
    ) is None
    assert commands._parse_replace_sticker_in_set_args(
        "/replacestickerinset 0 TestSet_by_bot old-file-id static new-file-id 🙂"
    ) is None


async def test_cmd_replace_sticker_in_set_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_replace_sticker_in_set", AsyncMock())
    message = _message(chat_id=42)

    await commands.cmd_replace_sticker_in_set(message)

    commands.perform_replace_sticker_in_set.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_replace_sticker_in_set_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_replace_sticker_in_set", AsyncMock())
    message = _message(text="/replacestickerinset", chat_id=42)

    await commands.cmd_replace_sticker_in_set(message)

    commands.perform_replace_sticker_in_set.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "replacestickerinset usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_replace_sticker_in_set_calls_service(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_replace_sticker_in_set",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(commands, "format_replace_sticker_in_set_result", lambda **_: "ok")
    message = _message(chat_id=42)

    await commands.cmd_replace_sticker_in_set(message)

    commands.perform_replace_sticker_in_set.assert_awaited_once_with(
        message.bot,
        user_id=123,
        name="TestSet_by_bot",
        old_sticker="old-file-id",
        sticker_format="static",
        sticker="new-file-id",
        emoji_list=["🙂", "🚀"],
    )
    message.answer.assert_awaited_once_with("ok", parse_mode="HTML")


async def test_cmd_replace_sticker_in_set_reports_errors(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_replace_sticker_in_set",
        AsyncMock(side_effect=ReplaceStickerInSetError("boom")),
    )
    message = _message(chat_id=42)

    await commands.cmd_replace_sticker_in_set(message)

    args, _kwargs = message.answer.await_args
    assert "Could not replace the sticker in the set" in args[0]
