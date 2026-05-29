from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import DeleteMessages

from bot.handlers import commands
from bot.services.delete_messages import (
    DeleteMessagesError,
    DeleteMessagesResult,
    format_delete_messages_result,
    perform_delete_messages,
)


MESSAGE_IDS = [101, 102]


async def test_perform_delete_messages_uses_typed_aiogram_api():
    bot = SimpleNamespace(delete_messages=AsyncMock(return_value=True))

    result = await perform_delete_messages(bot, chat_id=-100123, message_ids=MESSAGE_IDS)

    assert result.ok is True
    assert result.deleted_count == 2
    bot.delete_messages.assert_awaited_once_with(
        chat_id=-100123,
        message_ids=MESSAGE_IDS,
    )


async def test_perform_delete_messages_chunks_over_100_ids():
    ids = list(range(1, 206))
    bot = SimpleNamespace(delete_messages=AsyncMock(return_value=True))

    result = await perform_delete_messages(bot, chat_id=-100123, message_ids=ids)

    assert result.deleted_count == 205
    assert [
        call.kwargs["message_ids"] for call in bot.delete_messages.await_args_list
    ] == [
        list(range(1, 101)),
        list(range(101, 201)),
        list(range(201, 206)),
    ]


async def test_perform_delete_messages_reports_partial_chunk_errors():
    ids = list(range(1, 103))
    error = TelegramBadRequest(
        method=DeleteMessages(chat_id=-100123, message_ids=[101, 102]),
        message="Bad Request: messages can't be deleted",
    )
    bot = SimpleNamespace(delete_messages=AsyncMock(side_effect=[True, error]))

    result = await perform_delete_messages(bot, chat_id=-100123, message_ids=ids)

    assert result.ok is False
    assert result.deleted_count == 100
    assert len(result.failed_chunks) == 1
    assert result.failed_chunks[0].message_ids == [101, 102]
    assert "can't be deleted" in result.failed_chunks[0].message


async def test_perform_delete_messages_rejects_invalid_args():
    bot = SimpleNamespace(delete_messages=AsyncMock(return_value=True))

    for ids in ([], [0], [-1]):
        with pytest.raises(DeleteMessagesError):
            await perform_delete_messages(bot, chat_id=-100123, message_ids=ids)

    bot.delete_messages.assert_not_awaited()


def test_format_delete_messages_result():
    text = format_delete_messages_result(
        DeleteMessagesResult(
            chat_id=-100123,
            requested_count=2,
            deleted_count=1,
            failed_chunks=[],
        )
    )

    assert "deleteMessages" in text
    assert "-100123" in text
    assert "Requested: 2" in text
    assert "Deleted chunks count as: 1" in text


def test_parse_delete_messages_args():
    assert commands._parse_delete_messages_args(
        "/deletemessages -100123 101 102 confirm"
    ) == (-100123, MESSAGE_IDS, True)
    assert commands._parse_delete_messages_args(
        "/deletemessages -100123 101,102 confirm"
    ) == (-100123, MESSAGE_IDS, True)
    assert commands._parse_delete_messages_args("/deletemessages -100123 101 102") == (
        -100123,
        MESSAGE_IDS,
        False,
    )
    assert commands._parse_delete_messages_args("/deletemessages") is None
    assert commands._parse_delete_messages_args("/deletemessages nope 101") is None
    assert commands._parse_delete_messages_args("/deletemessages -100123 bad") is None
    assert commands._parse_delete_messages_args("/deletemessages -100123 0 confirm") is None


def _message(text: str = "/deletemessages", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_delete_messages_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_delete_messages", AsyncMock())
    message = _message(text="/deletemessages -100123 101 confirm", chat_id=42)

    await commands.cmd_delete_messages(message)

    commands.perform_delete_messages.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_delete_messages_requires_confirmation(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_delete_messages", AsyncMock())
    message = _message(text="/deletemessages -100123 101", chat_id=42)

    await commands.cmd_delete_messages(message)

    commands.perform_delete_messages.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "deletemessages confirmation required" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_delete_messages_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_delete_messages", AsyncMock())
    message = _message(text="/deletemessages", chat_id=42)

    await commands.cmd_delete_messages(message)

    commands.perform_delete_messages.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "deletemessages usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_delete_messages_calls_service(monkeypatch):
    result = DeleteMessagesResult(
        chat_id=-100123,
        requested_count=2,
        deleted_count=2,
        failed_chunks=[],
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_delete_messages", AsyncMock(return_value=result))
    monkeypatch.setattr(commands, "format_delete_messages_result", lambda _: "ok")
    message = _message(text="/deletemessages -100123 101,102 confirm", chat_id=42)

    await commands.cmd_delete_messages(message)

    commands.perform_delete_messages.assert_awaited_once_with(
        message.bot,
        chat_id=-100123,
        message_ids=MESSAGE_IDS,
    )
    message.answer.assert_awaited_once_with("ok", parse_mode="HTML")


async def test_cmd_delete_messages_reports_validation_errors(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_delete_messages",
        AsyncMock(side_effect=DeleteMessagesError("at least one message_id is required.")),
    )
    message = _message(text="/deletemessages -100123 101 confirm", chat_id=42)

    await commands.cmd_delete_messages(message)

    args, _ = message.answer.await_args
    assert "Could not delete the messages" in args[0]
