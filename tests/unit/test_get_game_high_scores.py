from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import GetGameHighScores

from bot.handlers import commands
from bot.services.get_game_high_scores import (
    GetGameHighScoresValidationError,
    perform_get_game_high_scores,
)


async def test_perform_get_game_high_scores_uses_typed_aiogram_api_for_chat_message():
    scores = [SimpleNamespace(position=1, user=SimpleNamespace(id=1001), score=42)]
    bot = SimpleNamespace(get_game_high_scores=AsyncMock(return_value=scores))

    result = await perform_get_game_high_scores(
        bot,
        user_id=1001,
        chat_id=42,
        message_id=777,
    )

    assert result == scores
    bot.get_game_high_scores.assert_awaited_once_with(
        user_id=1001,
        chat_id=42,
        message_id=777,
        inline_message_id=None,
    )


async def test_perform_get_game_high_scores_forwards_inline_message_id():
    bot = SimpleNamespace(get_game_high_scores=AsyncMock(return_value=[]))

    await perform_get_game_high_scores(
        bot,
        user_id=1001,
        inline_message_id=" inline-42 ",
    )

    _, kwargs = bot.get_game_high_scores.await_args
    assert kwargs["inline_message_id"] == "inline-42"
    assert kwargs["chat_id"] is None
    assert kwargs["message_id"] is None


@pytest.mark.parametrize(
    "kwargs",
    [
        {"user_id": 0, "chat_id": 42, "message_id": 7},
        {"user_id": 1, "chat_id": 42},
        {"user_id": 1, "message_id": 7},
        {
            "user_id": 1,
            "chat_id": 42,
            "message_id": 7,
            "inline_message_id": "abc",
        },
        {"user_id": 1, "inline_message_id": "   "},
    ],
)
async def test_perform_get_game_high_scores_rejects_invalid_targets(kwargs):
    bot = SimpleNamespace(get_game_high_scores=AsyncMock())

    with pytest.raises(GetGameHighScoresValidationError):
        await perform_get_game_high_scores(bot, **kwargs)

    bot.get_game_high_scores.assert_not_awaited()


async def test_perform_get_game_high_scores_reraises_telegram_errors():
    error = TelegramBadRequest(
        method=GetGameHighScores(user_id=1, chat_id=42, message_id=7),
        message="Bad Request: message is not a game",
    )
    bot = SimpleNamespace(get_game_high_scores=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_get_game_high_scores(
            bot,
            user_id=1,
            chat_id=42,
            message_id=7,
        )


async def test_perform_get_game_high_scores_reraises_forbidden():
    error = TelegramForbiddenError(
        method=GetGameHighScores(user_id=1, chat_id=42, message_id=7),
        message="Forbidden: bot was blocked by the user",
    )
    bot = SimpleNamespace(get_game_high_scores=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_get_game_high_scores(
            bot,
            user_id=1,
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


async def test_cmd_get_game_high_scores_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_get_game_high_scores", AsyncMock())
    message = _message("/gamehighscores 1001 chat_id=42 message_id=777")

    await commands.cmd_get_game_high_scores(message)

    commands.perform_get_game_high_scores.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_get_game_high_scores_fetches_chat_message_scores(monkeypatch):
    scores = [SimpleNamespace(position=1, user=SimpleNamespace(id=1001), score=42)]
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_get_game_high_scores", AsyncMock(return_value=scores)
    )
    message = _message("/gamehighscores 1001 chat_id=42 message_id=777")

    await commands.cmd_get_game_high_scores(message)

    commands.perform_get_game_high_scores.assert_awaited_once_with(
        message.bot,
        user_id=1001,
        chat_id=42,
        message_id=777,
        inline_message_id=None,
    )
    message.answer.assert_awaited_once_with(
        "Game high scores:\n1. user_id=1001 score=42"
    )


async def test_cmd_get_game_high_scores_fetches_inline_scores(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_get_game_high_scores", AsyncMock(return_value=[])
    )
    message = _message("/gamehighscores 1001 inline_message_id=inline-777")

    await commands.cmd_get_game_high_scores(message)

    commands.perform_get_game_high_scores.assert_awaited_once_with(
        message.bot,
        user_id=1001,
        chat_id=None,
        message_id=None,
        inline_message_id="inline-777",
    )
    message.answer.assert_awaited_once_with("No game high scores returned.")


@pytest.mark.parametrize(
    "text",
    [
        "/gamehighscores",
        "/gamehighscores 1001",
        "/gamehighscores abc chat_id=42 message_id=777",
        "/gamehighscores 1001 chat_id=42",
        "/gamehighscores 1001 message_id=777",
        "/gamehighscores 1001 chat_id=42 message_id=777 inline_message_id=x",
        "/gamehighscores 1001 unknown=1",
    ],
)
async def test_cmd_get_game_high_scores_shows_usage_for_invalid_args(monkeypatch, text):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_get_game_high_scores", AsyncMock())
    message = _message(text)

    await commands.cmd_get_game_high_scores(message)

    commands.perform_get_game_high_scores.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "gamehighscores usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_get_game_high_scores_reports_validation_errors(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_get_game_high_scores",
        AsyncMock(
            side_effect=GetGameHighScoresValidationError(
                "inline_message_id must be non-empty."
            )
        ),
    )
    message = _message("/gamehighscores 1001 inline_message_id=inline-777")

    await commands.cmd_get_game_high_scores(message)

    args, _ = message.answer.await_args
    assert "Could not fetch game high scores" in args[0]


async def test_cmd_get_game_high_scores_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(
        method=GetGameHighScores(user_id=1, chat_id=42, message_id=7),
        message="Bad Request: message is not a game",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_get_game_high_scores", AsyncMock(side_effect=error)
    )
    message = _message("/gamehighscores 1 chat_id=42 message_id=7")

    await commands.cmd_get_game_high_scores(message)

    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Could not fetch game high scores" in args[0]
