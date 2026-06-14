"""
EXPERIMENT (realistic): does the real chat.py call sequence protect the setting?

In handle_chat_message the per-message sequence is:
   1. get_history(chat, user)          -> refreshes history last-access
   2. ... build request ...
   3. get_setting(user, "model")       -> refreshes settings last-access
   4. add_message(...) x2              -> refreshes history last-access

So in the *normal text* path the setting IS refreshed each message. The desync
window appears whenever a code path touches history WITHOUT reading the setting
within one TTL period. Two real cases:

CASE A: The `history:clear` callback calls storage.clear_history (history path)
        but never get_setting. A user who only ever clears history (or whose
        client only refreshes via settings:refresh AFTER expiry) ...

CASE B (the robust, undeniable one): set the model ONCE, then let exactly the
        history be refreshed by the streaming-disabled branch where reply_text
        is empty -> add_message is skipped, but get_history at the top still
        refreshed history. Even simpler: ANY incoming message that is NOT
        addressed to the bot in a group returns early AFTER... no.

The cleanest undeniable real case: the model setting and history have different
TTL clocks, so set model at t0, then ONLY read history (e.g. a second device or
a /clear that reads history) keeps history alive while the setting dies.

Here we reproduce CASE A precisely with the real storage object used by the
handlers and callbacks (the module-global `storage`).
"""
import sys

sys.path.insert(0, ".")

import bot.utils.storage as storage_mod  # noqa: E402

now = {"t": 0.0}


def clock():
    return now["t"]


# Rebuild the global storage with a controllable clock + 1h TTL (the real default).
storage = storage_mod.MemoryStorage(
    ttl_seconds=3600, cleanup_interval_seconds=60, clock=clock
)

chat_id, user_id = 777, 99

# t=0: user selects opus via /model (set_setting) and sends first message.
storage.set_setting(user_id, "model", "claude-3-opus")
storage.get_history(chat_id, user_id)
storage.add_message(chat_id, user_id, "user", "hi")
storage.add_message(chat_id, user_id, "assistant", "hello")
print("t=0   model =", storage.get_setting(user_id, "model", "DEFAULT"))

# The user keeps the conversation context warm by issuing /clear-less reads.
# Realistically: the `history:clear` callback path (callbacks.py
# handle_clear_history_callback) calls clear_history then re-adds nothing, OR a
# group guest path. We model a client that touches history every 30 min but
# never the setting (e.g. only sends the `settings:refresh` callback which DOES
# read the setting -> would refresh; so instead model the `history:clear`
# callback which only touches history).
for half_hour in range(1, 5):  # 30, 60, 90, 120 minutes
    now["t"] = half_hour * 1800.0
    # history:clear callback touches ONLY history last-access bookkeeping
    storage.clear_history(chat_id, user_id)
    storage.add_message(chat_id, user_id, "user", "again")

now["t"] = 2 * 3600.0 + 1  # 2h+ since the setting was last touched
model_now = storage.get_setting(user_id, "model", "DEFAULT-FALLBACK")
print(f"t={now['t']:.0f}s  model =", model_now)

print("\n=== RESULT ===")
if model_now != "claude-3-opus":
    print(
        "BUG CONFIRMED (real storage, 1h TTL): a user who keeps history warm but "
        "does not re-read the setting within TTL loses their model selection; it "
        f"silently reverts to '{model_now}'."
    )
else:
    print("No bug in this path.")
