from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import CopyMessages

from bot.handlers import commands
from bot.services.copy_messages import perform_copy_messages


async def test_perform_copy_messages_uses_typed_aiogram_api():
    copied = [SimpleNamespace(message_id=777), SimpleNamespace(message_id=778)]
    bot = SimpleNamespace(copy_messages=AsyncMock(return_value=copied))

    result = await perform_copy_messages(
        bot,
        chat_id=42,
        from_chat_id=-100123,
        message_ids=[55, 56],
        protect_content=True,
        remove_caption=True,
    )

    assert result is copied
    bot.copy_messages.assert_awaited_once_with(
        chat_id=42,
        from_chat_id=-100123,
        message_ids=[55, 56],
        message_thread_id=None,
        disable_notification=None,
        protect_content=True,
        remove_caption=True,
    )


async def test_perform_copy_messages_reraises_telegram_errors():
    error = TelegramBadRequest(
        method=CopyMessages(chat_id=1, from_chat_id=2, message_ids=[3, 4]),
        message="Bad Request: message to copy not found",
    )
    bot = SimpleNamespace(copy_messages=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_copy_messages(
            bot, chat_id=1, from_chat_id=2, message_ids=[3, 4]
        )


async def test_perform_copy_messages_reraises_forbidden():
    error = TelegramForbiddenError(
        method=CopyMessages(chat_id=1, from_chat_id=2, message_ids=[3, 4]),
        message="Forbidden: bot is not a member of the chat",
    )
    bot = SimpleNamespace(copy_messages=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_copy_messages(
            bot, chat_id=1, from_chat_id=2, message_ids=[3, 4]
        )


def _message(text: str = "/copies", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_copies_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_copy_messages", AsyncMock())
    message = _message(text="/copies 100 55 56", chat_id=42)

    await commands.cmd_copies(message)

    commands.perform_copy_messages.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_copies_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_copy_messages", AsyncMock())
    message = _message(text="/copies", chat_id=42)

    await commands.cmd_copies(message)

    commands.perform_copy_messages.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "copies usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_copies_shows_usage_on_invalid_ids(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_copy_messages", AsyncMock())
    message = _message(text="/copies abc 55 56", chat_id=42)

    await commands.cmd_copies(message)

    commands.perform_copy_messages.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "copies usage" in args[0]


async def test_cmd_copies_shows_usage_when_not_increasing(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_copy_messages", AsyncMock())
    message = _message(text="/copies -100123 56 55", chat_id=42)

    await commands.cmd_copies(message)

    commands.perform_copy_messages.assert_not_awaited()
    args, _ = message.answer.await_args
    assert "copies usage" in args[0]


async def test_cmd_copies_shows_usage_on_duplicate_ids(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_copy_messages", AsyncMock())
    message = _message(text="/copies -100123 55 55", chat_id=42)

    await commands.cmd_copies(message)

    commands.perform_copy_messages.assert_not_awaited()
    args, _ = message.answer.await_args
    assert "copies usage" in args[0]


async def test_cmd_copies_shows_usage_when_too_many_ids(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_copy_messages", AsyncMock())
    ids = " ".join(str(i) for i in range(1, 102))  # 101 ids, strictly increasing
    message = _message(text=f"/copies -100123 {ids}", chat_id=42)

    await commands.cmd_copies(message)

    commands.perform_copy_messages.assert_not_awaited()
    args, _ = message.answer.await_args
    assert "copies usage" in args[0]


async def test_cmd_copies_protects_content_by_default(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_copy_messages",
        AsyncMock(return_value=[object(), object()]),
    )
    message = _message(text="/copies -100123 55 56", chat_id=42)

    await commands.cmd_copies(message)

    commands.perform_copy_messages.assert_awaited_once_with(
        message.bot,
        chat_id=42,
        from_chat_id=-100123,
        message_ids=[55, 56],
        protect_content=True,
        remove_caption=False,
    )
    args, _ = message.answer.await_args
    assert "Copied 2 of 2 messages" in args[0]
    assert "protected" in args[0]
    assert "with captions" in args[0]


async def test_cmd_copies_reports_skipped_messages(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_copy_messages",
        AsyncMock(return_value=[object()]),
    )
    message = _message(text="/copies -100123 55 56 57", chat_id=42)

    await commands.cmd_copies(message)

    args, _ = message.answer.await_args
    assert "Copied 1 of 3 messages" in args[0]


async def test_cmd_copies_share_keyword_disables_protection(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_copy_messages",
        AsyncMock(return_value=[object(), object()]),
    )
    message = _message(text="/copies -100123 55 56 share", chat_id=42)

    await commands.cmd_copies(message)

    commands.perform_copy_messages.assert_awaited_once_with(
        message.bot,
        chat_id=42,
        from_chat_id=-100123,
        message_ids=[55, 56],
        protect_content=False,
        remove_caption=False,
    )
    args, _ = message.answer.await_args
    assert "shareable" in args[0]


async def test_cmd_copies_nocaption_keyword_removes_captions(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_copy_messages",
        AsyncMock(return_value=[object(), object()]),
    )
    message = _message(text="/copies -100123 55 56 nocaption", chat_id=42)

    await commands.cmd_copies(message)

    commands.perform_copy_messages.assert_awaited_once_with(
        message.bot,
        chat_id=42,
        from_chat_id=-100123,
        message_ids=[55, 56],
        protect_content=True,
        remove_caption=True,
    )
    args, _ = message.answer.await_args
    assert "without captions" in args[0]


async def test_cmd_copies_combines_share_and_nocaption(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_copy_messages",
        AsyncMock(return_value=[object(), object()]),
    )
    message = _message(text="/copies -100123 55 56 share nocaption", chat_id=42)

    await commands.cmd_copies(message)

    commands.perform_copy_messages.assert_awaited_once_with(
        message.bot,
        chat_id=42,
        from_chat_id=-100123,
        message_ids=[55, 56],
        protect_content=False,
        remove_caption=True,
    )
    args, _ = message.answer.await_args
    assert "shareable" in args[0]
    assert "without captions" in args[0]


async def test_cmd_copies_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(
        method=CopyMessages(chat_id=1, from_chat_id=2, message_ids=[3, 4]),
        message="Bad Request: message to copy not found",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_copy_messages", AsyncMock(side_effect=error)
    )
    message = _message(text="/copies -100123 55 56", chat_id=42)

    await commands.cmd_copies(message)

    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Could not copy the messages" in args[0]
