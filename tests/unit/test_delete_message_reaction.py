from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from bot.handlers import commands
from bot.services.delete_message_reaction import (
    format_delete_message_reaction_result,
    perform_delete_message_reaction,
)


def _message(text: str = "/deletereaction", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_perform_delete_message_reaction_uses_typed_aiogram_api():
    bot = SimpleNamespace(delete_message_reaction=AsyncMock(return_value=True))

    result = await perform_delete_message_reaction(
        bot,
        chat_id=-100123,
        message_id=55,
        user_id=777,
    )

    assert result is True
    bot.delete_message_reaction.assert_awaited_once_with(
        chat_id=-100123,
        message_id=55,
        user_id=777,
    )


async def test_perform_delete_message_reaction_reraises_bad_request():
    error = TelegramBadRequest(method=None, message="Bad Request: reaction not found")
    bot = SimpleNamespace(delete_message_reaction=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_delete_message_reaction(
            bot,
            chat_id=-100123,
            message_id=55,
            user_id=777,
        )


async def test_perform_delete_message_reaction_reraises_forbidden():
    error = TelegramForbiddenError(method=None, message="Forbidden: bot is not an admin")
    bot = SimpleNamespace(delete_message_reaction=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_delete_message_reaction(
            bot,
            chat_id=-100123,
            message_id=55,
            user_id=777,
        )


def test_format_delete_message_reaction_result():
    text = format_delete_message_reaction_result(
        chat_id=-100123,
        message_id=55,
        user_id=777,
    )

    assert "deleteMessageReaction" in text
    assert "-100123" in text
    assert "55" in text
    assert "777" in text
    assert "reaction deleted" in text


def test_parse_delete_message_reaction_args():
    assert commands._parse_delete_message_reaction_args(
        "/deletereaction -100123 55 777"
    ) == (-100123, 55, 777)
    assert commands._parse_delete_message_reaction_args("/deletereaction") is None
    assert commands._parse_delete_message_reaction_args(
        "/deletereaction -100123 not-int 777"
    ) is None
    assert commands._parse_delete_message_reaction_args(
        "/deletereaction -100123 55 not-int"
    ) is None
    assert commands._parse_delete_message_reaction_args(
        "/deletereaction -100123 0 777"
    ) is None
    assert commands._parse_delete_message_reaction_args(
        "/deletereaction -100123 55 0"
    ) is None


async def test_cmd_delete_message_reaction_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_delete_message_reaction", AsyncMock())
    message = _message(text="/deletereaction -100123 55 777", chat_id=42)

    await commands.cmd_delete_message_reaction(message)

    commands.perform_delete_message_reaction.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_delete_message_reaction_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_delete_message_reaction", AsyncMock())
    message = _message(text="/deletereaction", chat_id=42)

    await commands.cmd_delete_message_reaction(message)

    commands.perform_delete_message_reaction.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "deletereaction usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_delete_message_reaction_calls_service(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_delete_message_reaction", AsyncMock(return_value=True)
    )
    monkeypatch.setattr(commands, "format_delete_message_reaction_result", lambda **_: "ok")
    message = _message(text="/deletereaction -100123 55 777", chat_id=42)

    await commands.cmd_delete_message_reaction(message)

    commands.perform_delete_message_reaction.assert_awaited_once_with(
        message.bot,
        chat_id=-100123,
        message_id=55,
        user_id=777,
    )
    message.answer.assert_awaited_once_with("ok", parse_mode="HTML")


async def test_cmd_delete_message_reaction_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(method=None, message="Bad Request: reaction not found")
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_delete_message_reaction", AsyncMock(side_effect=error)
    )
    message = _message(text="/deletereaction -100123 55 777", chat_id=42)

    await commands.cmd_delete_message_reaction(message)

    args, _ = message.answer.await_args
    assert "Could not delete the message reaction" in args[0]
    assert "reaction not found" not in args[0]
    assert "Please try again later" in args[0]
