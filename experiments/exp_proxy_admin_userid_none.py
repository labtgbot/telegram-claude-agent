"""
EXPERIMENT: admin_auth with user_id=None and the `chat_id > 0` private branch.

_is_private_admin_request(chat_id, user_id):
    if user_id is None: return chat_id > 0
    return chat_id == user_id

is_admin_sender_allowed: if admin_user_ids set -> user must be in it (None => False).
                         else -> _is_private_admin_request.

Question 1: When admin_user_ids is EMPTY and a message arrives with user_id=None
(e.g. anonymous group admins post with from_user=None, or channel posts), is the
sender treated as an admin purely because chat_id > 0?

In a *private* chat the id is always > 0 and equals the user id, so a private
DM is "trusted" without any user check when admin_user_ids is unset. That is the
intended fallback. But is_admin_action_allowed *also* requires
chat_id in admin_chat_ids, so a random private chat is NOT auto-admin.

Question 2 (the real risk): is_admin_or_allowed_chat with allowed_chat_ids only.
trusted_chat_ids = admin_chat_ids or allowed_chat_ids.
If a positive chat id is listed in allowed_chat_ids and a message there has
user_id=None, is_admin_sender_allowed returns _is_private_admin_request(chat>0,None)
= True. So ANY anonymous (user_id=None) message in an allowed positive-id chat
passes is_admin_or_allowed_chat even when admin_user_ids is configured-but-empty.
This gates /status, /whoami-like read commands (commands.py 3422/3437).

We enumerate to show exactly which inputs pass.
"""
from bot.utils.admin_auth import (
    is_admin_action_allowed,
    is_admin_or_allowed_chat,
    is_admin_sender_allowed,
    _is_private_admin_request,
)

print("=== _is_private_admin_request truth table ===")
for chat_id in (123, -100, 0):
    for user_id in (None, 123, 999):
        print(f"  chat_id={chat_id:5} user_id={str(user_id):5} -> {_is_private_admin_request(chat_id, user_id)}")
print()

print("=== is_admin_sender_allowed, admin_user_ids EMPTY ===")
print("  private chat 777, user None ->",
      is_admin_sender_allowed(chat_id=777, user_id=None, admin_user_ids=[]))
print("  group  chat -100, user None ->",
      is_admin_sender_allowed(chat_id=-100, user_id=None, admin_user_ids=[]))
print()

print("=== is_admin_action_allowed: random private DM is NOT auto-admin ===")
print("  chat 777 (NOT in admin_chat_ids), user None ->",
      is_admin_action_allowed(chat_id=777, user_id=None, admin_chat_ids=[555], admin_user_ids=[]))
print("  chat 555 (IN admin_chat_ids),    user None ->",
      is_admin_action_allowed(chat_id=555, user_id=None, admin_chat_ids=[555], admin_user_ids=[]))
print("    (a private DM whose chat_id 555 is in admin_chat_ids => admin, expected)")
print()

print("=== Question 2: is_admin_or_allowed_chat with allowed positive chat id ===")
allowed = [12345]  # a positive chat id in allowed_chat_ids (e.g. an allowed private chat)
# admin_user_ids EMPTY: anonymous message in allowed chat
r1 = is_admin_or_allowed_chat(chat_id=12345, user_id=None,
                              admin_chat_ids=[], allowed_chat_ids=allowed, admin_user_ids=[])
print(f"  allowed positive chat 12345, user None, admin_user_ids=[] -> {r1}")
# admin_user_ids SET: does the anonymous sender still slip through?
r2 = is_admin_or_allowed_chat(chat_id=12345, user_id=None,
                              admin_chat_ids=[], allowed_chat_ids=allowed, admin_user_ids=[111])
print(f"  allowed positive chat 12345, user None, admin_user_ids=[111] -> {r2}")
print()
if r1 and not r2:
    print(">>> RESULT: When admin_user_ids is EMPTY, an anonymous (user_id=None)")
    print(">>>         message in an allowed POSITIVE-id chat passes is_admin_or_allowed_chat")
    print(">>>         purely via the chat_id>0 fallback. With admin_user_ids set, it's blocked.")
    print(">>>         Severity depends on whether allowed_chat_ids ever holds positive ids and")
    print(">>>         whether user_id can be None there. For PRIVATE chats user_id is never None")
    print(">>>         in practice (from_user is always set), so this is mostly defense-in-depth.")
