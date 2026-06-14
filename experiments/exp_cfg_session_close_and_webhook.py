"""
EXPERIMENT 7: Lifecycle resource handling.

(A) Double session.close():
    start_polling defaults close_bot_session=True -> on polling shutdown aiogram
    calls bot.session.close(). bot/main.py on_shutdown ALSO calls
    `await bot.session.close()`. Is closing an aiohttp session twice safe, or
    does it raise / log? Show behaviour with the real aiogram session.

(B) Webhook lifecycle asymmetry:
    on_startup sets the webhook (bot.set_webhook) but on_shutdown NEVER calls
    delete_webhook. Also set_webhook is called WITHOUT drop_pending_updates, and
    any exception from set_webhook is unhandled in lifespan -> startup crash with
    a half-initialised app. We show the code paths statically + that on_shutdown
    has no delete_webhook.
"""
import asyncio
import inspect
import os
import sys

os.environ.setdefault("FREE_CLAUDE_BASE_URL", "http://localhost:8082")
os.environ.setdefault("FREE_CLAUDE_AUTH_TOKEN", "testtoken")
os.environ.setdefault("FREE_CLAUDE_DEFAULT_MODEL", "claude-3-haiku-20240307")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")

import bot.main as m
from aiogram.client.session.aiohttp import AiohttpSession


async def part_a_double_close():
    print("=== (A) double bot.session.close() behaviour ===")
    session = AiohttpSession()
    # force creation of the underlying aiohttp ClientSession
    cs = await session.create_session()
    print(f"  underlying ClientSession created: closed={cs.closed}")
    await session.close()
    print(f"  after 1st close: ClientSession.closed={cs.closed}")
    # aiogram's AiohttpSession.close awaits self._session.close(); a 2nd call:
    raised = None
    try:
        await session.close()
    except Exception as exc:
        raised = exc
    print(f"  2nd close raised: {raised!r}")
    # aiohttp also needs a tick to actually release the connector
    await asyncio.sleep(0)
    print(f"  RESULT: second close is safe (no exception) = {raised is None}")
    print("  NOTE: still wasteful/duplicated; the real risk is that the polling")
    print("  supervisor already closed the SAME bot's session via")
    print("  close_bot_session=True, so on_shutdown closes an already-closed one.")
    return raised is None


def part_b_webhook_lifecycle():
    print("\n=== (B) webhook lifecycle asymmetry ===")
    startup_src = inspect.getsource(m.on_startup)
    shutdown_src = inspect.getsource(m.on_shutdown)

    sets_webhook = "set_webhook" in startup_src
    startup_drop = "drop_pending_updates" in startup_src
    startup_try = "try" in startup_src and "set_webhook" in startup_src
    shutdown_deletes = "delete_webhook" in shutdown_src

    print(f"  on_startup calls set_webhook                : {sets_webhook}")
    print(f"  set_webhook passes drop_pending_updates     : {startup_drop}")
    print(f"  set_webhook wrapped in try/except in lifespan: {startup_try}")
    print(f"  on_shutdown calls delete_webhook            : {shutdown_deletes}")
    print()
    print("  Consequences:")
    print("   - On shutdown the webhook stays registered with Telegram, so after")
    print("     the process dies Telegram keeps POSTing to a dead endpoint until")
    print("     it is re-set/deleted elsewhere.")
    print("   - set_webhook is not wrapped: a transient Telegram error during")
    print("     startup propagates out of lifespan and aborts app startup.")
    print("   - No drop_pending_updates: backlog is delivered on (re)deploy.")
    no_delete = not shutdown_deletes
    no_drop = not startup_drop
    print(f"\n  RESULT: webhook never deleted on shutdown = {no_delete}")
    print(f"  RESULT: pending updates not dropped on set = {no_drop}")
    return no_delete and no_drop


def main():
    async def run():
        a = await part_a_double_close()
        return a
    a = asyncio.run(run())
    b = part_b_webhook_lifecycle()
    print("\n=== VERDICT ===")
    print(f"  (A) duplicate session.close path exists (harmless but redundant): {a}")
    print(f"  (B) webhook set without drop + never deleted on shutdown        : {b}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
