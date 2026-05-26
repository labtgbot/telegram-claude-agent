import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import send_checklist
from bot.services.send_checklist import SendChecklistError, perform_send_checklist

BUSINESS_CONNECTION_ID = "bizconn-123"
CHECKLIST = {
    "title": "Launch checklist",
    "tasks": [
        {"id": 1, "text": "Write tests"},
        {"id": 2, "text": "Ship it"},
    ],
}


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
        send_checklist.httpx, "AsyncClient", lambda *a, **k: client
    )


async def test_perform_send_checklist_posts_raw_payload(monkeypatch):
    client = _FakeClient(
        response=_FakeResponse({"ok": True, "result": {"message_id": 777}})
    )
    _install_client(monkeypatch, client)

    result = await perform_send_checklist(
        _bot(),
        business_connection_id=BUSINESS_CONNECTION_ID,
        chat_id=42,
        checklist=CHECKLIST,
        protect_content=True,
    )

    assert result == {"message_id": 777}
    assert client.posted["url"] == (
        "https://api.telegram.org/bot123:abc/sendChecklist"
    )
    assert client.posted["json"] == {
        "business_connection_id": BUSINESS_CONNECTION_ID,
        "chat_id": 42,
        "checklist": json.dumps(CHECKLIST),
        "protect_content": True,
    }
    # The checklist object must be JSON-serialized into the request body.
    assert json.loads(client.posted["json"]["checklist"]) == CHECKLIST


async def test_perform_send_checklist_omits_unset_optionals(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": {}}))
    _install_client(monkeypatch, client)

    await perform_send_checklist(
        _bot(),
        business_connection_id=BUSINESS_CONNECTION_ID,
        chat_id=7,
        checklist=CHECKLIST,
    )

    assert client.posted["json"] == {
        "business_connection_id": BUSINESS_CONNECTION_ID,
        "chat_id": 7,
        "checklist": json.dumps(CHECKLIST),
    }


async def test_perform_send_checklist_raises_on_telegram_error(monkeypatch):
    client = _FakeClient(
        response=_FakeResponse(
            {
                "ok": False,
                "error_code": 400,
                "description": "Bad Request: business connection not found",
            }
        )
    )
    _install_client(monkeypatch, client)

    with pytest.raises(SendChecklistError) as excinfo:
        await perform_send_checklist(
            _bot(),
            business_connection_id=BUSINESS_CONNECTION_ID,
            chat_id=1,
            checklist=CHECKLIST,
        )

    assert excinfo.value.error_code == 400
    assert "business connection not found" in str(excinfo.value)


async def test_perform_send_checklist_raises_on_transport_error(monkeypatch):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(SendChecklistError):
        await perform_send_checklist(
            _bot(),
            business_connection_id=BUSINESS_CONNECTION_ID,
            chat_id=1,
            checklist=CHECKLIST,
        )


def test_parse_checklist_args_variants():
    assert commands._parse_checklist_args(
        f"/checklist {BUSINESS_CONNECTION_ID} Launch | Write tests | Ship it"
    ) == (BUSINESS_CONNECTION_ID, "Launch", ["Write tests", "Ship it"])
    # A single task is valid.
    assert commands._parse_checklist_args(
        f"/checklist {BUSINESS_CONNECTION_ID} Title | Only task"
    ) == (BUSINESS_CONNECTION_ID, "Title", ["Only task"])
    # Surrounding whitespace is trimmed, internal spaces kept.
    assert commands._parse_checklist_args(
        f"/checklist {BUSINESS_CONNECTION_ID} My title  |  do a thing  "
    ) == (BUSINESS_CONNECTION_ID, "My title", ["do a thing"])
    # Missing the task separator -> no tasks -> usage.
    assert commands._parse_checklist_args(
        f"/checklist {BUSINESS_CONNECTION_ID} Just a title"
    ) is None
    # Missing the title/tasks entirely -> usage.
    assert commands._parse_checklist_args(f"/checklist {BUSINESS_CONNECTION_ID}") is None
    assert commands._parse_checklist_args("/checklist") is None
    # An empty task segment -> usage.
    assert commands._parse_checklist_args(
        f"/checklist {BUSINESS_CONNECTION_ID} Title | first | | third"
    ) is None
    # An empty title segment -> usage.
    assert commands._parse_checklist_args(
        f"/checklist {BUSINESS_CONNECTION_ID}  | task"
    ) is None


def _message(text: str = "/checklist", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_checklist_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_checklist", AsyncMock())
    message = _message(
        text=f"/checklist {BUSINESS_CONNECTION_ID} Title | task", chat_id=42
    )

    await commands.cmd_checklist(message)

    commands.perform_send_checklist.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_checklist_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_checklist", AsyncMock())
    message = _message(text="/checklist", chat_id=42)

    await commands.cmd_checklist(message)

    commands.perform_send_checklist.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "checklist usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_checklist_rejects_too_long_title(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_checklist", AsyncMock())
    long_title = "x" * (commands.CHECKLIST_TITLE_MAX_LENGTH + 1)
    message = _message(
        text=f"/checklist {BUSINESS_CONNECTION_ID} {long_title} | task", chat_id=42
    )

    await commands.cmd_checklist(message)

    commands.perform_send_checklist.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Title is too long" in args[0]


async def test_cmd_checklist_rejects_too_many_tasks(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_checklist", AsyncMock())
    tasks = " | ".join(f"task {i}" for i in range(commands.CHECKLIST_MAX_TASKS + 1))
    message = _message(
        text=f"/checklist {BUSINESS_CONNECTION_ID} Title | {tasks}", chat_id=42
    )

    await commands.cmd_checklist(message)

    commands.perform_send_checklist.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "A checklist needs between" in args[0]


async def test_cmd_checklist_rejects_too_long_task(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_checklist", AsyncMock())
    long_task = "y" * (commands.CHECKLIST_TASK_MAX_LENGTH + 1)
    message = _message(
        text=f"/checklist {BUSINESS_CONNECTION_ID} Title | {long_task}", chat_id=42
    )

    await commands.cmd_checklist(message)

    commands.perform_send_checklist.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Task is too long" in args[0]


async def test_cmd_checklist_sends_with_sequential_task_ids(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_send_checklist", AsyncMock(return_value={})
    )
    message = _message(
        text=f"/checklist {BUSINESS_CONNECTION_ID} Launch | Write tests | Ship it",
        chat_id=42,
    )

    await commands.cmd_checklist(message)

    commands.perform_send_checklist.assert_awaited_once_with(
        message.bot,
        business_connection_id=BUSINESS_CONNECTION_ID,
        chat_id=42,
        checklist={
            "title": "Launch",
            "tasks": [
                {"id": 1, "text": "Write tests"},
                {"id": 2, "text": "Ship it"},
            ],
        },
    )
    args, _ = message.answer.await_args
    assert args[0] == "Sent checklist with 2 tasks."


async def test_cmd_checklist_reports_send_errors(monkeypatch):
    error = SendChecklistError(
        "Bad Request: business connection not found", error_code=400
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_send_checklist", AsyncMock(side_effect=error)
    )
    message = _message(
        text=f"/checklist {BUSINESS_CONNECTION_ID} Title | task", chat_id=42
    )

    await commands.cmd_checklist(message)

    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Could not send the checklist" in args[0]
