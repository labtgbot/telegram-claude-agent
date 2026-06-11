from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import delete_all_message_reactions
from bot.services.delete_all_message_reactions import (
    DeleteAllMessageReactionsError,
    format_delete_all_message_reactions_result,
    perform_delete_all_message_reactions,
)


CHAT_ID = -100123
MESSAGE_ID = 55


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


def _install_client(monkeypatch, client):
    monkeypatch.setattr(
        delete_all_message_reactions.httpx,
        "AsyncClient",
        lambda *a, **k: client,
    )


async def test_perform_delete_all_message_reactions_posts_raw_payload(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    result = await perform_delete_all_message_reactions(
        _bot(),
        chat_id=CHAT_ID,
        message_id=MESSAGE_ID,
    )

    assert result is True
    assert client.posted["url"] == (
        "https://api.telegram.org/bot123:abc/deleteAllMessageReactions"
    )
    assert client.posted["json"] == {
        "chat_id": CHAT_ID,
        "message_id": MESSAGE_ID,
    }


async def test_perform_delete_all_message_reactions_rejects_invalid_message_id(
    monkeypatch,
):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    with pytest.raises(DeleteAllMessageReactionsError):
        await perform_delete_all_message_reactions(
            _bot(),
            chat_id=CHAT_ID,
            message_id=0,
        )

    assert client.posted is None


async def test_perform_delete_all_message_reactions_raises_on_telegram_error(
    monkeypatch,
):
    client = _FakeClient(
        response=_FakeResponse(
            {
                "ok": False,
                "error_code": 400,
                "description": "Bad Request: message not found",
            }
        )
    )
    _install_client(monkeypatch, client)

    with pytest.raises(DeleteAllMessageReactionsError) as excinfo:
        await perform_delete_all_message_reactions(
            _bot(),
            chat_id=CHAT_ID,
            message_id=MESSAGE_ID,
        )

    assert excinfo.value.error_code == 400
    assert "message not found" in str(excinfo.value)


async def test_perform_delete_all_message_reactions_raises_on_transport_error(
    monkeypatch,
):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(DeleteAllMessageReactionsError):
        await perform_delete_all_message_reactions(
            _bot(),
            chat_id=CHAT_ID,
            message_id=MESSAGE_ID,
        )


def test_format_delete_all_message_reactions_result():
    text = format_delete_all_message_reactions_result(
        chat_id=CHAT_ID,
        message_id=MESSAGE_ID,
    )

    assert "deleteAllMessageReactions" in text
    assert str(CHAT_ID) in text
    assert str(MESSAGE_ID) in text
    assert "all reactions deleted" in text


def test_parse_delete_all_message_reactions_args():
    assert commands._parse_delete_all_message_reactions_args(
        "/deleteallreactions -100123 55"
    ) == (CHAT_ID, MESSAGE_ID)
    assert commands._parse_delete_all_message_reactions_args("/deleteallreactions") is None
    assert (
        commands._parse_delete_all_message_reactions_args(
            "/deleteallreactions -100123 not-int"
        )
        is None
    )
    assert commands._parse_delete_all_message_reactions_args(
        "/deleteallreactions -100123 0"
    ) is None


def _message(text: str = "/deleteallreactions", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_delete_all_message_reactions_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_delete_all_message_reactions", AsyncMock())
    message = _message(text="/deleteallreactions -100123 55", chat_id=42)

    await commands.cmd_delete_all_message_reactions(message)

    commands.perform_delete_all_message_reactions.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_delete_all_message_reactions_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_delete_all_message_reactions", AsyncMock())
    message = _message(text="/deleteallreactions", chat_id=42)

    await commands.cmd_delete_all_message_reactions(message)

    commands.perform_delete_all_message_reactions.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "deleteallreactions usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_delete_all_message_reactions_calls_service(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_delete_all_message_reactions",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(
        commands,
        "format_delete_all_message_reactions_result",
        lambda **_: "ok",
    )
    message = _message(text="/deleteallreactions -100123 55", chat_id=42)

    await commands.cmd_delete_all_message_reactions(message)

    commands.perform_delete_all_message_reactions.assert_awaited_once_with(
        message.bot,
        chat_id=CHAT_ID,
        message_id=MESSAGE_ID,
    )
    message.answer.assert_awaited_once_with("ok", parse_mode="HTML")


async def test_cmd_delete_all_message_reactions_reports_telegram_errors(monkeypatch):
    error = DeleteAllMessageReactionsError("Bad Request: message not found")
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_delete_all_message_reactions",
        AsyncMock(side_effect=error),
    )
    message = _message(text="/deleteallreactions -100123 55", chat_id=42)

    await commands.cmd_delete_all_message_reactions(message)

    args, _ = message.answer.await_args
    assert "Could not delete all message reactions" in args[0]
    assert "message not found" not in args[0]
    assert "Please try again later" in args[0]
