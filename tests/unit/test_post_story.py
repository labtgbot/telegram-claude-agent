import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import post_story
from bot.services.post_story import (
    POST_STORY_ACTIVE_PERIODS,
    POST_STORY_CAPTION_LIMIT,
    PostStoryError,
    perform_post_story,
)

BUSINESS_CONNECTION_ID = "biz-123"
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
    monkeypatch.setattr(post_story.httpx, "AsyncClient", lambda *a, **k: client)


async def test_perform_post_story_posts_raw_payload(monkeypatch):
    client = _FakeClient(
        response=_FakeResponse(
            {"ok": True, "result": {"id": 77, "chat": {"id": 42}}}
        )
    )
    _install_client(monkeypatch, client)

    result = await perform_post_story(
        _bot(),
        business_connection_id=f" {BUSINESS_CONNECTION_ID} ",
        content={"type": "photo", "photo": PHOTO_FILE_ID},
        active_period=86400,
        caption="launch notes",
        post_to_chat_page=True,
        protect_content=True,
    )

    assert result == {"id": 77, "chat": {"id": 42}}
    assert client.posted["url"] == "https://api.telegram.org/bot123:abc/postStory"
    assert client.posted["json"] == {
        "business_connection_id": BUSINESS_CONNECTION_ID,
        "content": json.dumps({"type": "photo", "photo": PHOTO_FILE_ID}),
        "active_period": 86400,
        "caption": "launch notes",
        "post_to_chat_page": True,
        "protect_content": True,
    }


async def test_perform_post_story_omits_unset_optionals(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": {}}))
    _install_client(monkeypatch, client)

    await perform_post_story(
        _bot(),
        business_connection_id=BUSINESS_CONNECTION_ID,
        content={"type": "photo", "photo": PHOTO_FILE_ID},
        active_period=POST_STORY_ACTIVE_PERIODS[0],
    )

    assert client.posted["json"] == {
        "business_connection_id": BUSINESS_CONNECTION_ID,
        "content": json.dumps({"type": "photo", "photo": PHOTO_FILE_ID}),
        "active_period": POST_STORY_ACTIVE_PERIODS[0],
    }


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "business_connection_id": "",
            "content": {"type": "photo"},
            "active_period": 86400,
        },
        {
            "business_connection_id": BUSINESS_CONNECTION_ID,
            "content": {},
            "active_period": 86400,
        },
        {
            "business_connection_id": BUSINESS_CONNECTION_ID,
            "content": {"type": "photo", "photo": PHOTO_FILE_ID},
            "active_period": 3600,
        },
        {
            "business_connection_id": BUSINESS_CONNECTION_ID,
            "content": {"type": "photo", "photo": PHOTO_FILE_ID},
            "active_period": 86400,
            "caption": "x" * (POST_STORY_CAPTION_LIMIT + 1),
        },
    ],
)
async def test_perform_post_story_validates_before_request(monkeypatch, kwargs):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": {}}))
    _install_client(monkeypatch, client)

    with pytest.raises(PostStoryError):
        await perform_post_story(_bot(), **kwargs)

    assert client.posted is None


async def test_perform_post_story_raises_on_telegram_error(monkeypatch):
    client = _FakeClient(
        response=_FakeResponse(
            {
                "ok": False,
                "error_code": 400,
                "description": "Bad Request: BUSINESS_CONNECTION_INVALID",
            }
        )
    )
    _install_client(monkeypatch, client)

    with pytest.raises(PostStoryError) as excinfo:
        await perform_post_story(
            _bot(),
            business_connection_id=BUSINESS_CONNECTION_ID,
            content={"type": "photo", "photo": PHOTO_FILE_ID},
            active_period=86400,
        )

    assert excinfo.value.error_code == 400
    assert "BUSINESS_CONNECTION_INVALID" in str(excinfo.value)


async def test_perform_post_story_raises_on_transport_error(monkeypatch):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(PostStoryError):
        await perform_post_story(
            _bot(),
            business_connection_id=BUSINESS_CONNECTION_ID,
            content={"type": "photo", "photo": PHOTO_FILE_ID},
            active_period=86400,
        )


def test_parse_post_story_args_variants():
    assert commands._parse_post_story_args(
        f"/poststory {BUSINESS_CONNECTION_ID} 86400 {PHOTO_FILE_ID}"
    ) == (BUSINESS_CONNECTION_ID, 86400, PHOTO_FILE_ID, None)
    assert commands._parse_post_story_args(
        f"/poststory {BUSINESS_CONNECTION_ID} 172800 {PHOTO_FILE_ID} story caption"
    ) == (BUSINESS_CONNECTION_ID, 172800, PHOTO_FILE_ID, "story caption")
    assert commands._parse_post_story_args("/poststory") is None
    assert commands._parse_post_story_args(
        f"/poststory {BUSINESS_CONNECTION_ID} nope {PHOTO_FILE_ID}"
    ) is None


def _message(text: str = "/poststory", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_post_story_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_post_story", AsyncMock())
    message = _message(
        text=f"/poststory {BUSINESS_CONNECTION_ID} 86400 {PHOTO_FILE_ID}",
        chat_id=42,
    )

    await commands.cmd_post_story(message)

    commands.perform_post_story.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_post_story_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_post_story", AsyncMock())
    message = _message(text="/poststory", chat_id=42)

    await commands.cmd_post_story(message)

    commands.perform_post_story.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "poststory usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_post_story_rejects_invalid_active_period(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_post_story", AsyncMock())
    message = _message(
        text=f"/poststory {BUSINESS_CONNECTION_ID} 3600 {PHOTO_FILE_ID}",
        chat_id=42,
    )

    await commands.cmd_post_story(message)

    commands.perform_post_story.assert_not_awaited()
    args, _ = message.answer.await_args
    assert "Active period must be one of" in args[0]


async def test_cmd_post_story_posts_photo_story(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_post_story", AsyncMock(return_value={"id": 77})
    )
    message = _message(
        text=f"/poststory {BUSINESS_CONNECTION_ID} 86400 {PHOTO_FILE_ID} launch notes",
        chat_id=42,
    )

    await commands.cmd_post_story(message)

    commands.perform_post_story.assert_awaited_once_with(
        message.bot,
        business_connection_id=BUSINESS_CONNECTION_ID,
        content={"type": "photo", "photo": PHOTO_FILE_ID},
        active_period=86400,
        caption="launch notes",
    )
    message.answer.assert_awaited_once_with("Posted story 77.")
