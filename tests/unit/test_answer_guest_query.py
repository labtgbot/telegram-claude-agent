from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import chat as chat_handler
from bot.services import answer_guest_query
from bot.services.answer_guest_query import (
    ANSWER_GUEST_QUERY_TEXT_LIMIT,
    AnswerGuestQueryError,
    perform_answer_guest_query,
)


class _FakeResponse:
    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data


class _FakeClient:
    """Minimal async-context-manager stand-in for ``httpx.AsyncClient``."""

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
        username="ClaudeBot",
        session=SimpleNamespace(
            api=SimpleNamespace(
                api_url=lambda token, method: (
                    f"https://api.telegram.org/bot{token}/{method}"
                )
            )
        ),
        get_me=AsyncMock(),
    )


def _install_client(monkeypatch, client):
    monkeypatch.setattr(
        answer_guest_query.httpx, "AsyncClient", lambda *a, **k: client
    )


async def test_perform_answer_guest_query_posts_raw_payload(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    result = await perform_answer_guest_query(
        _bot(),
        guest_query_id="guest-query-1",
        text="answer",
    )

    assert result is True
    assert client.posted["url"] == (
        "https://api.telegram.org/bot123:abc/answerGuestQuery"
    )
    assert client.posted["json"] == {
        "guest_query_id": "guest-query-1",
        "text": "answer",
    }


async def test_perform_answer_guest_query_rejects_missing_guest_query_id(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    with pytest.raises(AnswerGuestQueryError):
        await perform_answer_guest_query(_bot(), guest_query_id="", text="answer")

    assert client.posted is None


async def test_perform_answer_guest_query_rejects_empty_text(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    with pytest.raises(AnswerGuestQueryError):
        await perform_answer_guest_query(_bot(), guest_query_id="guest-query-1", text="")

    assert client.posted is None


async def test_perform_answer_guest_query_rejects_too_long_text(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    too_long = "x" * (ANSWER_GUEST_QUERY_TEXT_LIMIT + 1)
    with pytest.raises(AnswerGuestQueryError):
        await perform_answer_guest_query(
            _bot(), guest_query_id="guest-query-1", text=too_long
        )

    assert client.posted is None


async def test_perform_answer_guest_query_raises_on_telegram_error(monkeypatch):
    client = _FakeClient(
        response=_FakeResponse(
            {
                "ok": False,
                "error_code": 400,
                "description": "Bad Request: query is too old",
            }
        )
    )
    _install_client(monkeypatch, client)

    with pytest.raises(AnswerGuestQueryError) as excinfo:
        await perform_answer_guest_query(
            _bot(), guest_query_id="guest-query-1", text="answer"
        )

    assert excinfo.value.error_code == 400
    assert "query is too old" in str(excinfo.value)


async def test_perform_answer_guest_query_raises_on_transport_error(monkeypatch):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(AnswerGuestQueryError):
        await perform_answer_guest_query(
            _bot(), guest_query_id="guest-query-1", text="answer"
        )


class _FakeClaudeClient:
    def __init__(self, *args, **kwargs):
        self.closed = False

    async def send_message(self, *, messages, model):
        return {"content": [{"type": "text", "text": "Guest answer"}]}

    async def close(self):
        self.closed = True


def _guest_message():
    return SimpleNamespace(
        from_user=SimpleNamespace(id=7),
        chat=SimpleNamespace(id=-100, type="supergroup"),
        bot=_bot(),
        text="@ClaudeBot question",
        caption=None,
        photo=None,
        voice=None,
        document=None,
        reply_to_message=None,
        guest_query_id="guest-query-1",
        answer=AsyncMock(),
    )


async def test_handle_chat_message_answers_guest_query(monkeypatch):
    monkeypatch.setattr(chat_handler.settings, "telegram_allowed_chat_ids", "")
    monkeypatch.setattr(chat_handler.settings, "telegram_guest_mode_enabled", True)
    monkeypatch.setattr(chat_handler.settings, "free_claude_streaming_enabled", False)
    monkeypatch.setattr(chat_handler, "ClaudeProxyClient", _FakeClaudeClient)
    answer_guest = AsyncMock(return_value=True)
    monkeypatch.setattr(chat_handler, "perform_answer_guest_query", answer_guest)
    message = _guest_message()

    await chat_handler.handle_chat_message(message)

    answer_guest.assert_awaited_once_with(
        message.bot,
        guest_query_id="guest-query-1",
        text="Guest answer",
    )
    message.answer.assert_not_awaited()
