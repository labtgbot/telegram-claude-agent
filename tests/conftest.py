import os

# Provide safe defaults for required settings before bot.config imports.
os.environ.setdefault("FREE_CLAUDE_BASE_URL", "http://localhost:8082")
os.environ.setdefault("FREE_CLAUDE_AUTH_TOKEN", "testtoken")
os.environ.setdefault("FREE_CLAUDE_DEFAULT_MODEL", "claude-3-haiku-20240307")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")

import pytest  # noqa: E402

from bot.config import Settings  # noqa: E402
from bot.utils.storage import MemoryStorage  # noqa: E402


@pytest.fixture
def test_settings():
    return Settings(
        free_claude_base_url="http://localhost:8082",
        free_claude_auth_token="testtoken",
        free_claude_default_model="claude-3-haiku-20240307",
        telegram_bot_token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
    )


@pytest.fixture
def storage():
    return MemoryStorage()
