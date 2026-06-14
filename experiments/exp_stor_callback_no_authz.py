"""
EXPERIMENT: callback handlers lack the allowed_chat_ids gate that chat.py has.

bot/handlers/chat.py:490-492 enforces:
    allowed_ids = settings.allowed_chat_ids
    if allowed_ids and chat.id not in allowed_ids:
        return

bot/handlers/callbacks.py applies NO such check for the non-admin callbacks:
    - settings:refresh   (handle_settings_refresh_callback)
    - model:set:<x>      (handle_model_set_callback)
    - history:clear      (handle_clear_history_callback)
    - action:cancel      (handle_cancel_callback)

Only the admin callbacks (logout/close) are gated (via _is_admin_action_allowed).

Consequence: when a deployment restricts the bot to specific chats via
TELEGRAM_ALLOWED_CHAT_IDS, ANY user who can deliver a callback_query (e.g. a
forwarded/shared inline keyboard, or simply a chat that is NOT in the allowlist)
can still:
    * overwrite another flow's per-user model setting, and
    * read/refresh settings,
even though the same user is blocked from sending normal chat messages.

We drive the REAL handler functions with a stub CallbackQuery and assert the
side effects happen regardless of allowlist.
"""
import asyncio
import os
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock

sys.path.insert(0, ".")

# Required settings so bot.config imports (mirrors tests/conftest.py).
os.environ.setdefault("FREE_CLAUDE_BASE_URL", "http://localhost:8082")
os.environ.setdefault("FREE_CLAUDE_AUTH_TOKEN", "testtoken")
os.environ.setdefault("FREE_CLAUDE_DEFAULT_MODEL", "claude-3-haiku-20240307")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")

import bot.handlers.callbacks as cb  # noqa: E402
from bot.utils.storage import MemoryStorage  # noqa: E402


class _SettingsStub:
    # A locked-down deployment: only chat 111 is allowed to use the bot.
    allowed_chat_ids = [111]
    admin_chat_ids = []
    admin_user_ids = []
    free_claude_default_model = "default-model"


def make_query(*, data, chat_id, user_id):
    msg = SimpleNamespace(
        chat=SimpleNamespace(id=chat_id),
        answer=AsyncMock(),
    )
    return SimpleNamespace(
        id="cbq-1",
        data=data,
        from_user=SimpleNamespace(id=user_id),
        message=msg,
        bot=SimpleNamespace(),
    )


async def main():
    test_storage = MemoryStorage()
    cb.storage = test_storage
    cb.settings = _SettingsStub()
    # Stub the ack so no network call happens.
    cb.perform_answer_callback_query = AsyncMock()

    EVIL_CHAT = 999999  # NOT in allowed_chat_ids
    EVIL_USER = 424242

    # 1) model:set from a NON-allowed chat
    q = make_query(data="model:set:attacker-controlled-model", chat_id=EVIL_CHAT, user_id=EVIL_USER)
    await cb.handle_model_set_callback(q)
    model = test_storage.get_setting(EVIL_USER, "model", "NONE")
    print("After model:set from non-allowed chat -> stored model:", model)

    # 2) history:clear from a NON-allowed chat (seed history first)
    test_storage.add_message(EVIL_CHAT, EVIL_USER, "user", "secret")
    print("History before clear:", len(test_storage.get_history(EVIL_CHAT, EVIL_USER)))
    q2 = make_query(data="history:clear", chat_id=EVIL_CHAT, user_id=EVIL_USER)
    await cb.handle_clear_history_callback(q2)
    print("History after clear from non-allowed chat:", len(test_storage.get_history(EVIL_CHAT, EVIL_USER)))

    # 3) settings:refresh from a NON-allowed chat
    q3 = make_query(data="settings:refresh", chat_id=EVIL_CHAT, user_id=EVIL_USER)
    await cb.handle_settings_refresh_callback(q3)
    refreshed_answer = q3.message.answer.await_args
    print("settings:refresh answered from non-allowed chat:", refreshed_answer is not None)

    print("\n=== RESULT ===")
    ok = (
        model == "attacker-controlled-model"
        and len(test_storage.get_history(EVIL_CHAT, EVIL_USER)) == 0
        and refreshed_answer is not None
    )
    if ok:
        print(
            "BUG CONFIRMED: non-admin callbacks (model:set, history:clear, "
            "settings:refresh) execute for users in chats that are NOT in "
            "TELEGRAM_ALLOWED_CHAT_IDS. chat.py blocks these same users; "
            "callbacks.py does not -> inconsistent authorization."
        )
    else:
        print("No bug: callbacks were gated.")


asyncio.run(main())
