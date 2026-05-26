from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import edit_forum_topic
from bot.services.edit_forum_topic import (
    EditForumTopicError,
    FORUM_TOPIC_NAME_LIMIT,
    format_edit_forum_topic_result,
    perform_edit_forum_topic,
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
    text: str = "/editforumtopic -100123 77 name=Support",
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
        edit_forum_topic.httpx,
        "AsyncClient",
        lambda *a, **k: client,
    )


async def test_perform_edit_forum_topic_posts_raw_payload(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    result = await perform_edit_forum_topic(
        _bot(),
        chat_id=-100123,
        message_thread_id=77,
        name="Support",
        icon_custom_emoji_id="emoji-id",
    )

    assert result is True
    assert client.posted == {
        "url": "https://api.telegram.org/bot123:abc/editForumTopic",
        "json": {
            "chat_id": -100123,
            "message_thread_id": 77,
            "name": "Support",
            "icon_custom_emoji_id": "emoji-id",
        },
    }


async def test_perform_edit_forum_topic_omits_optional_fields(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    await perform_edit_forum_topic(
        _bot(),
        chat_id=-100123,
        message_thread_id=77,
    )

    assert client.posted["json"] == {
        "chat_id": -100123,
        "message_thread_id": 77,
    }


async def test_perform_edit_forum_topic_raises_on_telegram_error(monkeypatch):
    client = _FakeClient(
        response=_FakeResponse(
            {
                "ok": False,
                "error_code": 400,
                "description": "Bad Request: TOPIC_NOT_MODIFIED",
            }
        )
    )
    _install_client(monkeypatch, client)

    with pytest.raises(EditForumTopicError) as excinfo:
        await perform_edit_forum_topic(
            _bot(),
            chat_id=-100123,
            message_thread_id=77,
            name="Support",
        )

    assert excinfo.value.error_code == 400
    assert "TOPIC_NOT_MODIFIED" in str(excinfo.value)


async def test_perform_edit_forum_topic_raises_on_transport_error(monkeypatch):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(EditForumTopicError):
        await perform_edit_forum_topic(
            _bot(),
            chat_id=-100123,
            message_thread_id=77,
            name="Support",
        )


def test_format_edit_forum_topic_result_escapes_fields():
    text = format_edit_forum_topic_result(
        chat_id=-100123,
        message_thread_id=77,
        name="Support <&>",
        icon_custom_emoji_id="emoji<&>",
    )

    assert "editForumTopic" in text
    assert "-100123" in text
    assert "77" in text
    assert "Support &lt;&amp;&gt;" in text
    assert "emoji&lt;&amp;&gt;" in text


async def test_cmd_edit_forum_topic_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_edit_forum_topic", AsyncMock())
    message = _message(chat_id=42)

    await commands.cmd_edit_forum_topic(message)

    commands.perform_edit_forum_topic.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_edit_forum_topic_shows_usage_for_invalid_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_edit_forum_topic", AsyncMock())
    message = _message(text="/editforumtopic -100123 77", chat_id=42)

    await commands.cmd_edit_forum_topic(message)

    commands.perform_edit_forum_topic.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "editforumtopic usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_edit_forum_topic_calls_service(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_edit_forum_topic",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(commands, "format_edit_forum_topic_result", lambda **_: "ok")
    message = _message(
        text="/editforumtopic -100123 77 name=Support icon_custom_emoji_id=emoji-id",
        chat_id=42,
    )

    await commands.cmd_edit_forum_topic(message)

    commands.perform_edit_forum_topic.assert_awaited_once_with(
        message.bot,
        chat_id=-100123,
        message_thread_id=77,
        name="Support",
        icon_custom_emoji_id="emoji-id",
    )
    message.answer.assert_awaited_once_with("ok", parse_mode="HTML")


async def test_cmd_edit_forum_topic_reports_errors(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_edit_forum_topic",
        AsyncMock(side_effect=EditForumTopicError("boom")),
    )
    message = _message(chat_id=42)

    await commands.cmd_edit_forum_topic(message)

    args, _kwargs = message.answer.await_args
    assert "Could not edit forum topic" in args[0]


def test_parse_edit_forum_topic_args_name_and_icon():
    result = commands._parse_edit_forum_topic_args(
        "/editforumtopic -100123 77 name=Support icon_custom_emoji_id=emoji-id"
    )

    assert result == (-100123, 77, "Support", "emoji-id")


def test_parse_edit_forum_topic_args_icon_only():
    result = commands._parse_edit_forum_topic_args(
        "/editforumtopic -100123 77 icon_custom_emoji_id=emoji-id"
    )

    assert result == (-100123, 77, None, "emoji-id")


def test_parse_edit_forum_topic_args_rejects_missing_edit_fields():
    assert commands._parse_edit_forum_topic_args("/editforumtopic -100123 77") is None


def test_parse_edit_forum_topic_args_rejects_invalid_thread_id():
    assert (
        commands._parse_edit_forum_topic_args(
            "/editforumtopic -100123 0 name=Support"
        )
        is None
    )


def test_parse_edit_forum_topic_args_rejects_too_long_name():
    text = "/editforumtopic -100123 77 name=" + "x" * (FORUM_TOPIC_NAME_LIMIT + 1)

    assert commands._parse_edit_forum_topic_args(text) is None
