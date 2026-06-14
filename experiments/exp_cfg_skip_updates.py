"""
EXPERIMENT 4: bot/main.py line 173 calls

    await dispatcher.start_polling(telegram_bot, skip_updates=True)

But aiogram 3.x `Dispatcher.start_polling` has NO `skip_updates` parameter.
It only has `**kwargs`, which aiogram treats as *contextual data* merged into
`workflow_data` and injected into every handler call.

Consequences to prove:
  (1) `skip_updates=True` is NOT a real polling option -> pending updates are
      NOT dropped (the developer intent is silently ignored). The actual way to
      drop the backlog in aiogram 3 is `drop_pending_updates=True` on
      delete_webhook/get_updates, which start_polling does itself only via
      delete_webhook(drop_pending_updates=...)? Show it is ignored.
  (2) The bogus kwarg leaks into handler `workflow_data` as a key literally
      named "skip_updates".

We avoid real network by stubbing the polling internals and capturing the
workflow_data that aiogram would build.
"""
import asyncio
import inspect
import os
import sys

os.environ.setdefault("FREE_CLAUDE_BASE_URL", "http://localhost:8082")
os.environ.setdefault("FREE_CLAUDE_AUTH_TOKEN", "testtoken")
os.environ.setdefault("FREE_CLAUDE_DEFAULT_MODEL", "claude-3-haiku-20240307")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")

from aiogram import Dispatcher
from aiogram.methods import GetUpdates  # noqa: F401


def part1_no_such_param():
    print("=== (1) start_polling has no real 'skip_updates' option ===")
    sig = inspect.signature(Dispatcher.start_polling)
    has_skip = "skip_updates" in sig.parameters
    accepts_kwargs = any(p.kind == p.VAR_KEYWORD for p in sig.parameters.values())
    print(f"  'skip_updates' explicit param : {has_skip}")
    print(f"  swallowed by **kwargs          : {accepts_kwargs}")
    print("  -> 'skip_updates=True' is treated as CONTEXTUAL DATA, not an option")
    return (not has_skip) and accepts_kwargs


def part2_leaks_into_workflow_data():
    print("\n=== (2) the bogus kwarg leaks into handler workflow_data ===")
    dp = Dispatcher()

    captured = {}

    # Patch the two heavy coroutines so start_polling returns quickly while we
    # capture the workflow_data aiogram assembles from our kwargs.
    async def fake_polling(*, bot, **workflow_data):
        captured.update(workflow_data)
        return None

    async def fake_emit_startup(*a, **k):
        # workflow_data is also passed here; capture the kwargs too
        captured.setdefault("_startup_kwargs", dict(k))
        return None

    async def fake_emit_shutdown(*a, **k):
        return None

    dp._polling = fake_polling            # type: ignore
    dp.emit_startup = fake_emit_startup   # type: ignore
    dp.emit_shutdown = fake_emit_shutdown # type: ignore

    class FakeSession:
        async def close(self):
            return None

    class FakeBot:
        id = 1
        session = FakeSession()

    async def run():
        # Mirror EXACTLY what bot/main.py does:
        await dp.start_polling(FakeBot(), skip_updates=True, handle_signals=False)

    asyncio.run(run())

    leaked = "skip_updates" in captured
    print(f"  workflow_data keys captured by _polling: "
          f"{sorted(k for k in captured if not k.startswith('_'))}")
    print(f"  'skip_updates' injected into handler contextual data: {leaked}")
    print(f"  value = {captured.get('skip_updates')!r}")
    return leaked


def main():
    r1 = part1_no_such_param()
    r2 = part2_leaks_into_workflow_data()
    print("\n=== VERDICT ===")
    print(f"  skip_updates is NOT a polling option (ignored)      : {r1}")
    print(f"  skip_updates leaks into every handler's kwargs      : {r2}")
    if r1 and r2:
        print("  CONFIRMED: skip_updates=True is silently ignored as a polling")
        print("  control AND pollutes handler contextual data. Pending-update")
        print("  backlog is NOT skipped on (re)start as the code intends.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
