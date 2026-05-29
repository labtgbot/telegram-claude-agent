from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import SendGame

from bot.handlers import commands
from bot.services.send_game import SendGameValidationError, perform_send_game


async def test_perform_send_game_uses_typed_aiogram_api():
    sent = SimpleNamespace(message_id=777)
    bot = SimpleNamespace(send_game=AsyncMock(return_value=sent))

    result = await perform_send_game(
        bot,
        chat_id=42,
        game_short_name="free_claude_code_demo",
    )

    assert result is sent
    bot.send_game.assert_awaited_once_with(
        chat_id=42,
        game_short_name="free_claude_code_demo",
        message_thread_id=None,
        disable_notification=None,
        protect_content=None,
    )


async def test_perform_send_game_forwards_optional_fields():
    bot = SimpleNamespace(send_game=AsyncMock(return_value=SimpleNamespace(message_id=1)))

    await perform_send_game(
        bot,
        chat_id=42,
        game_short_name="demo_game",
        message_thread_id=5,
        disable_notification=True,
        protect_content=True,
    )

    _, kwargs = bot.send_game.await_args
    assert kwargs["game_short_name"] == "demo_game"
    assert kwargs["message_thread_id"] == 5
    assert kwargs["disable_notification"] is True
    assert kwargs["protect_content"] is True


async def test_perform_send_game_rejects_empty_short_name():
    bot = SimpleNamespace(send_game=AsyncMock())

    with pytest.raises(SendGameValidationError):
        await perform_send_game(bot, chat_id=42, game_short_name="   ")

    bot.send_game.assert_not_awaited()


async def test_perform_send_game_reraises_telegram_errors():
    error = TelegramBadRequest(
        method=SendGame(chat_id=1, game_short_name="demo_game"),
        message="Bad Request: game not found",
    )
    bot = SimpleNamespace(send_game=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_send_game(bot, chat_id=1, game_short_name="demo_game")


async def test_perform_send_game_reraises_forbidden():
    error = TelegramForbiddenError(
        method=SendGame(chat_id=1, game_short_name="demo_game"),
        message="Forbidden: bot was blocked by the user",
    )
    bot = SimpleNamespace(send_game=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_send_game(bot, chat_id=1, game_short_name="demo_game")


def _message(text: str = "/game demo_game", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_game_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_game", AsyncMock())
    message = _message(chat_id=42)

    await commands.cmd_game(message)

    commands.perform_send_game.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_game_sends_game(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_send_game", AsyncMock(return_value=object())
    )
    message = _message(text="/game free_claude_code_demo", chat_id=42)

    await commands.cmd_game(message)

    commands.perform_send_game.assert_awaited_once_with(
        message.bot,
        chat_id=42,
        game_short_name="free_claude_code_demo",
    )
    args, _ = message.answer.await_args
    assert args[0] == "Sent game."


async def test_cmd_game_shows_usage_for_missing_short_name(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_game", AsyncMock())
    message = _message(text="/game", chat_id=42)

    await commands.cmd_game(message)

    commands.perform_send_game.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "game usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_game_shows_usage_for_too_many_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_game", AsyncMock())
    message = _message(text="/game first second", chat_id=42)

    await commands.cmd_game(message)

    commands.perform_send_game.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "game usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_game_reports_validation_errors(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_send_game",
        AsyncMock(side_effect=SendGameValidationError("game_short_name must be non-empty.")),
    )
    message = _message(text="/game demo_game", chat_id=42)

    await commands.cmd_game(message)

    args, _ = message.answer.await_args
    assert "Could not send the game" in args[0]


async def test_cmd_game_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(
        method=SendGame(chat_id=42, game_short_name="demo_game"),
        message="Bad Request: game not found",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_send_game", AsyncMock(side_effect=error)
    )
    message = _message(text="/game demo_game", chat_id=42)

    await commands.cmd_game(message)

    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Could not send the game" in args[0]
