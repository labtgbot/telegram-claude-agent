from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import edit_general_forum_topic
from bot.services.edit_general_forum_topic import (
    EditGeneralForumTopicError,
    GENERAL_FORUM_TOPIC_NAME_LIMIT,
    format_edit_general_forum_topic_result,
    perform_edit_general_forum_topic,
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
    text: str = "/editgeneralforumtopic -100123 General Support",
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
        edit_general_forum_topic.httpx,
        "AsyncClient",
        lambda *a, **k: client,
    )


async def test_perform_edit_general_forum_topic_posts_raw_payload(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    result = await perform_edit_general_forum_topic(
        _bot(),
        chat_id=-100123,
        name="General Support",
    )

    assert result is True
    assert client.posted == {
        "url": "https://api.telegram.org/bot123:abc/editGeneralForumTopic",
        "json": {
            "chat_id": -100123,
            "name": "General Support",
        },
    }


async def test_perform_edit_general_forum_topic_raises_on_telegram_error(
    monkeypatch,
):
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

    with pytest.raises(EditGeneralForumTopicError) as excinfo:
        await perform_edit_general_forum_topic(
            _bot(),
            chat_id=-100123,
            name="General Support",
        )

    assert excinfo.value.error_code == 400
    assert "TOPIC_NOT_MODIFIED" in str(excinfo.value)


async def test_perform_edit_general_forum_topic_raises_on_transport_error(
    monkeypatch,
):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(EditGeneralForumTopicError):
        await perform_edit_general_forum_topic(
            _bot(),
            chat_id=-100123,
            name="General Support",
        )


def test_format_edit_general_forum_topic_result_escapes_fields():
    text = format_edit_general_forum_topic_result(
        chat_id=-100123,
        name="General <&>",
    )

    assert "editGeneralForumTopic" in text
    assert "-100123" in text
    assert "General &lt;&amp;&gt;" in text
    assert "General forum topic updated" in text


async def test_cmd_edit_general_forum_topic_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_edit_general_forum_topic", AsyncMock())
    message = _message(chat_id=42)

    await commands.cmd_edit_general_forum_topic(message)

    commands.perform_edit_general_forum_topic.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_edit_general_forum_topic_shows_usage_for_invalid_args(
    monkeypatch,
):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_edit_general_forum_topic", AsyncMock())
    message = _message(text="/editgeneralforumtopic -100123", chat_id=42)

    await commands.cmd_edit_general_forum_topic(message)

    commands.perform_edit_general_forum_topic.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "editgeneralforumtopic usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_edit_general_forum_topic_calls_service(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_edit_general_forum_topic",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(
        commands,
        "format_edit_general_forum_topic_result",
        lambda **_: "ok",
    )
    message = _message(
        text="/editgeneralforumtopic -100123 General Support",
        chat_id=42,
    )

    await commands.cmd_edit_general_forum_topic(message)

    commands.perform_edit_general_forum_topic.assert_awaited_once_with(
        message.bot,
        chat_id=-100123,
        name="General Support",
    )
    message.answer.assert_awaited_once_with("ok", parse_mode="HTML")


async def test_cmd_edit_general_forum_topic_reports_errors(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_edit_general_forum_topic",
        AsyncMock(side_effect=EditGeneralForumTopicError("boom")),
    )
    message = _message(chat_id=42)

    await commands.cmd_edit_general_forum_topic(message)

    args, _kwargs = message.answer.await_args
    assert "Could not edit General forum topic" in args[0]


def test_parse_edit_general_forum_topic_args_preserves_spaces():
    result = commands._parse_edit_general_forum_topic_args(
        "/editgeneralforumtopic -100123 General Support"
    )

    assert result == (-100123, "General Support")


def test_parse_edit_general_forum_topic_args_rejects_long_name():
    result = commands._parse_edit_general_forum_topic_args(
        "/editgeneralforumtopic -100123 " + ("x" * (GENERAL_FORUM_TOPIC_NAME_LIMIT + 1))
    )

    assert result is None
