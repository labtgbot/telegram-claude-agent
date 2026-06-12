import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import (
    answer_chat_join_request_query,
    send_chat_join_request_web_app,
    send_rich_message,
    send_rich_message_draft,
)
from bot.services.answer_chat_join_request_query import (
    AnswerChatJoinRequestQueryError,
    perform_answer_chat_join_request_query,
)
from bot.services.send_chat_join_request_web_app import (
    SendChatJoinRequestWebAppError,
    perform_send_chat_join_request_web_app,
)
from bot.services.send_rich_message import (
    SendRichMessageError,
    perform_send_rich_message,
)
from bot.services.send_rich_message_draft import (
    SendRichMessageDraftError,
    perform_send_rich_message_draft,
)

RICH_MESSAGE = {"html": "<h1>Status</h1><p>All systems green.</p>"}


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


def _install_client(monkeypatch, module, client):
    monkeypatch.setattr(module.httpx, "AsyncClient", lambda *a, **k: client)


def _message(text: str, chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_perform_send_rich_message_posts_raw_payload(monkeypatch):
    client = _FakeClient(
        response=_FakeResponse({"ok": True, "result": {"message_id": 77}})
    )
    _install_client(monkeypatch, send_rich_message, client)

    result = await perform_send_rich_message(
        _bot(),
        chat_id=42,
        rich_message=RICH_MESSAGE,
        message_thread_id=5,
        protect_content=True,
    )

    assert result == {"message_id": 77}
    assert client.posted["url"] == (
        "https://api.telegram.org/bot123:abc/sendRichMessage"
    )
    assert client.posted["json"] == {
        "chat_id": 42,
        "rich_message": RICH_MESSAGE,
        "message_thread_id": 5,
        "protect_content": True,
    }


@pytest.mark.parametrize(
    "rich_message",
    [
        {},
        {"html": ""},
        {"markdown": ""},
        {"html": "<p>x</p>", "markdown": "**x**"},
    ],
)
async def test_perform_send_rich_message_rejects_invalid_input(
    monkeypatch, rich_message
):
    client = _FakeClient(
        response=_FakeResponse({"ok": True, "result": {"message_id": 1}})
    )
    _install_client(monkeypatch, send_rich_message, client)

    with pytest.raises(SendRichMessageError):
        await perform_send_rich_message(_bot(), chat_id=42, rich_message=rich_message)

    assert client.posted is None


async def test_perform_send_rich_message_raises_on_transport_error(monkeypatch):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, send_rich_message, client)

    with pytest.raises(SendRichMessageError):
        await perform_send_rich_message(
            _bot(),
            chat_id=42,
            rich_message=RICH_MESSAGE,
        )


async def test_perform_send_rich_message_draft_posts_raw_payload(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, send_rich_message_draft, client)

    result = await perform_send_rich_message_draft(
        _bot(),
        chat_id=42,
        draft_id=123,
        rich_message=RICH_MESSAGE,
        message_thread_id=9,
    )

    assert result is True
    assert client.posted["url"] == (
        "https://api.telegram.org/bot123:abc/sendRichMessageDraft"
    )
    assert client.posted["json"] == {
        "chat_id": 42,
        "draft_id": 123,
        "rich_message": RICH_MESSAGE,
        "message_thread_id": 9,
    }


async def test_perform_send_rich_message_draft_rejects_zero_draft_id(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, send_rich_message_draft, client)

    with pytest.raises(SendRichMessageDraftError):
        await perform_send_rich_message_draft(
            _bot(),
            chat_id=42,
            draft_id=0,
            rich_message=RICH_MESSAGE,
        )

    assert client.posted is None


async def test_perform_answer_chat_join_request_query_posts_raw_payload(
    monkeypatch,
):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, answer_chat_join_request_query, client)

    result = await perform_answer_chat_join_request_query(
        _bot(),
        chat_join_request_query_id="join-query-1",
        result="approve",
    )

    assert result is True
    assert client.posted["url"] == (
        "https://api.telegram.org/bot123:abc/answerChatJoinRequestQuery"
    )
    assert client.posted["json"] == {
        "chat_join_request_query_id": "join-query-1",
        "result": "approve",
    }


async def test_perform_answer_chat_join_request_query_rejects_bad_result(
    monkeypatch,
):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, answer_chat_join_request_query, client)

    with pytest.raises(AnswerChatJoinRequestQueryError):
        await perform_answer_chat_join_request_query(
            _bot(),
            chat_join_request_query_id="join-query-1",
            result="maybe",
        )

    assert client.posted is None


async def test_perform_send_chat_join_request_web_app_posts_raw_payload(
    monkeypatch,
):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, send_chat_join_request_web_app, client)

    result = await perform_send_chat_join_request_web_app(
        _bot(),
        chat_join_request_query_id="join-query-1",
        web_app_url="https://example.com/captcha",
    )

    assert result is True
    assert client.posted["url"] == (
        "https://api.telegram.org/bot123:abc/sendChatJoinRequestWebApp"
    )
    assert client.posted["json"] == {
        "chat_join_request_query_id": "join-query-1",
        "web_app_url": "https://example.com/captcha",
    }


async def test_perform_send_chat_join_request_web_app_rejects_bad_url(
    monkeypatch,
):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, send_chat_join_request_web_app, client)

    with pytest.raises(SendChatJoinRequestWebAppError):
        await perform_send_chat_join_request_web_app(
            _bot(),
            chat_join_request_query_id="join-query-1",
            web_app_url="ftp://example.com/captcha",
        )

    assert client.posted is None


def test_parse_rich_message_args():
    assert commands._parse_rich_message_args(
        f"/richmessage {json.dumps(RICH_MESSAGE)}"
    ) == RICH_MESSAGE
    assert commands._parse_rich_message_args("/richmessage") is None
    assert commands._parse_rich_message_args("/richmessage []") is None


async def test_cmd_send_rich_message_calls_service(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_send_rich_message",
        AsyncMock(return_value={"message_id": 77}),
    )
    message = _message(text=f"/richmessage {json.dumps(RICH_MESSAGE)}")

    await commands.cmd_send_rich_message(message)

    commands.perform_send_rich_message.assert_awaited_once_with(
        message.bot,
        chat_id=42,
        rich_message=RICH_MESSAGE,
    )
    message.answer.assert_awaited_once_with("Sent rich message 77.")


async def test_cmd_send_rich_message_draft_calls_service(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_send_rich_message_draft",
        AsyncMock(return_value=True),
    )
    message = _message(text=f"/richmessagedraft 123 {json.dumps(RICH_MESSAGE)}")

    await commands.cmd_send_rich_message_draft(message)

    commands.perform_send_rich_message_draft.assert_awaited_once_with(
        message.bot,
        chat_id=42,
        draft_id=123,
        rich_message=RICH_MESSAGE,
    )
    message.answer.assert_awaited_once_with("Streamed rich message draft 123.")


async def test_cmd_answer_chat_join_request_query_calls_service(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_answer_chat_join_request_query",
        AsyncMock(return_value=True),
    )
    message = _message(text="/answerjoinrequestquery join-query-1 approve")

    await commands.cmd_answer_chat_join_request_query(message)

    commands.perform_answer_chat_join_request_query.assert_awaited_once_with(
        message.bot,
        chat_join_request_query_id="join-query-1",
        result="approve",
    )
    message.answer.assert_awaited_once_with(
        "Answered chat join request query with approve."
    )


async def test_cmd_send_chat_join_request_web_app_calls_service(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_send_chat_join_request_web_app",
        AsyncMock(return_value=True),
    )
    message = _message(
        text="/joinrequestwebapp join-query-1 https://example.com/captcha"
    )

    await commands.cmd_send_chat_join_request_web_app(message)

    commands.perform_send_chat_join_request_web_app.assert_awaited_once_with(
        message.bot,
        chat_join_request_query_id="join-query-1",
        web_app_url="https://example.com/captcha",
    )
    message.answer.assert_awaited_once_with("Sent chat join request Mini App.")
