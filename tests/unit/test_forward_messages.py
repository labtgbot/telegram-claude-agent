from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import ForwardMessages

from bot.handlers import commands
from bot.services.forward_messages import perform_forward_messages


async def test_perform_forward_messages_uses_typed_aiogram_api():
    forwarded = [SimpleNamespace(message_id=777), SimpleNamespace(message_id=778)]
    bot = SimpleNamespace(forward_messages=AsyncMock(return_value=forwarded))

    result = await perform_forward_messages(
        bot,
        chat_id=42,
        from_chat_id=-100123,
        message_ids=[55, 56],
        protect_content=True,
    )

    assert result is forwarded
    bot.forward_messages.assert_awaited_once_with(
        chat_id=42,
        from_chat_id=-100123,
        message_ids=[55, 56],
        message_thread_id=None,
        disable_notification=None,
        protect_content=True,
    )


async def test_perform_forward_messages_reraises_telegram_errors():
    error = TelegramBadRequest(
        method=ForwardMessages(chat_id=1, from_chat_id=2, message_ids=[3, 4]),
        message="Bad Request: message to forward not found",
    )
    bot = SimpleNamespace(forward_messages=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_forward_messages(
            bot, chat_id=1, from_chat_id=2, message_ids=[3, 4]
        )


async def test_perform_forward_messages_reraises_forbidden():
    error = TelegramForbiddenError(
        method=ForwardMessages(chat_id=1, from_chat_id=2, message_ids=[3, 4]),
        message="Forbidden: bot is not a member of the chat",
    )
    bot = SimpleNamespace(forward_messages=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_forward_messages(
            bot, chat_id=1, from_chat_id=2, message_ids=[3, 4]
        )


def _message(text: str = "/forwards", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_forwards_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_forward_messages", AsyncMock())
    message = _message(text="/forwards 100 55 56", chat_id=42)

    await commands.cmd_forwards(message)

    commands.perform_forward_messages.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_forwards_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_forward_messages", AsyncMock())
    message = _message(text="/forwards", chat_id=42)

    await commands.cmd_forwards(message)

    commands.perform_forward_messages.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "forwards usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_forwards_shows_usage_on_invalid_ids(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_forward_messages", AsyncMock())
    message = _message(text="/forwards abc 55 56", chat_id=42)

    await commands.cmd_forwards(message)

    commands.perform_forward_messages.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "forwards usage" in args[0]


async def test_cmd_forwards_shows_usage_when_not_increasing(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_forward_messages", AsyncMock())
    message = _message(text="/forwards -100123 56 55", chat_id=42)

    await commands.cmd_forwards(message)

    commands.perform_forward_messages.assert_not_awaited()
    args, _ = message.answer.await_args
    assert "forwards usage" in args[0]


async def test_cmd_forwards_shows_usage_on_duplicate_ids(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_forward_messages", AsyncMock())
    message = _message(text="/forwards -100123 55 55", chat_id=42)

    await commands.cmd_forwards(message)

    commands.perform_forward_messages.assert_not_awaited()
    args, _ = message.answer.await_args
    assert "forwards usage" in args[0]


async def test_cmd_forwards_shows_usage_when_too_many_ids(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_forward_messages", AsyncMock())
    ids = " ".join(str(i) for i in range(1, 102))  # 101 ids, strictly increasing
    message = _message(text=f"/forwards -100123 {ids}", chat_id=42)

    await commands.cmd_forwards(message)

    commands.perform_forward_messages.assert_not_awaited()
    args, _ = message.answer.await_args
    assert "forwards usage" in args[0]


async def test_cmd_forwards_protects_content_by_default(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_forward_messages",
        AsyncMock(return_value=[object(), object()]),
    )
    message = _message(text="/forwards -100123 55 56", chat_id=42)

    await commands.cmd_forwards(message)

    commands.perform_forward_messages.assert_awaited_once_with(
        message.bot,
        chat_id=42,
        from_chat_id=-100123,
        message_ids=[55, 56],
        protect_content=True,
    )
    args, _ = message.answer.await_args
    assert "Forwarded 2 of 2 messages" in args[0]
    assert "protected" in args[0]


async def test_cmd_forwards_reports_skipped_messages(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_forward_messages",
        AsyncMock(return_value=[object()]),
    )
    message = _message(text="/forwards -100123 55 56 57", chat_id=42)

    await commands.cmd_forwards(message)

    args, _ = message.answer.await_args
    assert "Forwarded 1 of 3 messages" in args[0]


async def test_cmd_forwards_share_keyword_disables_protection(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_forward_messages",
        AsyncMock(return_value=[object(), object()]),
    )
    message = _message(text="/forwards -100123 55 56 share", chat_id=42)

    await commands.cmd_forwards(message)

    commands.perform_forward_messages.assert_awaited_once_with(
        message.bot,
        chat_id=42,
        from_chat_id=-100123,
        message_ids=[55, 56],
        protect_content=False,
    )
    args, _ = message.answer.await_args
    assert "shareable" in args[0]


async def test_cmd_forwards_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(
        method=ForwardMessages(chat_id=1, from_chat_id=2, message_ids=[3, 4]),
        message="Bad Request: message to forward not found",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_forward_messages", AsyncMock(side_effect=error)
    )
    message = _message(text="/forwards -100123 55 56", chat_id=42)

    await commands.cmd_forwards(message)

    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Could not forward the messages" in args[0]
