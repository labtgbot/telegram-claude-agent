from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import DeleteWebhook

from bot.handlers import commands
from bot.services.webhook_delete import delete_webhook


async def test_delete_webhook_uses_typed_aiogram_api_without_dropping_updates():
    bot = SimpleNamespace(delete_webhook=AsyncMock(return_value=True))

    result = await delete_webhook(bot)

    assert result is True
    bot.delete_webhook.assert_awaited_once_with(drop_pending_updates=False)


async def test_delete_webhook_can_drop_pending_updates():
    bot = SimpleNamespace(delete_webhook=AsyncMock(return_value=True))

    result = await delete_webhook(bot, drop_pending_updates=True)

    assert result is True
    bot.delete_webhook.assert_awaited_once_with(drop_pending_updates=True)


async def test_delete_webhook_reraises_telegram_errors():
    error = TelegramBadRequest(
        method=DeleteWebhook(drop_pending_updates=True),
        message="Bad Request: failed",
    )
    bot = SimpleNamespace(delete_webhook=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await delete_webhook(bot, drop_pending_updates=True)


def _message(chat_id: int = 42, text: str = "/deletewebhook"):
    return SimpleNamespace(
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        text=text,
        answer=AsyncMock(),
    )


async def test_cmd_delete_webhook_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "")
    monkeypatch.setattr(commands, "delete_webhook", AsyncMock())
    message = _message()

    await commands.cmd_delete_webhook(message)

    commands.delete_webhook.assert_not_awaited()
    message.answer.assert_awaited_once_with("Webhook lifecycle operations are restricted.")


async def test_cmd_delete_webhook_uses_admin_chat_allowlist(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "")
    monkeypatch.setattr(commands, "delete_webhook", AsyncMock(return_value=True))
    message = _message(chat_id=42)

    await commands.cmd_delete_webhook(message)

    commands.delete_webhook.assert_awaited_once_with(
        message.bot,
        drop_pending_updates=False,
    )
    message.answer.assert_awaited_once_with("Webhook deleted. Pending updates were kept.")


async def test_cmd_delete_webhook_parses_drop_pending_updates(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "")
    monkeypatch.setattr(commands, "delete_webhook", AsyncMock(return_value=True))
    message = _message(chat_id=42, text="/deletewebhook drop_pending_updates=true")

    await commands.cmd_delete_webhook(message)

    commands.delete_webhook.assert_awaited_once_with(
        message.bot,
        drop_pending_updates=True,
    )
    message.answer.assert_awaited_once_with("Webhook deleted. Pending updates were dropped.")


async def test_cmd_delete_webhook_rejects_invalid_drop_argument(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "")
    monkeypatch.setattr(commands, "delete_webhook", AsyncMock(return_value=True))
    message = _message(chat_id=42, text="/deletewebhook maybe")

    await commands.cmd_delete_webhook(message)

    commands.delete_webhook.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "Usage: /deletewebhook [drop_pending_updates=true|false]"
    )


async def test_cmd_delete_webhook_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(
        method=DeleteWebhook(drop_pending_updates=False),
        message="Bad Request: failed",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "")
    monkeypatch.setattr(commands, "delete_webhook", AsyncMock(side_effect=error))
    message = _message(chat_id=42)

    await commands.cmd_delete_webhook(message)

    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Could not delete webhook" in args[0]
