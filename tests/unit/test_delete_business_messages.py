from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import delete_business_messages
from bot.services.delete_business_messages import (
    DeleteBusinessMessagesError,
    perform_delete_business_messages,
)


BUSINESS_CONNECTION_ID = "bizconn-123"
MESSAGE_IDS = [456, 457]


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
        delete_business_messages.httpx, "AsyncClient", lambda *a, **k: client
    )


async def test_perform_delete_business_messages_posts_raw_payload(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    result = await perform_delete_business_messages(
        _bot(),
        business_connection_id=BUSINESS_CONNECTION_ID,
        message_ids=MESSAGE_IDS,
    )

    assert result is True
    assert client.posted["url"] == (
        "https://api.telegram.org/bot123:abc/deleteBusinessMessages"
    )
    assert client.posted["json"] == {
        "business_connection_id": BUSINESS_CONNECTION_ID,
        "message_ids": MESSAGE_IDS,
    }


async def test_perform_delete_business_messages_rejects_invalid_args(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    invalid_cases = [
        {"business_connection_id": "", "message_ids": MESSAGE_IDS},
        {"business_connection_id": BUSINESS_CONNECTION_ID, "message_ids": []},
        {"business_connection_id": BUSINESS_CONNECTION_ID, "message_ids": [0]},
        {
            "business_connection_id": BUSINESS_CONNECTION_ID,
            "message_ids": list(range(1, 102)),
        },
    ]
    for kwargs in invalid_cases:
        with pytest.raises(DeleteBusinessMessagesError):
            await perform_delete_business_messages(_bot(), **kwargs)

    assert client.posted is None


async def test_perform_delete_business_messages_raises_on_telegram_error(monkeypatch):
    client = _FakeClient(
        response=_FakeResponse(
            {
                "ok": False,
                "error_code": 400,
                "description": "Bad Request: message ids are invalid",
            }
        )
    )
    _install_client(monkeypatch, client)

    with pytest.raises(DeleteBusinessMessagesError) as excinfo:
        await perform_delete_business_messages(
            _bot(),
            business_connection_id=BUSINESS_CONNECTION_ID,
            message_ids=MESSAGE_IDS,
        )

    assert excinfo.value.error_code == 400
    assert "message ids are invalid" in str(excinfo.value)


async def test_perform_delete_business_messages_raises_on_transport_error(monkeypatch):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(DeleteBusinessMessagesError):
        await perform_delete_business_messages(
            _bot(),
            business_connection_id=BUSINESS_CONNECTION_ID,
            message_ids=MESSAGE_IDS,
        )


def test_parse_delete_business_messages_args():
    assert commands._parse_delete_business_messages_args(
        f"/deletebusinessmessages {BUSINESS_CONNECTION_ID} 456 457 confirm"
    ) == (BUSINESS_CONNECTION_ID, MESSAGE_IDS, True)
    assert commands._parse_delete_business_messages_args(
        f"/deletebusinessmessages {BUSINESS_CONNECTION_ID} 456,457 confirm"
    ) == (BUSINESS_CONNECTION_ID, MESSAGE_IDS, True)
    assert commands._parse_delete_business_messages_args(
        f"/deletebusinessmessages {BUSINESS_CONNECTION_ID} 456 457"
    ) == (BUSINESS_CONNECTION_ID, MESSAGE_IDS, False)
    assert commands._parse_delete_business_messages_args("/deletebusinessmessages") is None
    assert (
        commands._parse_delete_business_messages_args(
            f"/deletebusinessmessages {BUSINESS_CONNECTION_ID} not-int confirm"
        )
        is None
    )
    assert (
        commands._parse_delete_business_messages_args(
            f"/deletebusinessmessages {BUSINESS_CONNECTION_ID} 0 confirm"
        )
        is None
    )


def _message(text: str = "/deletebusinessmessages", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_delete_business_messages_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_delete_business_messages", AsyncMock())
    message = _message(
        text=f"/deletebusinessmessages {BUSINESS_CONNECTION_ID} 456 confirm",
        chat_id=42,
    )

    await commands.cmd_delete_business_messages(message)

    commands.perform_delete_business_messages.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_delete_business_messages_requires_confirmation(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_delete_business_messages", AsyncMock())
    message = _message(
        text=f"/deletebusinessmessages {BUSINESS_CONNECTION_ID} 456",
        chat_id=42,
    )

    await commands.cmd_delete_business_messages(message)

    commands.perform_delete_business_messages.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "confirmation required" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_delete_business_messages_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_delete_business_messages", AsyncMock())
    message = _message(text="/deletebusinessmessages", chat_id=42)

    await commands.cmd_delete_business_messages(message)

    commands.perform_delete_business_messages.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "deletebusinessmessages usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_delete_business_messages_deletes_messages(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_delete_business_messages",
        AsyncMock(return_value=True),
    )
    message = _message(
        text=f"/deletebusinessmessages {BUSINESS_CONNECTION_ID} 456,457 confirm",
        chat_id=42,
    )

    await commands.cmd_delete_business_messages(message)

    commands.perform_delete_business_messages.assert_awaited_once_with(
        message.bot,
        business_connection_id=BUSINESS_CONNECTION_ID,
        message_ids=MESSAGE_IDS,
    )
    message.answer.assert_awaited_once_with(
        f"Deleted 2 business messages for {BUSINESS_CONNECTION_ID}."
    )


async def test_cmd_delete_business_messages_reports_errors(monkeypatch):
    error = DeleteBusinessMessagesError(
        "Bad Request: message ids are invalid",
        error_code=400,
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_delete_business_messages", AsyncMock(side_effect=error)
    )
    message = _message(
        text=f"/deletebusinessmessages {BUSINESS_CONNECTION_ID} 456 confirm",
        chat_id=42,
    )

    await commands.cmd_delete_business_messages(message)

    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Could not delete the business messages" in args[0]
