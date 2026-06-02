from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import chat as chat_handler
from bot.handlers import commands
from bot.services import send_message_draft
from bot.services.send_message_draft import (
    MESSAGE_DRAFT_TEXT_LIMIT,
    SendMessageDraftError,
    perform_send_message_draft,
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
        session=SimpleNamespace(
            api=SimpleNamespace(
                api_url=lambda token, method: (
                    f"https://api.telegram.org/bot{token}/{method}"
                )
            )
        ),
    )


def _install_client(monkeypatch, client):
    monkeypatch.setattr(
        send_message_draft.httpx, "AsyncClient", lambda *a, **k: client
    )


# --- raw helper -----------------------------------------------------------


async def test_perform_send_message_draft_posts_raw_payload(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    result = await perform_send_message_draft(
        _bot(),
        chat_id=42,
        draft_id=99,
        text="partial answer",
    )

    assert result is True
    assert client.posted["url"] == (
        "https://api.telegram.org/bot123:abc/sendMessageDraft"
    )
    assert client.posted["json"] == {
        "chat_id": 42,
        "draft_id": 99,
        "text": "partial answer",
    }


async def test_perform_send_message_draft_allows_empty_placeholder(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    result = await perform_send_message_draft(_bot(), chat_id=7, draft_id=1)

    assert result is True
    # An empty text is explicitly sent so Telegram shows the "Thinking…" placeholder.
    assert client.posted["json"] == {"chat_id": 7, "draft_id": 1, "text": ""}


async def test_perform_send_message_draft_forwards_optional_fields(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    await perform_send_message_draft(
        _bot(),
        chat_id=42,
        draft_id=5,
        text="hi",
        message_thread_id=11,
        parse_mode="HTML",
        entities=[{"type": "bold", "offset": 0, "length": 2}],
    )

    assert client.posted["json"] == {
        "chat_id": 42,
        "draft_id": 5,
        "text": "hi",
        "message_thread_id": 11,
        "parse_mode": "HTML",
        "entities": [{"type": "bold", "offset": 0, "length": 2}],
    }


async def test_perform_send_message_draft_rejects_zero_draft_id(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    with pytest.raises(SendMessageDraftError):
        await perform_send_message_draft(_bot(), chat_id=1, draft_id=0, text="x")

    # Validation happens before any Telegram request is made.
    assert client.posted is None


async def test_perform_send_message_draft_rejects_too_long_text(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    too_long = "x" * (MESSAGE_DRAFT_TEXT_LIMIT + 1)
    with pytest.raises(SendMessageDraftError):
        await perform_send_message_draft(
            _bot(), chat_id=1, draft_id=1, text=too_long
        )

    assert client.posted is None


async def test_perform_send_message_draft_raises_on_telegram_error(monkeypatch):
    client = _FakeClient(
        response=_FakeResponse(
            {
                "ok": False,
                "error_code": 400,
                "description": "Bad Request: chat not found",
            }
        )
    )
    _install_client(monkeypatch, client)

    with pytest.raises(SendMessageDraftError) as excinfo:
        await perform_send_message_draft(_bot(), chat_id=1, draft_id=1, text="x")

    assert excinfo.value.error_code == 400
    assert "chat not found" in str(excinfo.value)


async def test_perform_send_message_draft_raises_on_transport_error(monkeypatch):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(SendMessageDraftError):
        await perform_send_message_draft(_bot(), chat_id=1, draft_id=1, text="x")


# --- argument parsing -----------------------------------------------------


def test_parse_message_draft_args_variants():
    assert commands._parse_message_draft_args("/messagedraft") == ""
    assert commands._parse_message_draft_args("/messagedraft hello world") == (
        "hello world"
    )
    # Internal spaces are preserved, surrounding whitespace is trimmed.
    assert commands._parse_message_draft_args("/messagedraft   a  b  ") == "a  b"


# --- admin command --------------------------------------------------------


def _message(text: str = "/messagedraft", chat_id: int = 42, message_id: int = 7):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        message_id=message_id,
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_message_draft_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_message_draft", AsyncMock())
    message = _message(text="/messagedraft hi", chat_id=42)

    await commands.cmd_message_draft(message)

    commands.perform_send_message_draft.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_message_draft_sends_placeholder_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_send_message_draft", AsyncMock(return_value=True)
    )
    message = _message(text="/messagedraft", chat_id=42, message_id=7)

    await commands.cmd_message_draft(message)

    commands.perform_send_message_draft.assert_awaited_once_with(
        message.bot,
        chat_id=42,
        draft_id=7,
        text="",
    )
    args, _ = message.answer.await_args
    assert "Thinking" in args[0]


async def test_cmd_message_draft_sends_with_text(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_send_message_draft", AsyncMock(return_value=True)
    )
    message = _message(text="/messagedraft streaming preview", chat_id=42, message_id=7)

    await commands.cmd_message_draft(message)

    commands.perform_send_message_draft.assert_awaited_once_with(
        message.bot,
        chat_id=42,
        draft_id=7,
        text="streaming preview",
    )
    args, _ = message.answer.await_args
    assert args[0] == "Sent message draft."


async def test_cmd_message_draft_rejects_too_long_text(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_message_draft", AsyncMock())
    long_text = "x" * (commands.MESSAGE_DRAFT_TEXT_LIMIT + 1)
    message = _message(text=f"/messagedraft {long_text}", chat_id=42)

    await commands.cmd_message_draft(message)

    commands.perform_send_message_draft.assert_not_awaited()
    args, _ = message.answer.await_args
    assert "too long" in args[0]


async def test_cmd_message_draft_reports_send_errors(monkeypatch):
    error = SendMessageDraftError("Bad Request: chat not found", error_code=400)
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_send_message_draft", AsyncMock(side_effect=error)
    )
    message = _message(text="/messagedraft hi", chat_id=42)

    await commands.cmd_message_draft(message)

    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Could not send the message draft" in args[0]


# --- streaming integration ------------------------------------------------


class _FakeStreamClient:
    def __init__(self, chunks):
        self._chunks = chunks
        self.model = None

    async def send_message(self, *, messages, model, stream):
        self.model = model

        async def _gen():
            for chunk in self._chunks:
                yield chunk

        return _gen()


def _text_delta(text: str) -> dict:
    return {"type": "content_block_delta", "delta": {"type": "text_delta", "text": text}}


def _stream_message(chat_id: int = 42, message_id: int = 7):
    return SimpleNamespace(
        bot=object(),
        chat=SimpleNamespace(id=chat_id, type="private"),
        message_id=message_id,
        answer=AsyncMock(),
    )


def test_should_use_message_draft_only_for_opted_in_private(monkeypatch):
    private = SimpleNamespace(chat=SimpleNamespace(type="private"))
    group = SimpleNamespace(chat=SimpleNamespace(type="group"))

    monkeypatch.setattr(chat_handler.settings, "telegram_message_draft_enabled", True)
    assert chat_handler._should_use_message_draft(private) is True
    # Drafts only target private chats, never groups.
    assert chat_handler._should_use_message_draft(group) is False

    monkeypatch.setattr(chat_handler.settings, "telegram_message_draft_enabled", False)
    assert chat_handler._should_use_message_draft(private) is False


async def test_handle_streaming_with_draft_shows_placeholder_and_persists(monkeypatch):
    draft = AsyncMock(return_value=True)
    monkeypatch.setattr(chat_handler, "perform_send_message_draft", draft)
    client = _FakeStreamClient([_text_delta("Hello "), _text_delta("world")])
    message = _stream_message()

    reply = await chat_handler.handle_streaming_with_draft(message, client, [], "test-model")

    assert reply == "Hello world"
    # The caller-resolved model is forwarded to the proxy (issue #348).
    assert client.model == "test-model"
    # The first draft preview is the empty "Thinking…" placeholder with a non-zero id.
    first_call = draft.await_args_list[0]
    assert first_call.kwargs["text"] == ""
    assert first_call.kwargs["draft_id"] == 7
    # The finished answer is persisted with a real message, not left as a draft.
    persisted = [call.args[0] for call in message.answer.await_args_list]
    assert "Hello world" in "".join(persisted)


async def test_handle_streaming_with_draft_swallows_draft_errors(monkeypatch):
    draft = AsyncMock(side_effect=SendMessageDraftError("boom"))
    monkeypatch.setattr(chat_handler, "perform_send_message_draft", draft)
    client = _FakeStreamClient([_text_delta("hi")])
    message = _stream_message()

    # A failure to show the ephemeral preview must not break the response.
    reply = await chat_handler.handle_streaming_with_draft(message, client, [], "test-model")

    assert reply == "hi"
    persisted = [call.args[0] for call in message.answer.await_args_list]
    assert "hi" in "".join(persisted)


async def test_handle_streaming_with_draft_handles_empty_stream(monkeypatch):
    monkeypatch.setattr(
        chat_handler, "perform_send_message_draft", AsyncMock(return_value=True)
    )
    client = _FakeStreamClient([])
    message = _stream_message()

    reply = await chat_handler.handle_streaming_with_draft(message, client, [], "test-model")

    assert reply == "Claude returned no text response."


def _edit_stream_message(chat_id: int = 42, message_id: int = 7):
    sent_msg = SimpleNamespace(edit_text=AsyncMock())
    return SimpleNamespace(
        bot=object(),
        chat=SimpleNamespace(id=chat_id, type="private"),
        message_id=message_id,
        answer=AsyncMock(return_value=sent_msg),
    ), sent_msg


async def test_handle_streaming_persists_and_renders_text():
    client = _FakeStreamClient([_text_delta("Hello "), _text_delta("world")])
    message, sent_msg = _edit_stream_message()

    reply = await chat_handler.handle_streaming(message, client, [], "test-model")

    assert reply == "Hello world"
    # The caller-resolved model is forwarded to the proxy (issue #348).
    assert client.model == "test-model"
    final_edit = sent_msg.edit_text.await_args_list[-1]
    assert "Hello world" in final_edit.args[0]


async def test_handle_streaming_falls_back_on_empty_stream():
    client = _FakeStreamClient([])
    message, sent_msg = _edit_stream_message()

    reply = await chat_handler.handle_streaming(message, client, [], "test-model")

    # The empty stream must yield the fallback rather than leave the "…" placeholder.
    assert reply == "Claude returned no text response."
    final_edit = sent_msg.edit_text.await_args_list[-1]
    assert "Claude returned no text response." in final_edit.args[0]
    assert final_edit.args[0] != "…"
