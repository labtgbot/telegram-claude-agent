from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import unpin_all_general_forum_topic_messages
from bot.services.unpin_all_general_forum_topic_messages import (
    UnpinAllGeneralForumTopicMessagesError,
    format_unpin_all_general_forum_topic_messages_result,
    perform_unpin_all_general_forum_topic_messages,
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
    text: str = "/unpinallgeneralforumtopicmessages -100123",
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
        unpin_all_general_forum_topic_messages.httpx,
        "AsyncClient",
        lambda *a, **k: client,
    )


async def test_perform_unpin_all_general_forum_topic_messages_posts_raw_payload(
    monkeypatch,
):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    result = await perform_unpin_all_general_forum_topic_messages(
        _bot(),
        chat_id=-100123,
    )

    assert result is True
    assert client.posted == {
        "url": (
            "https://api.telegram.org/bot123:abc/"
            "unpinAllGeneralForumTopicMessages"
        ),
        "json": {"chat_id": -100123},
    }


async def test_perform_unpin_all_general_forum_topic_messages_raises_on_telegram_error(
    monkeypatch,
):
    client = _FakeClient(
        response=_FakeResponse(
            {
                "ok": False,
                "error_code": 400,
                "description": "Bad Request: not enough rights",
            }
        )
    )
    _install_client(monkeypatch, client)

    with pytest.raises(UnpinAllGeneralForumTopicMessagesError) as excinfo:
        await perform_unpin_all_general_forum_topic_messages(
            _bot(),
            chat_id=-100123,
        )

    assert excinfo.value.error_code == 400
    assert "not enough rights" in str(excinfo.value)


async def test_perform_unpin_all_general_forum_topic_messages_raises_on_transport_error(
    monkeypatch,
):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(UnpinAllGeneralForumTopicMessagesError):
        await perform_unpin_all_general_forum_topic_messages(
            _bot(),
            chat_id=-100123,
        )


def test_format_unpin_all_general_forum_topic_messages_result():
    text = format_unpin_all_general_forum_topic_messages_result(chat_id=-100123)

    assert "unpinAllGeneralForumTopicMessages" in text
    assert "-100123" in text
    assert "all pinned General forum topic messages unpinned" in text


async def test_cmd_unpin_all_general_forum_topic_messages_rejects_non_admin_chat(
    monkeypatch,
):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(
        commands,
        "perform_unpin_all_general_forum_topic_messages",
        AsyncMock(),
    )
    message = _message(chat_id=42)

    await commands.cmd_unpin_all_general_forum_topic_messages(message)

    commands.perform_unpin_all_general_forum_topic_messages.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_unpin_all_general_forum_topic_messages_shows_usage_for_invalid_args(
    monkeypatch,
):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_unpin_all_general_forum_topic_messages",
        AsyncMock(),
    )
    message = _message(text="/unpinallgeneralforumtopicmessages", chat_id=42)

    await commands.cmd_unpin_all_general_forum_topic_messages(message)

    commands.perform_unpin_all_general_forum_topic_messages.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "unpinallgeneralforumtopicmessages usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_unpin_all_general_forum_topic_messages_calls_service(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_unpin_all_general_forum_topic_messages",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(
        commands,
        "format_unpin_all_general_forum_topic_messages_result",
        lambda **_: "ok",
    )
    message = _message()

    await commands.cmd_unpin_all_general_forum_topic_messages(message)

    commands.perform_unpin_all_general_forum_topic_messages.assert_awaited_once_with(
        message.bot,
        chat_id=-100123,
    )
    message.answer.assert_awaited_once_with("ok", parse_mode="HTML")


async def test_cmd_unpin_all_general_forum_topic_messages_reports_errors(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_unpin_all_general_forum_topic_messages",
        AsyncMock(side_effect=UnpinAllGeneralForumTopicMessagesError("boom")),
    )
    message = _message(chat_id=42)

    await commands.cmd_unpin_all_general_forum_topic_messages(message)

    args, _kwargs = message.answer.await_args
    assert "Could not unpin all General forum topic messages" in args[0]


def test_parse_unpin_all_general_forum_topic_messages_args():
    result = commands._parse_unpin_all_general_forum_topic_messages_args(
        "/unpinallgeneralforumtopicmessages -100123"
    )

    assert result == -100123


def test_parse_unpin_all_general_forum_topic_messages_args_rejects_invalid_chat_id():
    assert commands._parse_unpin_all_general_forum_topic_messages_args(
        "/unpinallgeneralforumtopicmessages nope"
    ) is None
