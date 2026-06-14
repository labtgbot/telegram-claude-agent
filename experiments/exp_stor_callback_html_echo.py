"""
EXPERIMENT: callback handlers echo user-influenced callback_data into an
HTML-parsed message without escaping.

The bot is created with default parse_mode=HTML (bot/main.py).
handle_model_set_callback does:
    model = (query.data or "").removeprefix("model:set:").strip()
    ...
    await query.message.answer(f"Model set to: {model}")     # parse_mode=HTML

`model` is taken verbatim from callback_data. callback_data is normally produced
by the bot, BUT a CallbackQuery can carry ANY data the client sends back from an
inline keyboard button the bot rendered — and Telegram does not guarantee the
data was unmodified for custom clients; more importantly, ANY inline keyboard
that the bot ever produced (or that is forwarded/shared) can be pressed, and the
64-byte callback_data is fully attacker-influenceable when the button originates
from an attacker-built message via a second bot or a shared keyboard.

We show that an HTML/script-bearing model string flows UNESCAPED into the
answer() text. With parse_mode=HTML, tags like <b>, <a href=...> are rendered;
malformed tags raise a Telegram 400 (can't parse entities) instead.
"""
import asyncio
import os
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock

sys.path.insert(0, ".")

os.environ.setdefault("FREE_CLAUDE_BASE_URL", "http://localhost:8082")
os.environ.setdefault("FREE_CLAUDE_AUTH_TOKEN", "testtoken")
os.environ.setdefault("FREE_CLAUDE_DEFAULT_MODEL", "claude-3-haiku-20240307")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")

import bot.handlers.callbacks as cb  # noqa: E402
from bot.utils.storage import MemoryStorage  # noqa: E402


async def main():
    cb.storage = MemoryStorage()
    cb.perform_answer_callback_query = AsyncMock()

    captured = {}

    async def fake_answer(text, *a, **k):
        captured["text"] = text

    payload = "<b>injected</b><a href='https://evil.example'>click</a>"
    q = SimpleNamespace(
        id="cbq",
        data=f"model:set:{payload}",
        from_user=SimpleNamespace(id=1),
        message=SimpleNamespace(answer=fake_answer, chat=SimpleNamespace(id=1)),
        bot=SimpleNamespace(),
    )
    await cb.handle_model_set_callback(q)

    print("Echoed message text:", repr(captured.get("text")))
    print("Stored model:", repr(cb.storage.get_setting(1, "model")))

    print("\n=== RESULT ===")
    text = captured.get("text", "")
    if payload in text and ("<b>" in text and "&lt;b&gt;" not in text):
        print(
            "CONFIRMED: raw HTML from callback_data is echoed UNESCAPED into an "
            "HTML-parsed message. With parse_mode=HTML this renders attacker "
            "markup (links/bold), and malformed tags would instead trigger a "
            "Telegram 400 'can't parse entities'. The same pattern repeats in "
            "settings:refresh / model:set ack text."
        )
    else:
        print("Echo is escaped or sanitized.")
    print(
        "Caveat on exploitability: callback_data buttons are normally rendered by "
        "THIS bot from the model list, so reachability requires a forwarded/"
        "shared keyboard or a non-standard client. Treat as defense-in-depth / "
        "robustness rather than a guaranteed remote vector."
    )


asyncio.run(main())
