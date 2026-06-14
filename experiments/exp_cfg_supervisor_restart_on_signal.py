"""
EXPERIMENT 6: Combine the two prior facts to show the *real* lifecycle hazard.

Facts established:
  - start_polling defaults handle_signals=True -> it installs SIGTERM/SIGINT
    handlers (`_signal_stop_polling`) that REPLACE uvicorn's.
  - On SIGTERM/SIGINT, aiogram's handler just makes start_polling RETURN cleanly
    (it sets the internal stop event).
  - bot/main.py `_run_supervised_polling` treats a clean return from
    start_polling as "start_polling returned unexpectedly" -> mark_degraded ->
    sleep(retry) -> LOOP AGAIN (re-running start_polling, which RE-installs the
    signal handlers).

Net effect on a real deployment: pressing Ctrl+C / sending SIGTERM to the
uvicorn process does NOT shut it down. aiogram catches the signal (uvicorn's
handler was overwritten), polling returns, the supervisor restarts polling,
re-installs the handler, and the process keeps running. The operator must send
the signal repeatedly / SIGKILL.

Here we reproduce the supervisor loop deterministically with a fake start_polling
that mimics "signal caused a clean return", and show it loops forever instead of
exiting.
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
    print("=== Reproducing supervisor behaviour when start_polling returns ===")
    print("(simulating aiogram's signal handler causing a clean return)\n")

    call_count = {"n": 0}

    class FakeDispatcher:
        async def start_polling(self, *a, **k):
            call_count["n"] += 1
            # Mimic aiogram: a SIGTERM made it return cleanly (no exception).
            return None

    # Make retries instant.
    delays = []

    async def fast_sleep(d):
        delays.append(d)
        # allow a few loops then stop the test
        if call_count["n"] >= 4:
            raise asyncio.CancelledError

    fake_dp = FakeDispatcher()

    try:
        await m._run_supervised_polling(
            fake_dp, object(),
            sleep=fast_sleep,
            base_delay_seconds=0.0,
            max_delay_seconds=0.0,
        )
    except asyncio.CancelledError:
        pass

    print(f"  start_polling was (re)invoked {call_count['n']} times after clean returns")
    print(f"  supervisor state after loops: {m.polling_state.snapshot()}")
    looped = call_count["n"] >= 4
    print(f"\n  RESULT: a clean return from start_polling => supervisor RESTARTS it "
          f"(loops) = {looped}")
    print("  Interpretation: when aiogram's signal handler makes polling return on")
    print("  SIGTERM/SIGINT, the supervisor immediately restarts polling (and")
    print("  aiogram re-installs its signal handler). Process does NOT terminate")
    print("  on the first SIGTERM. Status is also flagged 'degraded' (health 503)")
    print("  even though nothing is actually wrong.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
