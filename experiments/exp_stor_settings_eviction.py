"""
EXPERIMENT: Per-user model setting is evicted during a long ACTIVE chat session.

Hypothesis:
  MemoryStorage tracks history last-access (`_history_last_access`, keyed by
  (chat_id, user_id)) and settings last-access (`_settings_last_access`, keyed
  by user_id) INDEPENDENTLY.

  `add_message`/`get_history` only refresh `_history_last_access`. They never
  touch `_settings_last_access`. So a user who keeps chatting (refreshing
  history TTL constantly) but never re-reads their setting within the TTL will
  have their `model` setting silently evicted, falling back to the default
  model mid-session.

This is the exact failure mode of the supposedly-fixed #348 (per-user model
selection ignored), re-introduced through TTL eviction.
"""
import sys

sys.path.insert(0, ".")

from bot.utils.storage import MemoryStorage  # noqa: E402

now = {"t": 1000.0}


def clock():
    return now["t"]


# TTL 100s, cleanup checked on every access (interval 0 forces cleanup each call)
storage = MemoryStorage(ttl_seconds=100, cleanup_interval_seconds=0, clock=clock)

chat_id, user_id = 555, 42

# User picks a non-default model (e.g. via /model or model:set callback).
storage.set_setting(user_id, "model", "claude-3-opus")
print("Initial model setting:", storage.get_setting(user_id, "model", "DEFAULT"))

# Simulate an active chat session: user sends a message every 30s for 5 minutes.
# Each add_message refreshes history TTL but NOT the setting TTL.
for i in range(10):
    now["t"] += 30.0  # 30 seconds pass
    storage.add_message(chat_id, user_id, "user", f"message {i}")
    # The handler reads the model setting only when building a request,
    # but suppose the user's session relies on history liveness. We deliberately
    # do NOT call get_setting here to expose the desync.

print("\nAfter 5 minutes of continuous chatting (every 30s):")
print("  history present:", (chat_id, user_id) in storage.histories)
print("  history length:", len(storage.histories.get((chat_id, user_id), [])))

model_after = storage.get_setting(user_id, "model", "DEFAULT-FALLBACK")
print("  model setting:", model_after)

# The model setting dict itself:
print("  user_settings:", storage.user_settings)

print("\n=== RESULT ===")
if model_after != "claude-3-opus":
    print(
        "BUG CONFIRMED: history is alive but the user's model setting was evicted "
        f"-> handler now silently falls back to '{model_after}' instead of "
        "'claude-3-opus'."
    )
else:
    print("No bug: setting survived.")
