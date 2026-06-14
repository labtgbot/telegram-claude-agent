"""
EXPERIMENT (strongest real trigger): in handle_chat_message, get_history()
runs at the TOP (refreshing history TTL) but get_setting('model') runs much
LATER and is only reached if content_blocks is produced. Several early-return
paths between them refresh history WITHOUT ever reading the setting:

    line ~518: messages.extend(storage.get_history(chat.id, user_id))   # history touched
    ... media handling ...
    line ~532: oversized image      -> return        (setting NEVER read)
    line ~559: failed transcription -> return        (setting NEVER read)
    line ~574: failed extraction    -> return        (setting NEVER read)
    line ~585: model = storage.get_setting(...)       # only here

So a user who keeps sending e.g. voice notes that fail transcription (whisper
not installed -> transcribe returns "" -> early return) keeps their history TTL
fresh on every attempt, but their model setting is never re-touched and is
evicted after TTL. Next successful message silently uses the DEFAULT model.

We drive the REAL handle_chat_message with stubs and a controllable clock on the
real storage, exercising the failed-transcription early-return path.
"""
import asyncio
import os
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock

sys.path.insert(0, ".")

os.environ.setdefault("FREE_CLAUDE_BASE_URL", "http://localhost:8082")
os.environ.setdefault("FREE_CLAUDE_AUTH_TOKEN", "testtoken")
os.environ.setdefault("FREE_CLAUDE_DEFAULT_MODEL", "DEFAULT-MODEL")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")

import bot.handlers.chat as chat  # noqa: E402
from bot.utils.storage import MemoryStorage  # noqa: E402


class _SettingsStub:
    allowed_chat_ids = []
    free_claude_base_url = "http://localhost:8082"
    free_claude_auth_token = "t"
    free_claude_default_model = "DEFAULT-MODEL"
    free_claude_streaming_enabled = False
    free_claude_timeout_seconds = 1
    telegram_chat_action_enabled = False
    telegram_guest_mode_enabled = True
    telegram_media_download_max_bytes = 10_000_000
    telegram_message_draft_enabled = False


now = {"t": 0.0}


def clock():
    return now["t"]


def voice_message(chat_id, user_id):
    bot = SimpleNamespace(
        username="testbot",
        get_me=AsyncMock(return_value=SimpleNamespace(username="testbot")),
        get_file=AsyncMock(return_value=SimpleNamespace(file_path="v/f", file_size=10)),
        download_file=AsyncMock(return_value=b"audio"),
    )
    return SimpleNamespace(
        text=None,
        photo=None,
        voice=SimpleNamespace(file_id="v-id", file_size=10),
        document=None,
        caption=None,
        reply_to_message=None,
        message_id=1,
        from_user=SimpleNamespace(id=user_id),
        chat=SimpleNamespace(id=chat_id, type="private"),
        bot=bot,
        answer=AsyncMock(),
    )


async def main():
    test_storage = MemoryStorage(ttl_seconds=3600, cleanup_interval_seconds=0, clock=clock)
    chat.storage = test_storage
    chat.settings = _SettingsStub()
    # Transcription always fails (e.g. whisper not installed) -> early return.
    chat.transcribe_voice = AsyncMock(return_value="")

    CHAT, USER = 100, 7

    # t=0: user selects a model and has one good turn so history exists.
    test_storage.set_setting(USER, "model", "claude-3-opus")
    test_storage.add_message(CHAT, USER, "user", "hi")
    test_storage.add_message(CHAT, USER, "assistant", "hello")
    print("t=0    model =", test_storage.get_setting(USER, "model", "GONE"))

    # The user keeps sending voice notes every 20 min; each fails transcription
    # AFTER get_history already refreshed the history TTL.
    for minute in (20, 40, 60, 80, 100, 120):
        now["t"] = minute * 60.0
        await chat.handle_chat_message(voice_message(CHAT, USER))

    print("t=7200 history present:", (CHAT, USER) in test_storage.histories,
          "| len:", len(test_storage.histories.get((CHAT, USER), [])))
    model_now = test_storage.get_setting(USER, "model", "GONE-DEFAULTED")
    print("t=7200 model =", model_now)

    print("\n=== RESULT ===")
    if model_now != "claude-3-opus":
        print(
            "BUG CONFIRMED via the real handle_chat_message early-return path: "
            "repeated failed-media messages keep history TTL warm while the model "
            "setting is evicted; it silently reverts to "
            f"'{model_now}'. This is the #348 symptom re-introduced through TTL "
            "eviction because history and settings have independent last-access "
            "clocks and the early returns skip get_setting()."
        )
    else:
        print("Setting survived.")


asyncio.run(main())
