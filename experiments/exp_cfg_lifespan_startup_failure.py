"""
EXPERIMENT 8: lifespan startup-failure handling.

bot/main.py lifespan:

    async def lifespan(_):
        await on_startup()
        try:
            yield
        finally:
            await on_shutdown()

NOTE the `await on_startup()` is OUTSIDE the try. If on_startup raises (e.g.
_ensure_bot_identity_cached fails on a bad token, or set_webhook errors), the
`finally: on_shutdown()` does NOT run -> any partially-created resources
(e.g. a polling_task already created earlier in on_startup, or the bot session)
are NOT cleaned up.

We reproduce: monkeypatch on_startup to (a) create a polling task, then (b)
raise — and show the lifespan propagates the error WITHOUT running on_shutdown,
leaving the task dangling.
"""
import asyncio
import os
import sys

os.environ.setdefault("FREE_CLAUDE_BASE_URL", "http://localhost:8082")
os.environ.setdefault("FREE_CLAUDE_AUTH_TOKEN", "testtoken")
os.environ.setdefault("FREE_CLAUDE_DEFAULT_MODEL", "claude-3-haiku-20240307")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")

import bot.main as m


async def main():
    print("=== lifespan: does on_shutdown run if on_startup raises? ===\n")

    shutdown_ran = {"v": False}
    leaked_task = {"task": None}

    async def fake_on_startup():
        # Simulate the real on_startup having already created the polling task
        # before a later await fails.
        async def _spin():
            try:
                await asyncio.sleep(3600)
            except asyncio.CancelledError:
                raise
        t = asyncio.create_task(_spin())
        m.polling_task = t
        leaked_task["task"] = t
        # Now a later startup step fails (e.g. set_webhook / get_me):
        raise RuntimeError("startup step failed (e.g. Telegram unreachable)")

    async def fake_on_shutdown():
        shutdown_ran["v"] = True
        if m.polling_task:
            m.polling_task.cancel()

    m.on_startup = fake_on_startup
    m.on_shutdown = fake_on_shutdown

    raised = None
    try:
        async with m.lifespan(m.app):
            pass
    except Exception as exc:
        raised = exc

    print(f"  lifespan raised: {raised!r}")
    print(f"  on_shutdown ran: {shutdown_ran['v']}")
    t = leaked_task["task"]
    print(f"  polling task created during startup: {t!r}")
    print(f"  polling task cancelled/done after failure: "
          f"{t.cancelled() or t.done() if t else 'n/a'}")

    dangling = (raised is not None) and (not shutdown_ran["v"]) and t is not None and not t.done()
    print(f"\n  RESULT: startup failure leaves polling task DANGLING (no cleanup) = {dangling}")
    print("  ROOT CAUSE: `await on_startup()` is outside the try/finally, so the")
    print("  finally:on_shutdown() cleanup never runs when on_startup raises.")

    # cleanup our leaked task so the script exits cleanly
    if t and not t.done():
        t.cancel()
        try:
            await t
        except asyncio.CancelledError:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
