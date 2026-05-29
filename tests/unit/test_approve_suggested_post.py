from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import approve_suggested_post
from bot.services.approve_suggested_post import (
    ApproveSuggestedPostError,
    format_approve_suggested_post_result,
    perform_approve_suggested_post,
)


class _Response:
    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data


async def test_perform_approve_suggested_post_posts_raw_payload(monkeypatch):
    posted = {}

    class Client:
        def __init__(self, timeout):
            posted["timeout"] = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, json):
            posted["url"] = url
            posted["json"] = json
            return _Response({"ok": True, "result": True})

    monkeypatch.setattr(approve_suggested_post.httpx, "AsyncClient", Client)
    bot = SimpleNamespace(token="123:abc")

    result = await perform_approve_suggested_post(
        bot,
        chat_id=-100123,
        message_id=777,
        send_date=1_800_000_000,
        request_timeout=5.0,
    )

    assert result is True
    assert posted["timeout"] == 5.0
    assert posted["url"] == "https://api.telegram.org/bot123:abc/approveSuggestedPost"
    assert posted["json"] == {
        "chat_id": -100123,
        "message_id": 777,
        "send_date": 1_800_000_000,
    }


async def test_perform_approve_suggested_post_uses_custom_api_url(monkeypatch):
    posted = {}
    api = SimpleNamespace(
        api_url=lambda *, token, method: f"http://local/bot{token}/{method}"
    )

    class Client:
        def __init__(self, timeout):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, json):
            posted["url"] = url
            posted["json"] = json
            return _Response({"ok": True, "result": True})

    monkeypatch.setattr(approve_suggested_post.httpx, "AsyncClient", Client)
    bot = SimpleNamespace(token="123:abc", session=SimpleNamespace(api=api))

    await perform_approve_suggested_post(bot, chat_id="@channel", message_id=777)

    assert posted["url"] == "http://local/bot123:abc/approveSuggestedPost"
    assert posted["json"] == {"chat_id": "@channel", "message_id": 777}


async def test_perform_approve_suggested_post_rejects_invalid_input(monkeypatch):
    client = AsyncMock()
    monkeypatch.setattr(approve_suggested_post.httpx, "AsyncClient", client)
    bot = SimpleNamespace(token="123:abc")

    with pytest.raises(ApproveSuggestedPostError):
        await perform_approve_suggested_post(bot, chat_id="", message_id=777)
    with pytest.raises(ApproveSuggestedPostError):
        await perform_approve_suggested_post(bot, chat_id=-100123, message_id=0)
    with pytest.raises(ApproveSuggestedPostError):
        await perform_approve_suggested_post(
            bot,
            chat_id=-100123,
            message_id=777,
            send_date=0,
        )

    client.assert_not_called()


async def test_perform_approve_suggested_post_reports_telegram_error(monkeypatch):
    class Client:
        def __init__(self, timeout):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, json):
            return _Response(
                {
                    "ok": False,
                    "error_code": 400,
                    "description": "Bad Request: suggested post not found",
                }
            )

    monkeypatch.setattr(approve_suggested_post.httpx, "AsyncClient", Client)
    bot = SimpleNamespace(token="123:abc")

    with pytest.raises(ApproveSuggestedPostError) as exc_info:
        await perform_approve_suggested_post(bot, chat_id=-100123, message_id=777)

    assert exc_info.value.error_code == 400
    assert "suggested post not found" in str(exc_info.value)


async def test_perform_approve_suggested_post_reports_transport_error(monkeypatch):
    class Client:
        def __init__(self, timeout):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, json):
            raise httpx.ConnectError("offline")

    monkeypatch.setattr(approve_suggested_post.httpx, "AsyncClient", Client)
    bot = SimpleNamespace(token="123:abc")

    with pytest.raises(ApproveSuggestedPostError) as exc_info:
        await perform_approve_suggested_post(bot, chat_id=-100123, message_id=777)

    assert "approveSuggestedPost request failed" in str(exc_info.value)


def test_format_approve_suggested_post_result():
    text = format_approve_suggested_post_result(
        chat_id=-100123,
        message_id=777,
        send_date=1_800_000_000,
    )

    assert "approveSuggestedPost" in text
    assert "-100123" in text
    assert "777" in text
    assert "1800000000" in text


def _message(text: str = "/approvesuggestedpost", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_approve_suggested_post_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_approve_suggested_post", AsyncMock())
    message = _message(text="/approvesuggestedpost -100123 777")

    await commands.cmd_approve_suggested_post(message)

    commands.perform_approve_suggested_post.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_approve_suggested_post_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_approve_suggested_post", AsyncMock())
    message = _message()

    await commands.cmd_approve_suggested_post(message)

    commands.perform_approve_suggested_post.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "approvesuggestedpost usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_approve_suggested_post_calls_service(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_approve_suggested_post", AsyncMock())
    monkeypatch.setattr(
        commands,
        "format_approve_suggested_post_result",
        lambda **kwargs: "ok",
    )
    message = _message(text="/approvesuggestedpost -100123 777 1800000000")

    await commands.cmd_approve_suggested_post(message)

    commands.perform_approve_suggested_post.assert_awaited_once_with(
        message.bot,
        chat_id=-100123,
        message_id=777,
        send_date=1_800_000_000,
    )
    message.answer.assert_awaited_once_with("ok", parse_mode="HTML")


async def test_cmd_approve_suggested_post_reports_service_error(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_approve_suggested_post",
        AsyncMock(side_effect=ApproveSuggestedPostError("not found")),
    )
    message = _message(text="/approvesuggestedpost -100123 777")

    await commands.cmd_approve_suggested_post(message)

    args, _ = message.answer.await_args
    assert "Could not approve the suggested post" in args[0]


def test_parse_approve_suggested_post_args():
    assert commands._parse_approve_suggested_post_args(
        "/approvesuggestedpost -100123 777"
    ) == (-100123, 777, None)
    assert commands._parse_approve_suggested_post_args(
        "/approvesuggestedpost @channel 777 1800000000"
    ) == ("@channel", 777, 1_800_000_000)
    assert commands._parse_approve_suggested_post_args("/approvesuggestedpost") is None
    assert (
        commands._parse_approve_suggested_post_args(
            "/approvesuggestedpost channel 777"
        )
        is None
    )
    assert (
        commands._parse_approve_suggested_post_args(
            "/approvesuggestedpost -100123 0"
        )
        is None
    )
    assert (
        commands._parse_approve_suggested_post_args(
            "/approvesuggestedpost -100123 777 0"
        )
        is None
    )
