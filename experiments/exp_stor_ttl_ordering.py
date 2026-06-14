"""
EXPERIMENT: TTL eviction ordering / liveness correctness in MemoryStorage.

Probes several subtle properties:

(A) get_history runs `_cleanup_if_due(now)` BEFORE recording last-access. Does a
    read that arrives exactly at the cleanup tick evict the entry it is about to
    return? (Self-eviction on read.)

(B) Does an active reader keep its OWN entry alive, or can cleanup_if_due evict
    it using a stale last_access from > TTL ago even though we are reading NOW?

(C) The boundary: entries expire at last_access <= now - ttl. Check the exact
    off-by-one second.
"""
import sys

sys.path.insert(0, ".")

from bot.utils.storage import MemoryStorage  # noqa: E402

now = {"t": 0.0}


def clock():
    return now["t"]


print("--- (A)/(B) self-eviction-on-read probe ---")
# cleanup runs on every access (interval 0). TTL 100s.
s = MemoryStorage(ttl_seconds=100, cleanup_interval_seconds=0, clock=clock)
s.add_message(1, 1, "user", "hello")  # last_access = 0
print("t=0   history len:", len(s.histories.get((1, 1), [])))

# Jump to t=150 (> TTL). A read at t=150: _cleanup_if_due(150) runs FIRST using
# last_access=0 -> evicts -> then get returns [].
now["t"] = 150.0
h = s.get_history(1, 1)
print("t=150 get_history ->", h, "| histories:", dict(s.histories))
print("  (Reading right after expiry returns [] and drops the entry — expected.)")

# Now the user keeps chatting: does add_message resurrect & keep alive?
s.add_message(1, 1, "user", "again")  # last_access = 150
now["t"] = 200.0  # +50s, within TTL
h2 = s.get_history(1, 1)
print("t=200 after re-add, get_history len:", len(h2))

print("\n--- (C) exact boundary (expires at last_access <= now - ttl) ---")
s2 = MemoryStorage(ttl_seconds=100, cleanup_interval_seconds=999, clock=clock)
now["t"] = 1000.0
s2.add_message(5, 5, "user", "x")  # last_access = 1000
# now - ttl == 1100 - 100 == 1000 == last_access -> <= triggers eviction AT exactly ttl.
now["t"] = 1100.0
removed = s2.cleanup_expired()
print(f"At exactly ttl (100s elapsed): removed={removed} -> entry evicted at t==ttl boundary (<=).")

now["t"] = 1200.0
s2b = MemoryStorage(ttl_seconds=100, cleanup_interval_seconds=999, clock=clock)
now["t"] = 1200.0
s2b.add_message(6, 6, "user", "y")  # last_access = 1200
now["t"] = 1299.0  # 99s elapsed, < ttl
removed_b = s2b.cleanup_expired()
print(f"At ttl-1 (99s elapsed): removed={removed_b} -> still alive just under ttl.")

print("\n--- (D) live-reference aliasing after eviction ---")
s3 = MemoryStorage(ttl_seconds=100, cleanup_interval_seconds=999, clock=clock)
now["t"] = 0.0
s3.add_message(9, 9, "user", "m1")
ref = s3.get_history(9, 9)  # caller holds a live reference to the internal list
print("caller holds ref id:", id(ref), "len:", len(ref))
now["t"] = 1000.0  # >> TTL
s3.cleanup_expired()
print("after eviction: key in histories?", (9, 9) in s3.histories)
# The handler (chat.py) does messages.extend(get_history(...)) then appends and
# persists via add_message, which setdefault()s a NEW empty list. So a stale ref
# does not corrupt new state — but let's prove add_message creates a fresh list.
s3.add_message(9, 9, "assistant", "fresh")
print("ref still old (stale) len:", len(ref), "| new history len:", len(s3.get_history(9, 9)))
print("stale ref is NOT the new internal list:", ref is not s3.histories.get((9, 9)))
