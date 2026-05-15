import pytest
from bot.config import Settings
from bot.utils.storage import MemoryStorage
from bot.services.claude_proxy import ClaudeProxyClient

@pytest.fixture
def test_settings():
    return Settings(
        free_claude_base_url="http://localhost:8082",
        free_claude_auth_token="testtoken",
        telegram_bot_token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
    )

@pytest.fixture
def storage():
    return MemoryStorage()