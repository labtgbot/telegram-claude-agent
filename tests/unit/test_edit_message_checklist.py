import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import edit_message_checklist
from bot.services.edit_message_checklist import (
    EditMessageChecklistError,
    perform_edit_message_checklist,
)

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


def _message(text: str = "/editchecklist", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


def _install_client(monkeypatch, client):
    monkeypatch.setattr(
        edit_message_checklist.httpx, "AsyncClient", lambda *a, **k: client
    )


async def test_perform_edit_message_checklist_posts_raw_payload(monkeypatch):
    client = _FakeClient(
        response=_FakeResponse({"ok": True, "result": {"message_id": 777}})
    )
    _install_client(monkeypatch, client)

    result = await perform_edit_message_checklist(
        _bot(),
        business_connection_id=f" {BUSINESS_CONNECTION_ID} ",
        chat_id=-100123,
        message_id=777,
        checklist=CHECKLIST,
        reply_markup={"inline_keyboard": []},
    )

    assert result == {"message_id": 777}
    assert client.posted["url"] == (
        "https://api.telegram.org/bot123:abc/editMessageChecklist"
    )
    assert client.posted["json"] == {
        "business_connection_id": BUSINESS_CONNECTION_ID,
        "chat_id": -100123,
        "message_id": 777,
        "checklist": json.dumps(CHECKLIST),
        "reply_markup": json.dumps({"inline_keyboard": []}),
    }
    assert json.loads(client.posted["json"]["checklist"]) == CHECKLIST


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "business_connection_id": "",
            "chat_id": 42,
            "message_id": 777,
            "checklist": CHECKLIST,
        },
        {
            "business_connection_id": BUSINESS_CONNECTION_ID,
            "chat_id": 42,
            "message_id": 0,
            "checklist": CHECKLIST,
        },
        {
            "business_connection_id": BUSINESS_CONNECTION_ID,
            "chat_id": 42,
            "message_id": 777,
            "checklist": {},
        },
    ],
)
async def test_perform_edit_message_checklist_validates_before_request(
    monkeypatch, kwargs
):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": {}}))
    _install_client(monkeypatch, client)

    with pytest.raises(EditMessageChecklistError):
        await perform_edit_message_checklist(_bot(), **kwargs)

    assert client.posted is None


async def test_perform_edit_message_checklist_raises_on_telegram_error(monkeypatch):
    client = _FakeClient(
        response=_FakeResponse(
            {
                "ok": False,
                "error_code": 400,
                "description": "Bad Request: message can't be edited",
            }
        )
    )
    _install_client(monkeypatch, client)

    with pytest.raises(EditMessageChecklistError) as excinfo:
        await perform_edit_message_checklist(
            _bot(),
            business_connection_id=BUSINESS_CONNECTION_ID,
            chat_id=42,
            message_id=777,
            checklist=CHECKLIST,
        )

    assert excinfo.value.error_code == 400
    assert "can't be edited" in str(excinfo.value)


async def test_perform_edit_message_checklist_raises_on_transport_error(monkeypatch):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(EditMessageChecklistError):
        await perform_edit_message_checklist(
            _bot(),
            business_connection_id=BUSINESS_CONNECTION_ID,
            chat_id=42,
            message_id=777,
            checklist=CHECKLIST,
        )


def test_parse_edit_checklist_args_variants():
    assert commands._parse_edit_checklist_args(
        f"/editchecklist {BUSINESS_CONNECTION_ID} -100123 777 Launch | Write tests | Ship it"
    ) == (
        BUSINESS_CONNECTION_ID,
        -100123,
        777,
        "Launch",
        ["Write tests", "Ship it"],
    )
    assert commands._parse_edit_checklist_args(
        f"/editchecklist {BUSINESS_CONNECTION_ID} 42 1 Title | Only task"
    ) == (BUSINESS_CONNECTION_ID, 42, 1, "Title", ["Only task"])
    assert commands._parse_edit_checklist_args("/editchecklist") is None
    assert commands._parse_edit_checklist_args(
        f"/editchecklist {BUSINESS_CONNECTION_ID} chat 1 Title | task"
    ) is None
    assert commands._parse_edit_checklist_args(
        f"/editchecklist {BUSINESS_CONNECTION_ID} 42 0 Title | task"
    ) is None
    assert commands._parse_edit_checklist_args(
        f"/editchecklist {BUSINESS_CONNECTION_ID} 42 1 Title"
    ) is None
    assert commands._parse_edit_checklist_args(
        f"/editchecklist {BUSINESS_CONNECTION_ID} 42 1 Title | "
    ) is None


async def test_cmd_edit_checklist_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_edit_message_checklist", AsyncMock())
    message = _message(
        text=f"/editchecklist {BUSINESS_CONNECTION_ID} 42 777 Title | task",
        chat_id=42,
    )

    await commands.cmd_edit_message_checklist(message)

    commands.perform_edit_message_checklist.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_edit_checklist_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_edit_message_checklist", AsyncMock())
    message = _message(text="/editchecklist", chat_id=42)

    await commands.cmd_edit_message_checklist(message)

    commands.perform_edit_message_checklist.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "editchecklist usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_edit_checklist_edits_with_sequential_task_ids(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_edit_message_checklist",
        AsyncMock(return_value={"message_id": 777}),
    )
    message = _message(
        text=(
            f"/editchecklist {BUSINESS_CONNECTION_ID} -100123 777 "
            "Launch | Write tests | Ship it"
        ),
        chat_id=42,
    )

    await commands.cmd_edit_message_checklist(message)

    commands.perform_edit_message_checklist.assert_awaited_once_with(
        message.bot,
        business_connection_id=BUSINESS_CONNECTION_ID,
        chat_id=-100123,
        message_id=777,
        checklist={
            "title": "Launch",
            "tasks": [
                {"id": 1, "text": "Write tests"},
                {"id": 2, "text": "Ship it"},
            ],
        },
    )
    args, _ = message.answer.await_args
    assert args[0] == "Edited checklist message 777 with 2 tasks."


async def test_cmd_edit_checklist_reports_edit_errors(monkeypatch):
    error = EditMessageChecklistError(
        "Bad Request: message can't be edited", error_code=400
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_edit_message_checklist", AsyncMock(side_effect=error)
    )
    message = _message(
        text=f"/editchecklist {BUSINESS_CONNECTION_ID} 42 777 Title | task",
        chat_id=42,
    )

    await commands.cmd_edit_message_checklist(message)

    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Could not edit the checklist" in args[0]
