import logging
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.enums import ParseMode

import bot.main as main

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_bot_uses_default_properties_for_html_parse_mode():
    assert main.bot.default.parse_mode == ParseMode.HTML


def _registered_middleware_types(observer):
    return {type(mw) for mw in observer.middleware}


def test_middlewares_registered_on_concrete_event_observers():
    """Regression for #409.

    Middlewares attached to ``dp.update`` receive the raw ``Update`` object and
    never the concrete event, so their ``isinstance`` branches never fire. They
    must be registered on the message/callback_query/inline_query observers.
    """
    from bot.middlewares.logging import LoggingMiddleware
    from bot.middlewares.rate_limit import RateLimitMiddleware

    for observer in (main.dp.message, main.dp.callback_query, main.dp.inline_query):
        registered = _registered_middleware_types(observer)
        assert LoggingMiddleware in registered
        assert RateLimitMiddleware in registered

    update_middleware = _registered_middleware_types(main.dp.update)
    assert LoggingMiddleware not in update_middleware
    assert RateLimitMiddleware not in update_middleware


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


async def test_lifespan_runs_shutdown_when_startup_fails(monkeypatch):
    calls = []

    async def fake_startup():
        calls.append("startup")
        raise RuntimeError("startup failed after partial initialization")

    async def fake_shutdown():
        calls.append("shutdown")

    monkeypatch.setattr(main, "on_startup", fake_startup)
    monkeypatch.setattr(main, "on_shutdown", fake_shutdown)

    with pytest.raises(RuntimeError, match="startup failed after partial initialization"):
        async with main.lifespan(main.app):
            raise AssertionError("lifespan body should not run when startup fails")

    assert calls == ["startup", "shutdown"]


async def test_on_startup_sets_webhook_and_drops_pending_updates(monkeypatch):
    async def noop(*args, **kwargs):
        return None

    for name in (
        "_ensure_bot_identity_cached",
        "sync_configured_bot_name",
        "audit_configured_bot_name",
        "sync_configured_bot_short_description",
        "audit_configured_bot_short_description",
        "sync_configured_bot_description",
        "audit_configured_bot_description",
        "sync_configured_my_default_administrator_rights",
        "audit_configured_my_default_administrator_rights",
    ):
        monkeypatch.setattr(main, name, noop)

    webhook_url = "https://example.com/webhook"
    secret_token = "a-Strong_Secret_123456"
    bot = SimpleNamespace(set_webhook=AsyncMock())
    monkeypatch.setattr(main, "bot", bot)
    monkeypatch.setattr(main.settings, "telegram_webhook_url", webhook_url)
    monkeypatch.setattr(main.settings, "api_secret_token", secret_token)

    await main.on_startup()

    bot.set_webhook.assert_awaited_once_with(
        url=webhook_url,
        secret_token=secret_token,
        drop_pending_updates=True,
    )
    assert main.polling_task is None
    assert main.polling_state.snapshot()["mode"] == "webhook"


async def test_on_shutdown_deletes_configured_webhook_before_closing_session(monkeypatch):
    events = []

    async def delete_webhook(*, drop_pending_updates):
        events.append(("delete_webhook", drop_pending_updates))
        return True

    async def close_session():
        events.append(("close_session", None))

    bot = SimpleNamespace(
        delete_webhook=AsyncMock(side_effect=delete_webhook),
        session=SimpleNamespace(close=AsyncMock(side_effect=close_session)),
    )
    monkeypatch.setattr(main, "bot", bot)
    monkeypatch.setattr(main.settings, "telegram_webhook_url", "https://example.com/webhook")
    monkeypatch.setattr(main, "polling_task", None)

    await main.on_shutdown()

    bot.delete_webhook.assert_awaited_once_with(drop_pending_updates=False)
    bot.session.close.assert_awaited_once_with()
    assert events == [("delete_webhook", False), ("close_session", None)]


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
