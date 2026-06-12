import logging
import os
import subprocess
import sys
from pathlib import Path

from aiogram.enums import ParseMode

import bot.main as main

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_bot_uses_default_properties_for_html_parse_mode():
    assert main.bot.default.parse_mode == ParseMode.HTML


def test_app_uses_lifespan_instead_of_deprecated_event_hooks():
    assert not main.app.router.on_startup
    assert not main.app.router.on_shutdown


async def test_lifespan_runs_startup_and_shutdown(monkeypatch):
    calls = []

    async def fake_startup():
        calls.append("startup")

    async def fake_shutdown():
        calls.append("shutdown")

    monkeypatch.setattr(main, "on_startup", fake_startup)
    monkeypatch.setattr(main, "on_shutdown", fake_shutdown)

    async with main.lifespan(main.app):
        assert calls == ["startup"]

    assert calls == ["startup", "shutdown"]


def test_main_bootstrap_applies_log_level_to_structlog_and_stdlib():
    env = os.environ.copy()
    env.update(
        {
            "FREE_CLAUDE_BASE_URL": "http://localhost:8082",
            "FREE_CLAUDE_AUTH_TOKEN": "testtoken",
            "FREE_CLAUDE_DEFAULT_MODEL": "claude-3-haiku-20240307",
            "TELEGRAM_BOT_TOKEN": "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
            "LOG_LEVEL": "ERROR",
        }
    )
    script = """
import logging
import structlog

import bot.main

print(f"ROOT_LEVEL={logging.getLogger().getEffectiveLevel()}")
logger = structlog.get_logger()
logger.warning("below_threshold")
logger.error("at_threshold")
"""

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=PROJECT_ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert f"ROOT_LEVEL={logging.ERROR}" in result.stdout
    assert "below_threshold" not in result.stdout
    assert "at_threshold" in result.stdout
