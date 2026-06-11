from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import delete_story
from bot.services.delete_story import DeleteStoryError, perform_delete_story

BUSINESS_CONNECTION_ID = "biz-123"
STORY_ID = 77


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
    monkeypatch.setattr(delete_story.httpx, "AsyncClient", lambda *a, **k: client)


async def test_perform_delete_story_posts_raw_payload(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    result = await perform_delete_story(
        _bot(),
        business_connection_id=f" {BUSINESS_CONNECTION_ID} ",
        story_id=STORY_ID,
    )

    assert result is True
    assert client.posted["url"] == "https://api.telegram.org/bot123:abc/deleteStory"
    assert client.posted["json"] == {
        "business_connection_id": BUSINESS_CONNECTION_ID,
        "story_id": STORY_ID,
    }


@pytest.mark.parametrize(
    "kwargs",
    [
        {"business_connection_id": "", "story_id": STORY_ID},
        {"business_connection_id": BUSINESS_CONNECTION_ID, "story_id": 0},
    ],
)
async def test_perform_delete_story_validates_before_request(monkeypatch, kwargs):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    with pytest.raises(DeleteStoryError):
        await perform_delete_story(_bot(), **kwargs)

    assert client.posted is None


async def test_perform_delete_story_raises_on_telegram_error(monkeypatch):
    client = _FakeClient(
        response=_FakeResponse(
            {
                "ok": False,
                "error_code": 400,
                "description": "Bad Request: story not found",
            }
        )
    )
    _install_client(monkeypatch, client)

    with pytest.raises(DeleteStoryError) as excinfo:
        await perform_delete_story(
            _bot(),
            business_connection_id=BUSINESS_CONNECTION_ID,
            story_id=STORY_ID,
        )

    assert excinfo.value.error_code == 400
    assert "story not found" in str(excinfo.value)


async def test_perform_delete_story_raises_on_transport_error(monkeypatch):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(DeleteStoryError):
        await perform_delete_story(
            _bot(),
            business_connection_id=BUSINESS_CONNECTION_ID,
            story_id=STORY_ID,
        )


def test_parse_delete_story_args_variants():
    assert commands._parse_delete_story_args(
        f"/deletestory {BUSINESS_CONNECTION_ID} {STORY_ID}"
    ) == (BUSINESS_CONNECTION_ID, STORY_ID)
    assert commands._parse_delete_story_args("/deletestory") is None
    assert (
        commands._parse_delete_story_args(f"/deletestory {BUSINESS_CONNECTION_ID} nope")
        is None
    )
    assert commands._parse_delete_story_args(f"/deletestory {BUSINESS_CONNECTION_ID} 0") is None


def _message(text: str = "/deletestory", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=_bot(),
        answer=AsyncMock(),
    )


async def test_cmd_delete_story_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands, "_is_admin_action_allowed", lambda chat_id: False)
    monkeypatch.setattr(commands, "perform_delete_story", AsyncMock())
    message = _message(
        text=f"/deletestory {BUSINESS_CONNECTION_ID} {STORY_ID}",
        chat_id=42,
    )

    await commands.cmd_delete_story(message)

    commands.perform_delete_story.assert_not_awaited()
    message.answer.assert_awaited_once_with("This command is restricted to admin chats.")


async def test_cmd_delete_story_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands, "_is_admin_action_allowed", lambda chat_id: True)
    monkeypatch.setattr(commands, "perform_delete_story", AsyncMock())
    message = _message(text="/deletestory", chat_id=42)

    await commands.cmd_delete_story(message)

    commands.perform_delete_story.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "deletestory usage" in args[0]
    assert kwargs == {"parse_mode": "HTML"}


async def test_cmd_delete_story_deletes_story(monkeypatch):
    monkeypatch.setattr(commands, "_is_admin_action_allowed", lambda chat_id: True)
    monkeypatch.setattr(commands, "perform_delete_story", AsyncMock(return_value=True))
    message = _message(
        text=f"/deletestory {BUSINESS_CONNECTION_ID} {STORY_ID}",
        chat_id=42,
    )

    await commands.cmd_delete_story(message)

    commands.perform_delete_story.assert_awaited_once_with(
        message.bot,
        business_connection_id=BUSINESS_CONNECTION_ID,
        story_id=STORY_ID,
    )
    message.answer.assert_awaited_once_with(f"Deleted story {STORY_ID}.")


async def test_cmd_delete_story_reports_service_error(monkeypatch):
    monkeypatch.setattr(commands, "_is_admin_action_allowed", lambda chat_id: True)
    monkeypatch.setattr(
        commands,
        "perform_delete_story",
        AsyncMock(side_effect=DeleteStoryError("story not found")),
    )
    message = _message(
        text=f"/deletestory {BUSINESS_CONNECTION_ID} {STORY_ID}",
        chat_id=42,
    )

    await commands.cmd_delete_story(message)

    message.answer.assert_awaited_once_with("Could not delete the story. Please try again later.")
