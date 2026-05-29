from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import StopPoll
from aiogram.types import Poll, PollOption

from bot.handlers import commands
from bot.services.stop_poll import (
    StopPollValidationError,
    format_stop_poll_result,
    perform_stop_poll,
)


def _poll() -> Poll:
    return Poll(
        id="poll-1",
        question="Deploy now?",
        options=[
            PollOption(text="Yes", voter_count=2, persistent_id="yes"),
            PollOption(text="No", voter_count=1, persistent_id="no"),
        ],
        total_voter_count=3,
        is_closed=True,
        is_anonymous=False,
        type="regular",
        allows_multiple_answers=False,
        allows_revoting=False,
        members_only=False,
    )


async def test_perform_stop_poll_uses_typed_aiogram_api():
    expected = _poll()
    bot = SimpleNamespace(stop_poll=AsyncMock(return_value=expected))

    result = await perform_stop_poll(bot, chat_id=-100123, message_id=777)

    assert result == expected
    bot.stop_poll.assert_awaited_once_with(
        chat_id=-100123,
        message_id=777,
        reply_markup=None,
    )


async def test_perform_stop_poll_passes_reply_markup():
    bot = SimpleNamespace(stop_poll=AsyncMock(return_value=_poll()))
    reply_markup = {"inline_keyboard": []}

    await perform_stop_poll(
        bot,
        chat_id="@channel",
        message_id=777,
        reply_markup=reply_markup,
    )

    bot.stop_poll.assert_awaited_once_with(
        chat_id="@channel",
        message_id=777,
        reply_markup=reply_markup,
    )


async def test_perform_stop_poll_rejects_invalid_input():
    bot = SimpleNamespace(stop_poll=AsyncMock())

    with pytest.raises(StopPollValidationError):
        await perform_stop_poll(bot, chat_id="", message_id=777)
    with pytest.raises(StopPollValidationError):
        await perform_stop_poll(bot, chat_id=-100123, message_id=0)

    bot.stop_poll.assert_not_awaited()


async def test_perform_stop_poll_reraises_bad_request():
    error = TelegramBadRequest(
        method=StopPoll(chat_id=-100123, message_id=777),
        message="Bad Request: poll has already been closed",
    )
    bot = SimpleNamespace(stop_poll=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_stop_poll(bot, chat_id=-100123, message_id=777)


async def test_perform_stop_poll_reraises_forbidden():
    error = TelegramForbiddenError(
        method=StopPoll(chat_id=-100123, message_id=777),
        message="Forbidden: bot is not a member of the chat",
    )
    bot = SimpleNamespace(stop_poll=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_stop_poll(bot, chat_id=-100123, message_id=777)


def test_format_stop_poll_result_includes_final_poll_state():
    text = format_stop_poll_result(_poll(), chat_id=-100123, message_id=777)

    assert "stopPoll" in text
    assert "-100123" in text
    assert "777" in text
    assert "3" in text


def _message(text: str = "/stoppoll", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_stop_poll_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_stop_poll", AsyncMock())
    message = _message(text="/stoppoll -100123 777", chat_id=42)

    await commands.cmd_stop_poll(message)

    commands.perform_stop_poll.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_stop_poll_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_stop_poll", AsyncMock())
    message = _message(text="/stoppoll", chat_id=42)

    await commands.cmd_stop_poll(message)

    commands.perform_stop_poll.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "stoppoll usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_stop_poll_calls_service(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_stop_poll",
        AsyncMock(return_value=_poll()),
    )
    monkeypatch.setattr(commands, "format_stop_poll_result", lambda *_, **__: "ok")
    message = _message(text="/stoppoll -100123 777", chat_id=42)

    await commands.cmd_stop_poll(message)

    commands.perform_stop_poll.assert_awaited_once_with(
        message.bot,
        chat_id=-100123,
        message_id=777,
    )
    message.answer.assert_awaited_once_with("ok", parse_mode="HTML")


async def test_cmd_stop_poll_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(
        method=StopPoll(chat_id=-100123, message_id=777),
        message="Bad Request: poll can't be stopped",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_stop_poll", AsyncMock(side_effect=error))
    message = _message(text="/stoppoll -100123 777", chat_id=42)

    await commands.cmd_stop_poll(message)

    args, _ = message.answer.await_args
    assert "Could not stop the poll" in args[0]


def test_parse_stop_poll_args():
    assert commands._parse_stop_poll_args("/stoppoll -100123 777") == (-100123, 777)
    assert commands._parse_stop_poll_args("/stoppoll @channel 777") == (
        "@channel",
        777,
    )
    assert commands._parse_stop_poll_args("/stoppoll") is None
    assert commands._parse_stop_poll_args("/stoppoll chat 777") is None
    assert commands._parse_stop_poll_args("/stoppoll -100123 nope") is None
    assert commands._parse_stop_poll_args("/stoppoll -100123 0") is None
