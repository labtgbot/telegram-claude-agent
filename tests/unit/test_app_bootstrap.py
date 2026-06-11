from aiogram.enums import ParseMode

import bot.main as main


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
