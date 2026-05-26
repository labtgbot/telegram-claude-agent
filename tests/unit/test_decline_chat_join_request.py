from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import DeclineChatJoinRequest

from bot.handlers import commands
from bot.services import decline_chat_join_request
from bot.services.decline_chat_join_request import (
    DeclineChatJoinRequestError,
    format_decline_chat_join_request_result,
    perform_decline_chat_join_request,
)


class _FakeResponse:
    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data


class _FakeClient:
    def __init__(self, response):
        self._response = response
        self.posted = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, url, json):
        self.posted = {"url": url, "json": json}
        return self._response


def _message(text: str = "/declinechatjoinrequest", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_perform_decline_chat_join_request_uses_typed_aiogram_api():
    bot = SimpleNamespace(decline_chat_join_request=AsyncMock(return_value=True))

    result = await perform_decline_chat_join_request(
        bot,
        chat_id=-100123,
        user_id=456,
    )

    assert result is True
    bot.decline_chat_join_request.assert_awaited_once_with(
        chat_id=-100123,
        user_id=456,
    )


async def test_perform_decline_chat_join_request_posts_raw_payload_when_typed_missing(
    monkeypatch,
):
    client = _FakeClient(_FakeResponse({"ok": True, "result": True}))
    monkeypatch.setattr(
        decline_chat_join_request.httpx,
        "AsyncClient",
        lambda *args, **kwargs: client,
    )
    bot = SimpleNamespace(
        token="123:abc",
        session=SimpleNamespace(
            api=SimpleNamespace(
                api_url=lambda token, method: (
                    f"https://api.telegram.org/bot{token}/{method}"
                )
            )
        ),
    )

    result = await perform_decline_chat_join_request(
        bot,
        chat_id=-100123,
        user_id=456,
    )

    assert result is True
    assert client.posted["url"] == (
        "https://api.telegram.org/bot123:abc/declineChatJoinRequest"
    )
    assert client.posted["json"] == {"chat_id": -100123, "user_id": 456}


async def test_perform_decline_chat_join_request_reraises_bad_request():
    error = TelegramBadRequest(
        method=DeclineChatJoinRequest(chat_id=-100123, user_id=456),
        message="Bad Request: HIDE_REQUESTER_MISSING",
    )
    bot = SimpleNamespace(decline_chat_join_request=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_decline_chat_join_request(
            bot,
            chat_id=-100123,
            user_id=456,
        )


async def test_perform_decline_chat_join_request_reraises_forbidden():
    error = TelegramForbiddenError(
        method=DeclineChatJoinRequest(chat_id=-100123, user_id=456),
        message="Forbidden: bot is not an administrator",
    )
    bot = SimpleNamespace(decline_chat_join_request=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_decline_chat_join_request(
            bot,
            chat_id=-100123,
            user_id=456,
        )


async def test_perform_decline_chat_join_request_rejects_invalid_user_id():
    bot = SimpleNamespace(decline_chat_join_request=AsyncMock())

    with pytest.raises(DeclineChatJoinRequestError):
        await perform_decline_chat_join_request(bot, chat_id=-100123, user_id=0)

    bot.decline_chat_join_request.assert_not_awaited()


async def test_perform_decline_chat_join_request_raises_raw_telegram_error(
    monkeypatch,
):
    client = _FakeClient(
        _FakeResponse(
            {
                "ok": False,
                "error_code": 400,
                "description": "Bad Request: user not found",
            }
        )
    )
    monkeypatch.setattr(
        decline_chat_join_request.httpx,
        "AsyncClient",
        lambda *args, **kwargs: client,
    )
    bot = SimpleNamespace(token="123:abc", session=None)

    with pytest.raises(DeclineChatJoinRequestError) as exc_info:
        await perform_decline_chat_join_request(
            bot,
            chat_id=-100123,
            user_id=456,
        )

    assert exc_info.value.error_code == 400
    assert "user not found" in str(exc_info.value)


def test_format_decline_chat_join_request_result_escapes_values():
    text = format_decline_chat_join_request_result(
        chat_id=-100123,
        user_id=456,
    )

    assert "declineChatJoinRequest" in text
    assert "-100123" in text
    assert "456" in text
    assert "join request declined successfully" in text


async def test_cmd_decline_chat_join_request_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_decline_chat_join_request", AsyncMock())
    message = _message(text="/declinechatjoinrequest -100123 456", chat_id=42)

    await commands.cmd_decline_chat_join_request(message)

    commands.perform_decline_chat_join_request.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_decline_chat_join_request_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_decline_chat_join_request", AsyncMock())
    message = _message(text="/declinechatjoinrequest", chat_id=42)

    await commands.cmd_decline_chat_join_request(message)

    commands.perform_decline_chat_join_request.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "declinechatjoinrequest usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_decline_chat_join_request_calls_service(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_decline_chat_join_request",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(
        commands,
        "format_decline_chat_join_request_result",
        lambda **kwargs: "ok",
    )
    message = _message(text="/declinechatjoinrequest -100123 456", chat_id=42)

    await commands.cmd_decline_chat_join_request(message)

    commands.perform_decline_chat_join_request.assert_awaited_once_with(
        message.bot,
        chat_id=-100123,
        user_id=456,
    )
    args, kwargs = message.answer.await_args
    assert args[0] == "ok"
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_decline_chat_join_request_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(
        method=DeclineChatJoinRequest(chat_id=-100123, user_id=456),
        message="Bad Request: not enough rights",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_decline_chat_join_request",
        AsyncMock(side_effect=error),
    )
    message = _message(text="/declinechatjoinrequest -100123 456", chat_id=42)

    await commands.cmd_decline_chat_join_request(message)

    args, _ = message.answer.await_args
    assert "Could not decline the chat join request" in args[0]


def test_parse_decline_chat_join_request_args_no_args():
    assert commands._parse_decline_chat_join_request_args(
        "/declinechatjoinrequest"
    ) is None


def test_parse_decline_chat_join_request_args_required_args():
    assert commands._parse_decline_chat_join_request_args(
        "/declinechatjoinrequest -100123 456"
    ) == (-100123, 456)


def test_parse_decline_chat_join_request_args_invalid_chat_id():
    assert commands._parse_decline_chat_join_request_args(
        "/declinechatjoinrequest bad 456"
    ) is None


def test_parse_decline_chat_join_request_args_invalid_user_id():
    assert commands._parse_decline_chat_join_request_args(
        "/declinechatjoinrequest -100123 bad"
    ) is None


def test_parse_decline_chat_join_request_args_extra_args():
    assert commands._parse_decline_chat_join_request_args(
        "/declinechatjoinrequest -100123 456 extra"
    ) is None
