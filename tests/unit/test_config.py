import pytest

from bot.config import Settings


def _base_env(monkeypatch):
    monkeypatch.setenv("FREE_CLAUDE_BASE_URL", "http://localhost:8082")
    monkeypatch.setenv("FREE_CLAUDE_AUTH_TOKEN", "token")
    monkeypatch.setenv("FREE_CLAUDE_DEFAULT_MODEL", "claude-3-haiku-20240307")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:ABC")


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

def test_bot_short_description_settings(monkeypatch):
    monkeypatch.setenv("FREE_CLAUDE_BASE_URL", "http://localhost:8082")
    monkeypatch.setenv("FREE_CLAUDE_AUTH_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:ABC")
    monkeypatch.setenv("TELEGRAM_BOT_SHORT_DESCRIPTION", "Claude agent")
    monkeypatch.setenv("TELEGRAM_BOT_SHORT_DESCRIPTION_LANGUAGE_CODE", "ru")
    settings = Settings()
    assert settings.telegram_bot_short_description == "Claude agent"
    assert settings.telegram_bot_short_description_language_code == "ru"

def test_bot_default_administrator_rights_settings(monkeypatch):
    monkeypatch.setenv("FREE_CLAUDE_BASE_URL", "http://localhost:8082")
    monkeypatch.setenv("FREE_CLAUDE_AUTH_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:ABC")
    monkeypatch.setenv("TELEGRAM_BOT_DEFAULT_ADMINISTRATOR_RIGHTS", "moderator")
    monkeypatch.setenv("TELEGRAM_BOT_DEFAULT_ADMINISTRATOR_RIGHTS_FOR_CHANNELS", "false")
    settings = Settings()
    assert settings.telegram_bot_default_administrator_rights == "moderator"
    assert settings.telegram_bot_default_administrator_rights_for_channels is False


def test_webhook_mode_requires_secret_token(monkeypatch):
    _base_env(monkeypatch)
    monkeypatch.setenv("TELEGRAM_WEBHOOK_URL", "https://example.com/webhook")
    monkeypatch.delenv("API_SECRET_TOKEN", raising=False)
    with pytest.raises(ValueError, match="API_SECRET_TOKEN is required"):
        Settings()


def test_webhook_mode_rejects_empty_secret_token(monkeypatch):
    _base_env(monkeypatch)
    monkeypatch.setenv("TELEGRAM_WEBHOOK_URL", "https://example.com/webhook")
    monkeypatch.setenv("API_SECRET_TOKEN", "")
    with pytest.raises(ValueError, match="API_SECRET_TOKEN is required"):
        Settings()


def test_webhook_mode_accepts_valid_secret_token(monkeypatch):
    _base_env(monkeypatch)
    monkeypatch.setenv("TELEGRAM_WEBHOOK_URL", "https://example.com/webhook")
    monkeypatch.setenv("API_SECRET_TOKEN", "a-Strong_Secret_123456")
    settings = Settings()
    assert settings.api_secret_token == "a-Strong_Secret_123456"


def test_polling_mode_allows_missing_secret_token(monkeypatch):
    _base_env(monkeypatch)
    monkeypatch.delenv("TELEGRAM_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("API_SECRET_TOKEN", raising=False)
    settings = Settings()
    assert settings.api_secret_token is None


def test_secret_token_rejects_invalid_characters(monkeypatch):
    _base_env(monkeypatch)
    monkeypatch.setenv("API_SECRET_TOKEN", "invalid token with spaces!")
    with pytest.raises(ValueError, match="A-Z, a-z, 0-9"):
        Settings()


def test_secret_token_rejects_too_short(monkeypatch):
    _base_env(monkeypatch)
    monkeypatch.setenv("API_SECRET_TOKEN", "short")
    with pytest.raises(ValueError, match="at least"):
        Settings()


def test_secret_token_too_long_rejected(monkeypatch):
    _base_env(monkeypatch)
    monkeypatch.setenv("API_SECRET_TOKEN", "a" * 257)
    with pytest.raises(ValueError, match="1-256 characters"):
        Settings()
