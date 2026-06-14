"""
EXPERIMENT: whisper model lazy-cache in _transcribe_sync is not thread-safe.

transcribe_voice runs _transcribe_sync via loop.run_in_executor(None, ...), i.e.
on the default ThreadPoolExecutor (multiple worker threads). The lazy cache is:

    if not hasattr(_transcribe_sync, "model"):
        _transcribe_sync.model = whisper.load_model("base")   # expensive

This check-then-set has no lock. Two voice messages that arrive before the
model is cached run on two different threads, both observe hasattr()==False, and
both call whisper.load_model("base") concurrently -> double load of a large
model (CPU + RAM spike, duplicated work), and a torn write window.

We can't import whisper here, so we reproduce the EXACT cache pattern with a
stand-in `load_model` that sleeps (simulating the heavy load) and counts how
many times it is actually invoked when N threads hit a cold cache together.
"""
import sys
import threading
import time

sys.path.insert(0, ".")

load_calls = []
_marker = threading.Event()


def _heavy_load_model(name):
    # Simulate an expensive load so concurrent threads overlap.
    load_calls.append(name)
    time.sleep(0.2)
    return f"model-{name}-{len(load_calls)}"


class _Fn:
    """Stand-in object mimicking the function-attribute cache on _transcribe_sync."""


fn = _Fn()


def transcribe_like():
    # EXACT pattern from bot/utils/media.py _transcribe_sync:
    if not hasattr(fn, "model"):
        fn.model = _heavy_load_model("base")
    return fn.model


N = 8
threads = [threading.Thread(target=transcribe_like) for _ in range(N)]
start = time.monotonic()
for t in threads:
    t.start()
for t in threads:
    t.join()
elapsed = time.monotonic() - start

print(f"threads={N} | whisper.load_model invoked {len(load_calls)} time(s)")
print(f"elapsed={elapsed:.2f}s (each load simulated at 0.2s)")

print("\n=== RESULT ===")
if len(load_calls) > 1:
    print(
        f"BUG CONFIRMED: the unlocked check-then-set cache caused "
        f"{len(load_calls)} concurrent whisper.load_model('base') calls on a cold "
        "cache. In production this duplicates a ~hundreds-of-MB model load across "
        "ThreadPool workers (RAM/CPU spike) whenever several voice messages arrive "
        "before the first load completes."
    )
else:
    print("Only one load occurred; race did not trigger in this run.")
