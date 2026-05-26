import os
from bot.config import Settings

def test_chat_ids_parsing_from_string(monkeypatch):
    monkeypatch.setenv("FREE_CLAUDE_BASE_URL", "http://localhost:8082")
    monkeypatch.setenv("FREE_CLAUDE_AUTH_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:ABC")
    monkeypatch.setenv("TELEGRAM_ALLOWED_CHAT_IDS", "12345, -1001234567890")
    settings = Settings()
    assert settings.allowed_chat_ids == [12345, -1001234567890]

def test_chat_ids_empty_string(monkeypatch):
    monkeypatch.setenv("FREE_CLAUDE_BASE_URL", "http://localhost:8082")
    monkeypatch.setenv("FREE_CLAUDE_AUTH_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:ABC")
    monkeypatch.setenv("TELEGRAM_ALLOWED_CHAT_IDS", "")
    settings = Settings()
    assert settings.allowed_chat_ids == []

def test_chat_ids_not_set(monkeypatch):
    monkeypatch.setenv("FREE_CLAUDE_BASE_URL", "http://localhost:8082")
    monkeypatch.setenv("FREE_CLAUDE_AUTH_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:ABC")
    monkeypatch.delenv("TELEGRAM_ALLOWED_CHAT_IDS", raising=False)
    settings = Settings()
    assert settings.allowed_chat_ids == []

def test_boolean_parsing(monkeypatch):
    monkeypatch.setenv("FREE_CLAUDE_BASE_URL", "http://localhost:8082")
    monkeypatch.setenv("FREE_CLAUDE_AUTH_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:ABC")
    monkeypatch.setenv("FREE_CLAUDE_STREAMING_ENABLED", "false")
    monkeypatch.setenv("TELEGRAM_GUEST_MODE_ENABLED", "False")
    settings = Settings()
    assert settings.free_claude_streaming_enabled is False
    assert settings.telegram_guest_mode_enabled is False

def test_bot_name_settings(monkeypatch):
    monkeypatch.setenv("FREE_CLAUDE_BASE_URL", "http://localhost:8082")
    monkeypatch.setenv("FREE_CLAUDE_AUTH_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:ABC")
    monkeypatch.setenv("TELEGRAM_BOT_NAME", "Claude Agent")
    monkeypatch.setenv("TELEGRAM_BOT_NAME_LANGUAGE_CODE", "ru")
    settings = Settings()
    assert settings.telegram_bot_name == "Claude Agent"
    assert settings.telegram_bot_name_language_code == "ru"

def test_bot_description_settings(monkeypatch):
    monkeypatch.setenv("FREE_CLAUDE_BASE_URL", "http://localhost:8082")
    monkeypatch.setenv("FREE_CLAUDE_AUTH_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:ABC")
    monkeypatch.setenv("TELEGRAM_BOT_DESCRIPTION", "Claude agent for Telegram")
    monkeypatch.setenv("TELEGRAM_BOT_DESCRIPTION_LANGUAGE_CODE", "ru")
    settings = Settings()
    assert settings.telegram_bot_description == "Claude agent for Telegram"
    assert settings.telegram_bot_description_language_code == "ru"
