"""
EXPERIMENT 5: bot/main.py calls

    await dispatcher.start_polling(telegram_bot, skip_updates=True)

without passing handle_signals=False. In aiogram 3.x, start_polling defaults to
handle_signals=True, which does:

    loop.add_signal_handler(SIGTERM, self._signal_stop_polling, SIGTERM)
    loop.add_signal_handler(SIGINT,  self._signal_stop_polling, SIGINT)

But this bot runs polling as a background asyncio task INSIDE a uvicorn/FastAPI
process. uvicorn installs its OWN SIGTERM/SIGINT handlers to drive graceful
shutdown (run lifespan shutdown, close connections). asyncio's
loop.add_signal_handler REPLACES any previously registered handler for that
signal. So aiogram's start_polling silently overwrites uvicorn's signal
handlers.

We prove:
  (1) loop.add_signal_handler overwrites a previously-installed handler for the
      same signal (only one handler per signal; last writer wins).
  (2) Running start_polling exactly as main.py does (handle_signals defaulted)
      replaces a pre-installed SIGTERM handler with aiogram's
      _signal_stop_polling.

Impact: SIGTERM (e.g. `docker stop`, k8s pod termination) no longer triggers
uvicorn's graceful shutdown path through the signal it expects; instead aiogram
just stops polling. FastAPI lifespan shutdown (on_shutdown) may not run the way
the operator expects, and shutdown semantics become order/implementation
dependent.
"""
import asyncio
import os
import signal
import sys

os.environ.setdefault("FREE_CLAUDE_BASE_URL", "http://localhost:8082")
os.environ.setdefault("FREE_CLAUDE_AUTH_TOKEN", "testtoken")
os.environ.setdefault("FREE_CLAUDE_DEFAULT_MODEL", "claude-3-haiku-20240307")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")

from aiogram import Dispatcher


def _current_sigterm_handler(loop):
    # There is no public getter; asyncio stores handles in loop._signal_handlers
    handlers = getattr(loop, "_signal_handlers", {})
    h = handlers.get(signal.SIGTERM)
    return h


async def part1_overwrite_semantics():
    print("=== (1) loop.add_signal_handler replaces prior handler (last wins) ===")
    loop = asyncio.get_running_loop()

    calls = []

    def uvicorn_like_handler():
        calls.append("uvicorn")

    def other_handler():
        calls.append("other")

    loop.add_signal_handler(signal.SIGTERM, uvicorn_like_handler)
    h1 = _current_sigterm_handler(loop)
    loop.add_signal_handler(signal.SIGTERM, other_handler)
    h2 = _current_sigterm_handler(loop)

    print(f"  handler after 1st register callback = {getattr(h1, '_callback', h1)}")
    print(f"  handler after 2nd register callback = {getattr(h2, '_callback', h2)}")
    replaced = h1 is not h2
    print(f"  RESULT: second registration replaced the first = {replaced}")
    loop.remove_signal_handler(signal.SIGTERM)
    return replaced


async def part2_aiogram_clobbers():
    print("\n=== (2) start_polling (handle_signals defaulted) clobbers SIGTERM ===")
    loop = asyncio.get_running_loop()

    sentinel = []

    def preinstalled_uvicorn_handler():
        sentinel.append("uvicorn-graceful-shutdown")

    # Simulate uvicorn having installed its graceful-shutdown signal handler.
    loop.add_signal_handler(signal.SIGTERM, preinstalled_uvicorn_handler)
    before = _current_sigterm_handler(loop)
    before_cb = getattr(before, "_callback", None)
    print(f"  SIGTERM handler BEFORE start_polling = {getattr(before_cb, '__name__', before_cb)}")

    dp = Dispatcher()

    # Stub heavy internals so start_polling returns immediately after it has
    # installed its signal handlers (it installs them before _polling runs).
    async def fake_polling(*, bot, **wd):
        return None

    async def fake_emit_startup(*a, **k):
        return None

    async def fake_emit_shutdown(*a, **k):
        return None

    dp._polling = fake_polling             # type: ignore
    dp.emit_startup = fake_emit_startup    # type: ignore
    dp.emit_shutdown = fake_emit_shutdown  # type: ignore

    class FakeSession:
        async def close(self):
            return None

    class FakeBot:
        id = 1
        session = FakeSession()

    # EXACTLY as bot/main.py: no handle_signals kwarg => defaults to True.
    # (We keep skip_updates to mirror the real call faithfully.)
    await dp.start_polling(FakeBot(), skip_updates=True)

    after = _current_sigterm_handler(loop)
    after_cb = getattr(after, "_callback", None)
    after_name = getattr(after_cb, "__name__", str(after_cb))
    # aiogram binds self._signal_stop_polling; it's a bound method
    after_qual = getattr(after_cb, "__qualname__", after_name)
    print(f"  SIGTERM handler AFTER  start_polling = {after_qual}")

    clobbered = after is not before
    is_aiogram = "_signal_stop_polling" in str(after_qual)
    print(f"  RESULT: uvicorn's SIGTERM handler was overwritten = {clobbered}")
    print(f"  RESULT: it is now aiogram's _signal_stop_polling   = {is_aiogram}")

    loop.remove_signal_handler(signal.SIGTERM)
    try:
        loop.remove_signal_handler(signal.SIGINT)
    except Exception:
        pass
    return clobbered and is_aiogram


def main():
    async def run():
        r1 = await part1_overwrite_semantics()
        r2 = await part2_aiogram_clobbers()
        return r1, r2

    r1, r2 = asyncio.run(run())
    print("\n=== VERDICT ===")
    print(f"  add_signal_handler overwrites prior handler : {r1}")
    print(f"  start_polling clobbers host SIGTERM handler : {r2}")
    if r1 and r2:
        print("  CONFIRMED: polling started without handle_signals=False hijacks")
        print("  SIGTERM/SIGINT from uvicorn, undermining graceful shutdown.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
