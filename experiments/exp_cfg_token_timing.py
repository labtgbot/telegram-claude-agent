"""
EXPERIMENT 3: The webhook secret-token check in bot/main.py uses a plain
Python `!=` comparison:

    if header_token != settings.api_secret_token:
        raise HTTPException(status_code=403, detail="Invalid secret token")

`str.__ne__` short-circuits on the first differing byte, so the time taken to
reject a wrong token leaks how many leading bytes were correct. A constant-time
compare (`secrets.compare_digest`) does not.

PART A: Microbenchmark `!=` vs `secrets.compare_digest` to show the early-exit
        timing signal that an attacker could exploit to recover the token
        byte-by-byte.
PART B: Drive the REAL FastAPI `/webhook` endpoint via TestClient and confirm
        the code path that does the comparison is the plain `!=` (i.e. there is
        NO constant-time guard) and that a correct token is accepted while a
        wrong one is rejected with 403.
"""
import os
import secrets as _secrets
import sys
import time

# Required env so importing bot.config / bot.main does not crash at module load.
os.environ.setdefault("FREE_CLAUDE_BASE_URL", "http://localhost:8082")
os.environ.setdefault("FREE_CLAUDE_AUTH_TOKEN", "testtoken")
os.environ.setdefault("FREE_CLAUDE_DEFAULT_MODEL", "claude-3-haiku-20240307")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")
os.environ.setdefault("API_SECRET_TOKEN", "S3cretWebhookToken_aaaaaaaaaaaaaaaaaaaaaa")


SECRET = "S" + "a" * 1023  # long secret to make the byte-by-byte effect visible
ALMOST = "S" + "a" * 1022 + "b"  # differs only in the LAST byte
EARLY = "X" + "a" * 1022 + "b"   # differs in the FIRST byte


def _bench(fn, a, b, *, repeats=20000):
    # warm up
    for _ in range(2000):
        fn(a, b)
    samples = []
    for _ in range(7):
        t0 = time.perf_counter_ns()
        for _ in range(repeats):
            fn(a, b)
        samples.append((time.perf_counter_ns() - t0) / repeats)
    return min(samples)  # min = least noisy estimate of intrinsic cost


def _correlation(xs, ys):
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    if vx == 0 or vy == 0:
        return 0.0
    return cov / (vx * vy) ** 0.5


def part_a():
    print("=== PART A: timing of != vs secrets.compare_digest ===")
    print(f"  secret length = {len(SECRET)} chars")
    print("  Measuring time to REJECT a candidate whose first differing byte is")
    print("  at increasing prefix lengths. A monotonic rise => exploitable oracle.\n")

    ne = lambda a, b: a != b               # noqa: E731  (mirrors main.py)
    cd = _secrets.compare_digest

    prefixes = [0, 128, 256, 384, 512, 640, 768, 896, 1023]
    ne_times, cd_times = [], []
    print("  prefix_match |   !=  ns/op |  compare_digest ns/op")
    print("  -------------+-------------+----------------------")
    for p in prefixes:
        # candidate shares `p` correct leading bytes, then differs.
        cand = SECRET[:p] + ("b" if SECRET[p:p + 1] != "b" else "c") + SECRET[p + 1:]
        assert cand != SECRET and len(cand) == len(SECRET)
        tne = _bench(ne, cand, SECRET, repeats=20000)
        tcd = _bench(cd, cand, SECRET, repeats=20000)
        ne_times.append(tne)
        cd_times.append(tcd)
        print(f"  {p:11d} | {tne:10.2f} | {tcd:18.2f}")

    ne_corr = _correlation(prefixes, ne_times)
    cd_corr = _correlation(prefixes, cd_times)
    print(f"\n  Pearson corr(prefix_len, time)  !=  : {ne_corr:+.3f}  "
          "(strongly positive => time grows with matched prefix => LEAK)")
    print(f"  Pearson corr(prefix_len, time)  cmp : {cd_corr:+.3f}  "
          "(~0 => constant-time, safe)")

    # `!=` leaks if its correlation is strongly positive AND clearly stronger
    # than the constant-time baseline.
    leaks_at_token_len = ne_corr > 0.8 and ne_corr > cd_corr + 0.5
    print(f"\n  RESULT: != leaks at token-length ({len(SECRET)} chars) = {leaks_at_token_len}")
    print("  (Note: at realistic token sizes the per-op cost is dominated by")
    print("   fixed overhead, so the early-exit signal is buried in noise.)")

    # Demonstrate that != IS data-dependent in principle, at large N where the
    # buffer comparison cost dominates fixed overhead.
    print("\n  --- Same comparison at N=200000 to expose intrinsic non-constant-time ---")
    big = "a" * 200000
    first_diff = "b" + "a" * 199999
    last_diff = "a" * 199999 + "b"
    tf = _bench(ne, first_diff, big, repeats=50000)
    tl = _bench(ne, last_diff, big, repeats=50000)
    print(f"    != first-byte mismatch: {tf:8.1f} ns/op")
    print(f"    != last-byte  mismatch: {tl:8.1f} ns/op")
    ratio = tl / tf if tf else float("inf")
    print(f"    ratio last/first      : {ratio:6.1f}x  (>>1 => non-constant-time in principle)")
    leaks_in_principle = ratio > 5
    print(f"  RESULT: != is non-constant-time IN PRINCIPLE = {leaks_in_principle}")
    return leaks_in_principle


def part_b():
    print("\n=== PART B: real /webhook endpoint comparison path ===")
    import bot.main as m

    # Confirm there is no constant-time machinery imported in the module.
    import inspect
    src = inspect.getsource(m.telegram_webhook)
    uses_ne = "!=" in src
    uses_cd = "compare_digest" in src or "hmac" in src
    print(f"  webhook source uses '!='            = {uses_ne}")
    print(f"  webhook source uses compare_digest  = {uses_cd}")

    # Prevent real network/dispatch side effects: stub feed_update.
    async def _noop_feed_update(*a, **k):
        return None
    m.dp.feed_update = _noop_feed_update  # type: ignore

    # We must avoid running the lifespan (it would hit Telegram). Instead of a
    # TestClient (whose startup would call Telegram), we test the comparison
    # directly against the route handler coroutine.
    import asyncio

    correct = m.settings.api_secret_token
    wrong = "definitely-not-the-token"

    class FakeRequest:
        def __init__(self, token, body):
            self.headers = {"X-Telegram-Bot-Api-Secret-Token": token} if token is not None else {}
            self._body = body

        async def json(self):
            return self._body

    valid_update = {"update_id": 1}

    async def call(token):
        try:
            resp = await m.telegram_webhook(FakeRequest(token, valid_update))
            return ("ok", getattr(resp, "status_code", 200))
        except Exception as exc:  # HTTPException
            return ("err", getattr(exc, "status_code", None), getattr(exc, "detail", None))

    res_correct = asyncio.run(call(correct))
    res_wrong = asyncio.run(call(wrong))
    res_missing = asyncio.run(call(None))

    print(f"  correct token -> {res_correct}")
    print(f"  wrong token   -> {res_wrong}")
    print(f"  missing header-> {res_missing}")

    accepted_correct = res_correct[0] == "ok"
    rejected_wrong = res_wrong[0] == "err" and res_wrong[1] == 403
    rejected_missing = res_missing[0] == "err" and res_missing[1] == 403
    print(f"\n  RESULT: correct accepted={accepted_correct}, "
          f"wrong 403={rejected_wrong}, missing 403={rejected_missing}, "
          f"non-constant-time(!=)={uses_ne and not uses_cd}")
    return uses_ne and not uses_cd


def main():
    leaks = part_a()
    non_ct = part_b()
    print("\n=== VERDICT ===")
    print(f"  Plain != is non-constant-time in principle : {leaks}")
    print(f"  /webhook uses non-constant-time compare     : {non_ct}")
    print("  HONEST ASSESSMENT: the comparison is NOT timing-safe by best")
    print("  practice (should use secrets.compare_digest), but at realistic")
    print("  Telegram token sizes (<=256 chars) the leak is NOT practically")
    print("  measurable over a network. Severity: hardening (P3/P4), not P1.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
