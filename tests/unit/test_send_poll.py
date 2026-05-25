from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import SendPoll

from bot.handlers import commands
from bot.services.send_poll import perform_send_poll

QUESTION = "What is the best editor?"
OPTIONS = ["Vim", "Emacs", "VS Code"]


async def test_perform_send_poll_uses_typed_aiogram_api():
    sent = SimpleNamespace(message_id=777)
    bot = SimpleNamespace(send_poll=AsyncMock(return_value=sent))

    result = await perform_send_poll(
        bot,
        chat_id=42,
        question=QUESTION,
        options=OPTIONS,
    )

    assert result is sent
    bot.send_poll.assert_awaited_once_with(
        chat_id=42,
        question=QUESTION,
        options=OPTIONS,
        is_anonymous=None,
        type=None,
        allows_multiple_answers=None,
        correct_option_id=None,
        explanation=None,
        open_period=None,
        close_date=None,
        is_closed=None,
        message_thread_id=None,
        disable_notification=None,
        protect_content=None,
    )


async def test_perform_send_poll_forwards_quiz_metadata():
    bot = SimpleNamespace(send_poll=AsyncMock(return_value=SimpleNamespace(message_id=1)))

    await perform_send_poll(
        bot,
        chat_id=42,
        question=QUESTION,
        options=OPTIONS,
        type="quiz",
        correct_option_id=2,
        explanation="VS Code is the answer.",
        is_anonymous=False,
        open_period=60,
    )

    _, kwargs = bot.send_poll.await_args
    assert kwargs["type"] == "quiz"
    assert kwargs["correct_option_id"] == 2
    assert kwargs["explanation"] == "VS Code is the answer."
    assert kwargs["is_anonymous"] is False
    assert kwargs["open_period"] == 60


async def test_perform_send_poll_reraises_telegram_errors():
    error = TelegramBadRequest(
        method=SendPoll(chat_id=1, question=QUESTION, options=OPTIONS),
        message="Bad Request: poll must have at least 2 option",
    )
    bot = SimpleNamespace(send_poll=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_send_poll(
            bot,
            chat_id=1,
            question=QUESTION,
            options=OPTIONS,
        )


async def test_perform_send_poll_reraises_forbidden():
    error = TelegramForbiddenError(
        method=SendPoll(chat_id=1, question=QUESTION, options=OPTIONS),
        message="Forbidden: bot was blocked by the user",
    )
    bot = SimpleNamespace(send_poll=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_send_poll(
            bot,
            chat_id=1,
            question=QUESTION,
            options=OPTIONS,
        )


def _message(text: str = "/poll", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_poll_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_poll", AsyncMock())
    message = _message(text=f"/poll {QUESTION} | Vim | Emacs", chat_id=42)

    await commands.cmd_poll(message)

    commands.perform_send_poll.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_poll_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_poll", AsyncMock())
    message = _message(text="/poll", chat_id=42)

    await commands.cmd_poll(message)

    commands.perform_send_poll.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "poll usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_poll_shows_usage_without_options(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_poll", AsyncMock())
    message = _message(text="/poll Just a question with no separator", chat_id=42)

    await commands.cmd_poll(message)

    commands.perform_send_poll.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "poll usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_poll_shows_usage_for_empty_option(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_poll", AsyncMock())
    message = _message(text=f"/poll {QUESTION} | Vim | ", chat_id=42)

    await commands.cmd_poll(message)

    commands.perform_send_poll.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "poll usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_poll_shows_usage_for_empty_question(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_poll", AsyncMock())
    message = _message(text="/poll  | Vim | Emacs", chat_id=42)

    await commands.cmd_poll(message)

    commands.perform_send_poll.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "poll usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_poll_sends_poll(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_send_poll", AsyncMock(return_value=object())
    )
    message = _message(text=f"/poll {QUESTION} | Vim | Emacs | VS Code", chat_id=42)

    await commands.cmd_poll(message)

    commands.perform_send_poll.assert_awaited_once_with(
        message.bot,
        chat_id=42,
        question=QUESTION,
        options=["Vim", "Emacs", "VS Code"],
    )
    args, _ = message.answer.await_args
    assert args[0] == "Sent poll with 3 options."


async def test_cmd_poll_keeps_spaces_in_question_and_options(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_send_poll", AsyncMock(return_value=object())
    )
    message = _message(
        text="/poll  The   Question   |   Option  One  |  Option  Two  ",
        chat_id=42,
    )

    await commands.cmd_poll(message)

    _, kwargs = commands.perform_send_poll.await_args
    assert kwargs["question"] == "The   Question"
    assert kwargs["options"] == ["Option  One", "Option  Two"]


async def test_cmd_poll_rejects_too_few_options(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_poll", AsyncMock())
    message = _message(text=f"/poll {QUESTION} | Only one", chat_id=42)

    await commands.cmd_poll(message)

    commands.perform_send_poll.assert_not_awaited()
    args, _ = message.answer.await_args
    assert "A poll needs between" in args[0]


async def test_cmd_poll_rejects_too_many_options(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_poll", AsyncMock())
    options = " | ".join(f"Option {i}" for i in range(11))
    message = _message(text=f"/poll {QUESTION} | {options}", chat_id=42)

    await commands.cmd_poll(message)

    commands.perform_send_poll.assert_not_awaited()
    args, _ = message.answer.await_args
    assert "A poll needs between" in args[0]


async def test_cmd_poll_rejects_too_long_question(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_poll", AsyncMock())
    long_question = "Q" * 301
    message = _message(text=f"/poll {long_question} | Vim | Emacs", chat_id=42)

    await commands.cmd_poll(message)

    commands.perform_send_poll.assert_not_awaited()
    args, _ = message.answer.await_args
    assert "Question is too long" in args[0]


async def test_cmd_poll_rejects_too_long_option(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_poll", AsyncMock())
    long_option = "A" * 101
    message = _message(text=f"/poll {QUESTION} | Vim | {long_option}", chat_id=42)

    await commands.cmd_poll(message)

    commands.perform_send_poll.assert_not_awaited()
    args, _ = message.answer.await_args
    assert "Option is too long" in args[0]


async def test_cmd_poll_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(
        method=SendPoll(chat_id=42, question=QUESTION, options=OPTIONS),
        message="Bad Request: chat not found",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_send_poll", AsyncMock(side_effect=error)
    )
    message = _message(text=f"/poll {QUESTION} | Vim | Emacs", chat_id=42)

    await commands.cmd_poll(message)

    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Could not send the poll" in args[0]
