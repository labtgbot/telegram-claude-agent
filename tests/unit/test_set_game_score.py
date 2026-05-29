from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import SetGameScore

from bot.handlers import commands
from bot.services.set_game_score import (
    SetGameScoreValidationError,
    perform_set_game_score,
)


async def test_perform_set_game_score_uses_typed_aiogram_api_for_chat_message():
    bot = SimpleNamespace(set_game_score=AsyncMock(return_value=True))

    result = await perform_set_game_score(
        bot,
        user_id=1001,
        score=42,
        chat_id=42,
        message_id=777,
    )

    assert result is True
    bot.set_game_score.assert_awaited_once_with(
        user_id=1001,
        score=42,
        force=None,
        disable_edit_message=None,
        chat_id=42,
        message_id=777,
        inline_message_id=None,
    )


async def test_perform_set_game_score_forwards_inline_and_optional_fields():
    bot = SimpleNamespace(set_game_score=AsyncMock(return_value=True))

    await perform_set_game_score(
        bot,
        user_id=1001,
        score=43,
        inline_message_id=" inline-42 ",
        force=True,
        disable_edit_message=True,
    )

    _, kwargs = bot.set_game_score.await_args
    assert kwargs["inline_message_id"] == "inline-42"
    assert kwargs["chat_id"] is None
    assert kwargs["message_id"] is None
    assert kwargs["force"] is True
    assert kwargs["disable_edit_message"] is True


@pytest.mark.parametrize(
    "kwargs",
    [
        {"user_id": 1, "score": -1, "chat_id": 42, "message_id": 7},
        {"user_id": 1, "score": 0, "chat_id": 42},
        {"user_id": 1, "score": 0, "message_id": 7},
        {
            "user_id": 1,
            "score": 0,
            "chat_id": 42,
            "message_id": 7,
            "inline_message_id": "abc",
        },
        {"user_id": 1, "score": 0, "inline_message_id": "   "},
    ],
)
async def test_perform_set_game_score_rejects_invalid_targets(kwargs):
    bot = SimpleNamespace(set_game_score=AsyncMock())

    with pytest.raises(SetGameScoreValidationError):
        await perform_set_game_score(bot, **kwargs)

    bot.set_game_score.assert_not_awaited()


async def test_perform_set_game_score_reraises_telegram_errors():
    error = TelegramBadRequest(
        method=SetGameScore(user_id=1, score=1, chat_id=42, message_id=7),
        message="Bad Request: message is not a game",
    )
    bot = SimpleNamespace(set_game_score=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_set_game_score(
            bot,
            user_id=1,
            score=1,
            chat_id=42,
            message_id=7,
        )


async def test_perform_set_game_score_reraises_forbidden():
    error = TelegramForbiddenError(
        method=SetGameScore(user_id=1, score=1, chat_id=42, message_id=7),
        message="Forbidden: bot was blocked by the user",
    )
    bot = SimpleNamespace(set_game_score=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_set_game_score(
            bot,
            user_id=1,
            score=1,
            chat_id=42,
            message_id=7,
        )


def _message(text: str, chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_set_game_score_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_set_game_score", AsyncMock())
    message = _message("/setgamescore 1001 42 chat_id=42 message_id=777")

    await commands.cmd_set_game_score(message)

    commands.perform_set_game_score.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_set_game_score_sets_chat_message_score(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_set_game_score", AsyncMock(return_value=True)
    )
    message = _message(
        "/setgamescore 1001 42 chat_id=42 message_id=777 "
        "force=true disable_edit_message=false"
    )

    await commands.cmd_set_game_score(message)

    commands.perform_set_game_score.assert_awaited_once_with(
        message.bot,
        user_id=1001,
        score=42,
        chat_id=42,
        message_id=777,
        inline_message_id=None,
        force=True,
        disable_edit_message=False,
    )
    message.answer.assert_awaited_once_with("Set game score.")


async def test_cmd_set_game_score_sets_inline_message_score(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_set_game_score", AsyncMock(return_value=True)
    )
    message = _message("/setgamescore 1001 42 inline_message_id=inline-777")

    await commands.cmd_set_game_score(message)

    commands.perform_set_game_score.assert_awaited_once_with(
        message.bot,
        user_id=1001,
        score=42,
        chat_id=None,
        message_id=None,
        inline_message_id="inline-777",
        force=None,
        disable_edit_message=None,
    )


@pytest.mark.parametrize(
    "text",
    [
        "/setgamescore",
        "/setgamescore 1001",
        "/setgamescore abc 42 chat_id=42 message_id=777",
        "/setgamescore 1001 abc chat_id=42 message_id=777",
        "/setgamescore 1001 42 chat_id=42",
        "/setgamescore 1001 42 message_id=777",
        "/setgamescore 1001 42 chat_id=42 message_id=777 inline_message_id=x",
        "/setgamescore 1001 42 inline_message_id=x force=maybe",
        "/setgamescore 1001 42 unknown=1",
    ],
)
async def test_cmd_set_game_score_shows_usage_for_invalid_args(monkeypatch, text):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_set_game_score", AsyncMock())
    message = _message(text)

    await commands.cmd_set_game_score(message)

    commands.perform_set_game_score.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "setgamescore usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_set_game_score_reports_validation_errors(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_set_game_score",
        AsyncMock(side_effect=SetGameScoreValidationError("score must be non-negative.")),
    )
    message = _message("/setgamescore 1001 -1 chat_id=42 message_id=777")

    await commands.cmd_set_game_score(message)

    args, _ = message.answer.await_args
    assert "Could not set the game score" in args[0]


async def test_cmd_set_game_score_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(
        method=SetGameScore(user_id=1, score=1, chat_id=42, message_id=7),
        message="Bad Request: score is not modified",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_set_game_score", AsyncMock(side_effect=error)
    )
    message = _message("/setgamescore 1 1 chat_id=42 message_id=7")

    await commands.cmd_set_game_score(message)

    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Could not set the game score" in args[0]
