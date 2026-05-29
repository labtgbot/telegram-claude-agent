from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import repost_story
from bot.services.repost_story import (
    RepostStoryError,
    perform_repost_story,
)

BUSINESS_CONNECTION_ID = "biz-123"
FROM_CHAT_ID = 777000
FROM_STORY_ID = 42


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
    monkeypatch.setattr(repost_story.httpx, "AsyncClient", lambda *a, **k: client)


async def test_perform_repost_story_posts_raw_payload(monkeypatch):
    client = _FakeClient(
        response=_FakeResponse(
            {"ok": True, "result": {"id": 78, "chat": {"id": 43}}}
        )
    )
    _install_client(monkeypatch, client)

    result = await perform_repost_story(
        _bot(),
        business_connection_id=f" {BUSINESS_CONNECTION_ID} ",
        from_chat_id=FROM_CHAT_ID,
        from_story_id=FROM_STORY_ID,
        active_period=86400,
        post_to_chat_page=True,
        protect_content=True,
    )

    assert result == {"id": 78, "chat": {"id": 43}}
    assert client.posted["url"] == "https://api.telegram.org/bot123:abc/repostStory"
    assert client.posted["json"] == {
        "business_connection_id": BUSINESS_CONNECTION_ID,
        "from_chat_id": FROM_CHAT_ID,
        "from_story_id": FROM_STORY_ID,
        "active_period": 86400,
        "post_to_chat_page": True,
        "protect_content": True,
    }


async def test_perform_repost_story_omits_unset_optionals(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": {}}))
    _install_client(monkeypatch, client)

    await perform_repost_story(
        _bot(),
        business_connection_id=BUSINESS_CONNECTION_ID,
        from_chat_id=FROM_CHAT_ID,
        from_story_id=FROM_STORY_ID,
        active_period=21600,
    )

    assert client.posted["json"] == {
        "business_connection_id": BUSINESS_CONNECTION_ID,
        "from_chat_id": FROM_CHAT_ID,
        "from_story_id": FROM_STORY_ID,
        "active_period": 21600,
    }


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "business_connection_id": "",
            "from_chat_id": FROM_CHAT_ID,
            "from_story_id": FROM_STORY_ID,
            "active_period": 86400,
        },
        {
            "business_connection_id": BUSINESS_CONNECTION_ID,
            "from_chat_id": 0,
            "from_story_id": FROM_STORY_ID,
            "active_period": 86400,
        },
        {
            "business_connection_id": BUSINESS_CONNECTION_ID,
            "from_chat_id": FROM_CHAT_ID,
            "from_story_id": 0,
            "active_period": 86400,
        },
        {
            "business_connection_id": BUSINESS_CONNECTION_ID,
            "from_chat_id": FROM_CHAT_ID,
            "from_story_id": FROM_STORY_ID,
            "active_period": 3600,
        },
    ],
)
async def test_perform_repost_story_validates_before_request(monkeypatch, kwargs):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": {}}))
    _install_client(monkeypatch, client)

    with pytest.raises(RepostStoryError):
        await perform_repost_story(_bot(), **kwargs)

    assert client.posted is None


async def test_perform_repost_story_raises_on_telegram_error(monkeypatch):
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

    with pytest.raises(RepostStoryError) as excinfo:
        await perform_repost_story(
            _bot(),
            business_connection_id=BUSINESS_CONNECTION_ID,
            from_chat_id=FROM_CHAT_ID,
            from_story_id=FROM_STORY_ID,
            active_period=86400,
        )

    assert excinfo.value.error_code == 400
    assert "story not found" in str(excinfo.value)


async def test_perform_repost_story_raises_on_transport_error(monkeypatch):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(RepostStoryError):
        await perform_repost_story(
            _bot(),
            business_connection_id=BUSINESS_CONNECTION_ID,
            from_chat_id=FROM_CHAT_ID,
            from_story_id=FROM_STORY_ID,
            active_period=86400,
        )


def test_parse_repost_story_args_variants():
    assert commands._parse_repost_story_args(
        f"/repoststory {BUSINESS_CONNECTION_ID} {FROM_CHAT_ID} {FROM_STORY_ID} 86400"
    ) == (BUSINESS_CONNECTION_ID, FROM_CHAT_ID, FROM_STORY_ID, 86400)
    assert commands._parse_repost_story_args("/repoststory") is None
    assert (
        commands._parse_repost_story_args(
            f"/repoststory {BUSINESS_CONNECTION_ID} nope {FROM_STORY_ID} 86400"
        )
        is None
    )


def _message(text: str = "/repoststory", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_repost_story_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_repost_story", AsyncMock())
    message = _message(
        text=(
            f"/repoststory {BUSINESS_CONNECTION_ID} {FROM_CHAT_ID} "
            f"{FROM_STORY_ID} 86400"
        ),
        chat_id=42,
    )

    await commands.cmd_repost_story(message)

    commands.perform_repost_story.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_repost_story_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_repost_story", AsyncMock())
    message = _message(text="/repoststory", chat_id=42)

    await commands.cmd_repost_story(message)

    commands.perform_repost_story.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "repoststory usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_repost_story_rejects_invalid_active_period(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_repost_story", AsyncMock())
    message = _message(
        text=(
            f"/repoststory {BUSINESS_CONNECTION_ID} {FROM_CHAT_ID} "
            f"{FROM_STORY_ID} 3600"
        ),
        chat_id=42,
    )

    await commands.cmd_repost_story(message)

    commands.perform_repost_story.assert_not_awaited()
    args, _ = message.answer.await_args
    assert "Active period must be one of" in args[0]


async def test_cmd_repost_story_reposts_story(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_repost_story", AsyncMock(return_value={"id": 78})
    )
    message = _message(
        text=(
            f"/repoststory {BUSINESS_CONNECTION_ID} {FROM_CHAT_ID} "
            f"{FROM_STORY_ID} 86400"
        ),
        chat_id=42,
    )

    await commands.cmd_repost_story(message)

    commands.perform_repost_story.assert_awaited_once_with(
        message.bot,
        business_connection_id=BUSINESS_CONNECTION_ID,
        from_chat_id=FROM_CHAT_ID,
        from_story_id=FROM_STORY_ID,
        active_period=86400,
    )
    message.answer.assert_awaited_once_with("Reposted story 78.")
