"""
EXPERIMENT: Admin-callback authorization uses query.message.chat.id, not the
clicker's chat. Can a non-admin in an admin group trigger destructive callbacks?

Setup recap (from bot/handlers/callbacks.py):
    handle_logout_confirm_callback / handle_close_confirm_callback do:
        if query.message is None or not _is_admin_action_allowed(
            query.message.chat.id,        # <-- chat of the button message
            _callback_user_id(query),     # <-- who clicked
        ): reject

    _is_admin_action_allowed -> is_admin_action_allowed(
        chat_id, user_id, admin_chat_ids, admin_user_ids)

    is_admin_action_allowed requires:
        admin_chat_ids set AND chat_id in admin_chat_ids
        AND is_admin_sender_allowed(...)

    is_admin_sender_allowed:
        if admin_user_ids: user_id in admin_user_ids
        else: _is_private_admin_request(chat_id, user_id)
              -> if user_id is None: chat_id > 0
                 else: chat_id == user_id

This experiment checks the *configuration where admin_user_ids is NOT set*
(only admin_chat_ids), which is a supported config per issue #396's wording.
We model an admin group chat (negative id) that is in admin_chat_ids and ask:
which (chat_id, user_id) combinations pass?
"""
from bot.utils.admin_auth import (
    is_admin_action_allowed,
    _is_private_admin_request,
)

ADMIN_GROUP = -1001234567890  # an admin *group* chat id


def check(chat_id, user_id, admin_chat_ids, admin_user_ids):
    return is_admin_action_allowed(
        chat_id=chat_id,
        user_id=user_id,
        admin_chat_ids=admin_chat_ids,
        admin_user_ids=admin_user_ids,
    )


print("=== Config A: admin_chat_ids = [admin group], admin_user_ids = [] ===")
print("(This is the #396-described 'chat_id only' fallback still being allowed)")
admin_chat_ids = [ADMIN_GROUP]
admin_user_ids = []

# Any user clicking the button INSIDE the admin group.
# chat_id = ADMIN_GROUP (negative), user_id = some random non-admin member.
random_member = 555
res = check(ADMIN_GROUP, random_member, admin_chat_ids, admin_user_ids)
print(f"  random group member {random_member} clicks logout/close in admin group -> allowed={res}")
print(f"    _is_private_admin_request({ADMIN_GROUP}, {random_member}) = {_is_private_admin_request(ADMIN_GROUP, random_member)}")

# Same, but the callback arrives with user_id = None (rare, e.g. anonymized).
res_none = check(ADMIN_GROUP, None, admin_chat_ids, admin_user_ids)
print(f"  user_id=None in admin group -> allowed={res_none}")
print()

print(">>> Interpretation:")
if not res:
    print(">>> In config A, ANY member of the admin group is REJECTED for a group")
    print(">>> chat unless admin_user_ids is configured, because _is_private_admin_request")
    print(">>> requires chat_id == user_id (impossible for a negative group id).")
    print(">>> => For GROUP admin chats, admin actions are effectively UNUSABLE")
    print(">>>    unless admin_user_ids is also set. This is a usability footgun,")
    print(">>>    NOT a privilege escalation.")
print()

print("=== Config B: admin_user_ids set => callback chat is query.message.chat.id ===")
admin_user_ids2 = [111, 222]
admin_chat_ids2 = [ADMIN_GROUP]
# The right person (admin user 111) clicks inside the admin group -> allowed.
print("  admin user 111 clicks in admin group ->",
      check(ADMIN_GROUP, 111, admin_chat_ids2, admin_user_ids2))
# A non-admin user 999 clicks in the admin group -> must be rejected.
print("  non-admin 999 clicks in admin group ->",
      check(ADMIN_GROUP, 999, admin_chat_ids2, admin_user_ids2))
print()
print(">>> With admin_user_ids set, the user-level check correctly gates clicks")
print(">>> regardless of who is in the group. (#396 fix works for this path.)")
