from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import GetWebhookInfo
from aiogram.types import WebhookInfo

from bot.config import Settings
from bot.handlers import commands
from bot.services.webhook_info import fetch_webhook_info, format_webhook_info


def _webhook_info(**overrides) -> WebhookInfo:
    data = {
        "url": "https://bot.example.com/webhook",
        "has_custom_certificate": False,
        "pending_update_count": 3,
        "allowed_updates": ["message", "inline_query"],
    }
    data.update(overrides)
    return WebhookInfo(**data)


def test_admin_chat_ids_parsing_from_string(monkeypatch):
    monkeypatch.setenv("FREE_CLAUDE_BASE_URL", "http://localhost:8082")
    monkeypatch.setenv("FREE_CLAUDE_AUTH_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:ABC")
    monkeypatch.setenv("TELEGRAM_ADMIN_CHAT_IDS", "42, -10042")

    settings = Settings()

    assert settings.admin_chat_ids == [42, -10042]


def test_format_webhook_info_shows_status_and_delivery_errors():
    info = _webhook_info(
        last_error_date=datetime(2026, 5, 25, 18, 0, tzinfo=timezone.utc),
        last_error_message="Bad Gateway <502>",
        max_connections=40,
    )

    rendered = format_webhook_info(info)

    assert "Status: enabled" in rendered
    assert "Pending updates: 3" in rendered
    assert "Allowed updates: message, inline_query" in rendered
    assert "Bad Gateway &lt;502&gt;" in rendered
    assert "2026-05-25T18:00:00+00:00" in rendered


def test_format_webhook_info_handles_polling_mode_defaults():
    info = _webhook_info(url="", pending_update_count=0, allowed_updates=None)

    rendered = format_webhook_info(info)

    assert "Status: disabled" in rendered
    assert "URL: not set" in rendered
    assert "Pending updates: 0" in rendered
    assert "Allowed updates: Telegram default" in rendered
    assert "Last delivery error: none" in rendered


async def test_fetch_webhook_info_uses_typed_aiogram_api():
    info = _webhook_info()
    bot = SimpleNamespace(get_webhook_info=AsyncMock(return_value=info))

    result = await fetch_webhook_info(bot)

    assert result == info
    bot.get_webhook_info.assert_awaited_once_with()


async def test_fetch_webhook_info_reraises_telegram_errors():
    error = TelegramBadRequest(method=GetWebhookInfo(), message="Bad Request: failed")
    bot = SimpleNamespace(get_webhook_info=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await fetch_webhook_info(bot)


def _message(chat_id: int = 42):
    return SimpleNamespace(
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_webhook_info_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "")
    monkeypatch.setattr(commands, "fetch_webhook_info", AsyncMock())
    message = _message()

    await commands.cmd_webhook_info(message)

    commands.fetch_webhook_info.assert_not_awaited()
    message.answer.assert_awaited_once_with("Webhook diagnostics are restricted.")


async def test_cmd_webhook_info_uses_admin_chat_allowlist(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "")
    monkeypatch.setattr(commands, "fetch_webhook_info", AsyncMock(return_value=_webhook_info()))
    message = _message(chat_id=42)

    await commands.cmd_webhook_info(message)

    commands.fetch_webhook_info.assert_awaited_once_with(message.bot)
    message.answer.assert_awaited_once()
    _, kwargs = message.answer.await_args
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_webhook_info_falls_back_to_allowed_chat_allowlist(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(commands, "fetch_webhook_info", AsyncMock(return_value=_webhook_info()))
    message = _message(chat_id=42)

    await commands.cmd_webhook_info(message)

    commands.fetch_webhook_info.assert_awaited_once_with(message.bot)
    message.answer.assert_awaited_once()


async def test_cmd_webhook_info_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(method=GetWebhookInfo(), message="Bad Request: failed")
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "")
    monkeypatch.setattr(commands, "fetch_webhook_info", AsyncMock(side_effect=error))
    message = _message(chat_id=42)

    await commands.cmd_webhook_info(message)

    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Could not fetch webhook diagnostics" in args[0]
