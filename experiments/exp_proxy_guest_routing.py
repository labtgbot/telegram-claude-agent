"""
EXPERIMENT: Guest Mode routing decisions in handle_chat_message.

We model the routing booleans exactly as chat.py computes them, for several
scenarios, to expose two concerns:

(A) The top-of-handler gate:
        allowed_ids = settings.allowed_chat_ids
        if allowed_ids and chat.id not in allowed_ids: return
    A guest_message arrives from a chat the bot is NOT a member of. Its chat.id
    is the *guest's* chat, which by definition will not be in allowed_chat_ids.
    => If allowed_chat_ids is configured, ALL guest queries are dropped before
       answerGuestQuery is ever called. Does Guest Mode silently stop working
       whenever allowed_chat_ids is set?

(B) Streaming vs guest:
        use_streaming = settings.free_claude_streaming_enabled and not _guest_query_id(message)
        use_draft_stream = _should_use_message_draft(message)  # private + draft enabled
    Confirm a guest query never takes the streaming/draft path (this is the #390
    fix) and always goes through the non-stream branch -> send_final_reply ->
    answerGuestQuery.
"""

class FakeChat:
    def __init__(self, cid, ctype):
        self.id = cid
        self.type = ctype


def routing(chat_id, chat_type, *, allowed_chat_ids, guest_mode_enabled,
            streaming_enabled, draft_enabled, guest_query_id, is_group_addressed=True):
    chat = FakeChat(chat_id, chat_type)

    # (1) allowed gate
    if allowed_chat_ids and chat.id not in allowed_chat_ids:
        return {"dropped_by_allowed_gate": True}

    is_group = chat.type in ("group", "supergroup")

    # group addressing gate (simplified: assume addressed when is_group_addressed)
    if is_group and not is_group_addressed:
        return {"dropped_by_addressing": True}

    use_history = not (is_group and guest_mode_enabled)

    use_draft_stream = draft_enabled and chat.type == "private"
    use_streaming = streaming_enabled and not guest_query_id

    if use_streaming and use_draft_stream:
        path = "draft_stream"
    elif use_streaming:
        path = "edit_stream"
    else:
        path = "nonstream -> send_final_reply"

    return {
        "dropped_by_allowed_gate": False,
        "use_history": use_history,
        "use_streaming": use_streaming,
        "use_draft_stream": use_draft_stream,
        "path": path,
    }


print("=== (A) Guest query from a non-member chat, allowed_chat_ids SET ===")
# allowed list contains some operator group, NOT the guest's chat.
r = routing(
    chat_id=-100999,            # guest's chat, NOT in allowed list
    chat_type="supergroup",
    allowed_chat_ids=[-100111], # operator's allowed chat
    guest_mode_enabled=True,
    streaming_enabled=True,
    draft_enabled=False,
    guest_query_id="gq_abc",
)
print("  ", r)
if r.get("dropped_by_allowed_gate"):
    print(">>> RESULT: With allowed_chat_ids set, a Guest Mode query whose chat is")
    print(">>>         not in the allow-list is DROPPED before answerGuestQuery.")
    print(">>>         Guest Mode + allowed_chat_ids are mutually incompatible:")
    print(">>>         the guest query id is never honoured. NEEDS confirmation whether")
    print(">>>         guest updates even pass through this handler / allowed gate.")
print()

print("=== (A') Guest query, allowed_chat_ids EMPTY (default) ===")
r2 = routing(
    chat_id=-100999, chat_type="supergroup",
    allowed_chat_ids=[], guest_mode_enabled=True,
    streaming_enabled=True, draft_enabled=False, guest_query_id="gq_abc",
)
print("  ", r2)
print()

print("=== (B) Guest query never streams (=> #390 fix) ===")
assert r2["path"].startswith("nonstream"), r2
assert r2["use_streaming"] is False
print("  guest query path:", r2["path"], "use_streaming:", r2["use_streaming"], "-> OK")
print()

print("=== (B') Normal private message streams via draft when enabled ===")
r3 = routing(
    chat_id=777, chat_type="private",
    allowed_chat_ids=[], guest_mode_enabled=True,
    streaming_enabled=True, draft_enabled=True, guest_query_id=None,
)
print("  ", r3)
