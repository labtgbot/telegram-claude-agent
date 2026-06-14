"""
EXPERIMENT: per-message pop(0) trimming can leave history starting with an
'assistant' turn (orphaned), producing a malformed message sequence that is
later prepended to a new request.

chat.py persists TWO messages per turn (user, then assistant) and the default
max_history is 20 (even). With an even cap and 2-per-turn writes the boundary
still lands such that after trimming the first surviving message can be an
'assistant' role. We reproduce the exact sequence and inspect history[0].

Many chat-completⁱon backends (incl. Anthropic Messages API) require the first
message in `messages` to have role 'user'; a leading 'assistant' turn is at best
wasted context and at worst a 400 from the upstream proxy.
"""
import sys

sys.path.insert(0, ".")

from bot.utils.storage import MemoryStorage  # noqa: E402


def run(max_history):
    s = MemoryStorage(max_history=max_history, ttl_seconds=None)
    chat_id, user_id = 1, 1
    # Simulate N conversation turns exactly like chat.py does.
    for i in range(max_history):  # enough turns to overflow the cap
        s.add_message(chat_id, user_id, "user", f"u{i}")
        s.add_message(chat_id, user_id, "assistant", f"a{i}")
    hist = s.get_history(chat_id, user_id)
    roles = [m["role"] for m in hist]
    return roles


for mh in (20, 5, 4, 3, 10):
    roles = run(mh)
    leads_assistant = roles[0] == "assistant"
    print(
        f"max_history={mh:2d} | len={len(roles)} | first_role={roles[0]:9s} "
        f"| sequence={roles}"
    )
    if leads_assistant:
        print("    ^ history begins with an ORPHAN assistant turn")

print("\n=== RESULT ===")
roles20 = run(20)
if roles20[0] == "assistant":
    print(
        "BUG CONFIRMED (default max_history=20): trimmed history starts with an "
        "'assistant' message. chat.py prepends this to every new request "
        "(messages.extend(get_history(...))), so the upstream sees a leading "
        "assistant turn — wasted/invalid context for the Anthropic Messages API."
    )
else:
    print(
        "With max_history=20 the first surviving role is 'user' (roles[0]="
        f"{roles20[0]!r}); the orphan-assistant problem appears with ODD caps "
        "or other write patterns — see the table above."
    )
