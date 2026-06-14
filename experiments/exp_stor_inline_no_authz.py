"""
EXPERIMENT: inline handler has zero authorization & ignores allowed_chat_ids.

bot/handlers/inline.py answers EVERY inline query from ANY user, with no check
against settings.allowed_chat_ids / admin lists. For a bot deployed as
"private / restricted to specific chats", inline mode still responds to the
entire world (anyone who types @thebot in any chat).

We confirm:
  1. The handler answers regardless of who sends it.
  2. It reads NO settings and performs NO allowlist gate (static analysis of the
     module source: no reference to allowed_chat_ids / admin / settings).
"""
import asyncio
import inspect
import os
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock

sys.path.insert(0, ".")

os.environ.setdefault("FREE_CLAUDE_BASE_URL", "http://localhost:8082")
os.environ.setdefault("FREE_CLAUDE_AUTH_TOKEN", "testtoken")
os.environ.setdefault("FREE_CLAUDE_DEFAULT_MODEL", "claude-3-haiku-20240307")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")

import bot.handlers.inline as inline_mod  # noqa: E402
from bot.handlers.inline import handle_inline_query  # noqa: E402


async def main():
    # An attacker / random user who is NOT in any allowlist.
    q = SimpleNamespace(
        id="iq-1",
        from_user=SimpleNamespace(id=-999, username="random_outsider"),
        query="anything",
        answer=AsyncMock(),
    )
    await handle_inline_query(q)
    answered = q.answer.await_count == 1
    print("Inline query from random outsider answered:", answered)

    src = inspect.getsource(inline_mod)
    mentions_authz = any(
        tok in src
        for tok in ("allowed_chat_ids", "admin", "is_admin", "settings.", "authoriz")
    )
    print("inline.py references any authorization/allowlist:", mentions_authz)

    print("\n=== RESULT ===")
    if answered and not mentions_authz:
        print(
            "BUG CONFIRMED: inline handler answers all users with no authorization "
            "and ignores TELEGRAM_ALLOWED_CHAT_IDS. A 'restricted' deployment still "
            "exposes inline results to anyone."
        )
    else:
        print("No bug.")


asyncio.run(main())
