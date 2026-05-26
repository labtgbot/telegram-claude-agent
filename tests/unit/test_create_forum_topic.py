from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import create_forum_topic
from bot.services.create_forum_topic import (
    CreateForumTopicError,
    FORUM_TOPIC_NAME_LIMIT,
    format_create_forum_topic_result,
    perform_create_forum_topic,
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


def _message(text: str = "/createforumtopic -100123 Support", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


def _install_client(monkeypatch, client):
    monkeypatch.setattr(
        create_forum_topic.httpx,
        "AsyncClient",
        lambda *a, **k: client,
    )


def _topic_payload(**overrides):
    payload = {
        "message_thread_id": 77,
        "name": "Support",
        "icon_color": 7322096,
    }
    payload.update(overrides)
    return payload


async def test_perform_create_forum_topic_posts_raw_payload(monkeypatch):
    client = _FakeClient(
        response=_FakeResponse({"ok": True, "result": _topic_payload()})
    )
    _install_client(monkeypatch, client)

    topic = await perform_create_forum_topic(
        _bot(),
        chat_id=-100123,
        name="Support",
        icon_color=7322096,
        icon_custom_emoji_id="emoji-id",
    )

    assert topic.message_thread_id == 77
    assert client.posted == {
        "url": "https://api.telegram.org/bot123:abc/createForumTopic",
        "json": {
            "chat_id": -100123,
            "name": "Support",
            "icon_color": 7322096,
            "icon_custom_emoji_id": "emoji-id",
        },
    }


async def test_perform_create_forum_topic_omits_optional_fields(monkeypatch):
    client = _FakeClient(
        response=_FakeResponse({"ok": True, "result": _topic_payload()})
    )
    _install_client(monkeypatch, client)

    await perform_create_forum_topic(
        _bot(),
        chat_id=-100123,
        name="Support",
    )

    assert client.posted["json"] == {
        "chat_id": -100123,
        "name": "Support",
    }


async def test_perform_create_forum_topic_raises_on_telegram_error(monkeypatch):
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

    with pytest.raises(CreateForumTopicError) as excinfo:
        await perform_create_forum_topic(
            _bot(),
            chat_id=-100123,
            name="Support",
        )

    assert excinfo.value.error_code == 400
    assert "not enough rights" in str(excinfo.value)


async def test_perform_create_forum_topic_raises_on_transport_error(monkeypatch):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(CreateForumTopicError):
        await perform_create_forum_topic(
            _bot(),
            chat_id=-100123,
            name="Support",
        )


def test_format_create_forum_topic_result_escapes_fields():
    topic = SimpleNamespace(message_thread_id=77)

    text = format_create_forum_topic_result(
        chat_id=-100123,
        name="Support <&>",
        topic=topic,
        icon_color=7322096,
        icon_custom_emoji_id="emoji<&>",
    )

    assert "createForumTopic" in text
    assert "-100123" in text
    assert "77" in text
    assert "Support &lt;&amp;&gt;" in text
    assert "7322096" in text
    assert "emoji&lt;&amp;&gt;" in text


async def test_cmd_create_forum_topic_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_create_forum_topic", AsyncMock())
    message = _message(chat_id=42)

    await commands.cmd_create_forum_topic(message)

    commands.perform_create_forum_topic.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_create_forum_topic_shows_usage_for_invalid_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_create_forum_topic", AsyncMock())
    message = _message(text="/createforumtopic -100123", chat_id=42)

    await commands.cmd_create_forum_topic(message)

    commands.perform_create_forum_topic.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "createforumtopic usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_create_forum_topic_rejects_long_name(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_create_forum_topic", AsyncMock())
    message = _message(
        text=f"/createforumtopic -100123 {'x' * (FORUM_TOPIC_NAME_LIMIT + 1)}",
        chat_id=42,
    )

    await commands.cmd_create_forum_topic(message)

    commands.perform_create_forum_topic.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "createforumtopic usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_create_forum_topic_calls_service(monkeypatch):
    topic = SimpleNamespace(message_thread_id=77)
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_create_forum_topic",
        AsyncMock(return_value=topic),
    )
    monkeypatch.setattr(commands, "format_create_forum_topic_result", lambda **_: "ok")
    message = _message(
        text=(
            "/createforumtopic -100123 Support "
            "icon_color=7322096 icon_custom_emoji_id=emoji-id"
        ),
        chat_id=42,
    )

    await commands.cmd_create_forum_topic(message)

    commands.perform_create_forum_topic.assert_awaited_once_with(
        message.bot,
        chat_id=-100123,
        name="Support",
        icon_color=7322096,
        icon_custom_emoji_id="emoji-id",
    )
    message.answer.assert_awaited_once_with("ok", parse_mode="HTML")


async def test_cmd_create_forum_topic_reports_errors(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_create_forum_topic",
        AsyncMock(side_effect=CreateForumTopicError("Bad Request")),
    )
    message = _message(chat_id=42)

    await commands.cmd_create_forum_topic(message)

    message.answer.assert_awaited_once_with("Could not create forum topic: Bad Request")
