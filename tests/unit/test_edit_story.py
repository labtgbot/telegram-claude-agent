import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import edit_story
from bot.services.edit_story import EditStoryError, perform_edit_story
from bot.services.post_story import POST_STORY_CAPTION_LIMIT

BUSINESS_CONNECTION_ID = "biz-123"
STORY_ID = 77
PHOTO_FILE_ID = "photo-file-id"


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
    monkeypatch.setattr(edit_story.httpx, "AsyncClient", lambda *a, **k: client)


async def test_perform_edit_story_posts_raw_payload(monkeypatch):
    client = _FakeClient(
        response=_FakeResponse(
            {"ok": True, "result": {"id": STORY_ID, "chat": {"id": 42}}}
        )
    )
    _install_client(monkeypatch, client)

    result = await perform_edit_story(
        _bot(),
        business_connection_id=f" {BUSINESS_CONNECTION_ID} ",
        story_id=STORY_ID,
        content={"type": "photo", "photo": PHOTO_FILE_ID},
        caption="updated launch notes",
    )

    assert result == {"id": STORY_ID, "chat": {"id": 42}}
    assert client.posted["url"] == "https://api.telegram.org/bot123:abc/editStory"
    assert client.posted["json"] == {
        "business_connection_id": BUSINESS_CONNECTION_ID,
        "story_id": STORY_ID,
        "content": json.dumps({"type": "photo", "photo": PHOTO_FILE_ID}),
        "caption": "updated launch notes",
    }


async def test_perform_edit_story_omits_unset_optionals(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": {}}))
    _install_client(monkeypatch, client)

    await perform_edit_story(
        _bot(),
        business_connection_id=BUSINESS_CONNECTION_ID,
        story_id=STORY_ID,
        content={"type": "photo", "photo": PHOTO_FILE_ID},
    )

    assert client.posted["json"] == {
        "business_connection_id": BUSINESS_CONNECTION_ID,
        "story_id": STORY_ID,
        "content": json.dumps({"type": "photo", "photo": PHOTO_FILE_ID}),
    }


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "business_connection_id": "",
            "story_id": STORY_ID,
            "content": {"type": "photo"},
        },
        {
            "business_connection_id": BUSINESS_CONNECTION_ID,
            "story_id": 0,
            "content": {"type": "photo"},
        },
        {
            "business_connection_id": BUSINESS_CONNECTION_ID,
            "story_id": STORY_ID,
            "content": {},
        },
        {
            "business_connection_id": BUSINESS_CONNECTION_ID,
            "story_id": STORY_ID,
            "content": {"type": "photo", "photo": PHOTO_FILE_ID},
            "caption": "x" * (POST_STORY_CAPTION_LIMIT + 1),
        },
    ],
)
async def test_perform_edit_story_validates_before_request(monkeypatch, kwargs):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": {}}))
    _install_client(monkeypatch, client)

    with pytest.raises(EditStoryError):
        await perform_edit_story(_bot(), **kwargs)

    assert client.posted is None


async def test_perform_edit_story_raises_on_telegram_error(monkeypatch):
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

    with pytest.raises(EditStoryError) as excinfo:
        await perform_edit_story(
            _bot(),
            business_connection_id=BUSINESS_CONNECTION_ID,
            story_id=STORY_ID,
            content={"type": "photo", "photo": PHOTO_FILE_ID},
        )

    assert excinfo.value.error_code == 400
    assert "story not found" in str(excinfo.value)


async def test_perform_edit_story_raises_on_transport_error(monkeypatch):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(EditStoryError):
        await perform_edit_story(
            _bot(),
            business_connection_id=BUSINESS_CONNECTION_ID,
            story_id=STORY_ID,
            content={"type": "photo", "photo": PHOTO_FILE_ID},
        )


def test_parse_edit_story_args_variants():
    assert commands._parse_edit_story_args(
        f"/editstory {BUSINESS_CONNECTION_ID} {STORY_ID} {PHOTO_FILE_ID}"
    ) == (BUSINESS_CONNECTION_ID, STORY_ID, PHOTO_FILE_ID, None)
    assert commands._parse_edit_story_args(
        f"/editstory {BUSINESS_CONNECTION_ID} {STORY_ID} {PHOTO_FILE_ID} story caption"
    ) == (BUSINESS_CONNECTION_ID, STORY_ID, PHOTO_FILE_ID, "story caption")
    assert commands._parse_edit_story_args("/editstory") is None
    assert (
        commands._parse_edit_story_args(
            f"/editstory {BUSINESS_CONNECTION_ID} nope {PHOTO_FILE_ID}"
        )
        is None
    )


def _message(text: str = "/editstory", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_edit_story_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_edit_story", AsyncMock())
    message = _message(
        text=f"/editstory {BUSINESS_CONNECTION_ID} {STORY_ID} {PHOTO_FILE_ID}",
        chat_id=42,
    )

    await commands.cmd_edit_story(message)

    commands.perform_edit_story.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_edit_story_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_edit_story", AsyncMock())
    message = _message(text="/editstory", chat_id=42)

    await commands.cmd_edit_story(message)

    commands.perform_edit_story.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "editstory usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_edit_story_edits_photo_story(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_edit_story", AsyncMock(return_value={"id": STORY_ID})
    )
    message = _message(
        text=(
            f"/editstory {BUSINESS_CONNECTION_ID} {STORY_ID} "
            f"{PHOTO_FILE_ID} updated notes"
        ),
        chat_id=42,
    )

    await commands.cmd_edit_story(message)

    commands.perform_edit_story.assert_awaited_once_with(
        message.bot,
        business_connection_id=BUSINESS_CONNECTION_ID,
        story_id=STORY_ID,
        content={"type": "photo", "photo": PHOTO_FILE_ID},
        caption="updated notes",
    )
    message.answer.assert_awaited_once_with(f"Edited story {STORY_ID}.")
