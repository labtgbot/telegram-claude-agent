from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import get_forum_topic_icon_stickers
from bot.services.get_forum_topic_icon_stickers import (
    GetForumTopicIconStickersError,
    format_forum_topic_icon_stickers,
    perform_get_forum_topic_icon_stickers,
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


def _message(text: str = "/forumtopiciconstickers", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


def _install_client(monkeypatch, client):
    monkeypatch.setattr(
        get_forum_topic_icon_stickers.httpx,
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
        "set_name": "ForumIcons",
        "custom_emoji_id": "custom-emoji-id",
    }
    payload.update(overrides)
    return payload


async def test_perform_get_forum_topic_icon_stickers_posts_raw_payload(monkeypatch):
    client = _FakeClient(
        response=_FakeResponse({"ok": True, "result": [_sticker_payload()]})
    )
    _install_client(monkeypatch, client)

    stickers = await perform_get_forum_topic_icon_stickers(_bot())

    assert len(stickers) == 1
    assert stickers[0].custom_emoji_id == "custom-emoji-id"
    assert client.posted == {
        "url": "https://api.telegram.org/bot123:abc/getForumTopicIconStickers",
        "json": {},
    }


async def test_perform_get_forum_topic_icon_stickers_raises_on_telegram_error(
    monkeypatch,
):
    client = _FakeClient(
        response=_FakeResponse(
            {
                "ok": False,
                "error_code": 429,
                "description": "Too Many Requests: retry later",
            }
        )
    )
    _install_client(monkeypatch, client)

    with pytest.raises(GetForumTopicIconStickersError) as excinfo:
        await perform_get_forum_topic_icon_stickers(_bot())

    assert excinfo.value.error_code == 429
    assert "Too Many Requests" in str(excinfo.value)


async def test_perform_get_forum_topic_icon_stickers_raises_on_transport_error(
    monkeypatch,
):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(GetForumTopicIconStickersError):
        await perform_get_forum_topic_icon_stickers(_bot())


def test_format_forum_topic_icon_stickers_escapes_values():
    stickers = [
        SimpleNamespace(
            emoji="<star>",
            custom_emoji_id="id<&>",
            set_name="Forum <Icons>",
        )
    ]

    text = format_forum_topic_icon_stickers(stickers)

    assert "getForumTopicIconStickers" in text
    assert "Stickers: 1" in text
    assert "&lt;star&gt;" in text
    assert "id&lt;&amp;&gt;" in text
    assert "Forum &lt;Icons&gt;" in text


async def test_cmd_forum_topic_icon_stickers_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_get_forum_topic_icon_stickers", AsyncMock())
    message = _message(chat_id=42)

    await commands.cmd_forum_topic_icon_stickers(message)

    commands.perform_get_forum_topic_icon_stickers.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_forum_topic_icon_stickers_shows_usage_with_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_get_forum_topic_icon_stickers", AsyncMock())
    message = _message(text="/forumtopiciconstickers extra", chat_id=42)

    await commands.cmd_forum_topic_icon_stickers(message)

    commands.perform_get_forum_topic_icon_stickers.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "forumtopiciconstickers usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_forum_topic_icon_stickers_calls_service(monkeypatch):
    stickers = [SimpleNamespace(emoji="⭐", custom_emoji_id="id", set_name=None)]
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_get_forum_topic_icon_stickers",
        AsyncMock(return_value=stickers),
    )
    monkeypatch.setattr(
        commands,
        "format_forum_topic_icon_stickers",
        lambda result: "ok",
    )
    message = _message(chat_id=42)

    await commands.cmd_forum_topic_icon_stickers(message)

    commands.perform_get_forum_topic_icon_stickers.assert_awaited_once_with(
        message.bot
    )
    args, kwargs = message.answer.await_args
    assert args[0] == "ok"
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_forum_topic_icon_stickers_reports_errors(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_get_forum_topic_icon_stickers",
        AsyncMock(side_effect=GetForumTopicIconStickersError("boom")),
    )
    message = _message(chat_id=42)

    await commands.cmd_forum_topic_icon_stickers(message)

    args, _kwargs = message.answer.await_args
    assert "Could not get forum topic icon stickers" in args[0]
