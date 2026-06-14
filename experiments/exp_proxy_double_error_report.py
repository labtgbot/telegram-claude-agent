"""
EXPERIMENT: On a streaming failure, is the error reported to the user TWICE?

handle_streaming:
    sent_msg = await message.answer("…")
    try:
        stream = await client.send_message(...); async for ...
    except Exception:
        await sent_msg.edit_text(CHAT_USER_ERROR_MESSAGE)   # (1) edit "…" -> error
        raise

handle_chat_message:
    try:
        ... handle_streaming(...) ...
    except Exception as exc:
        logger.exception(...)
        await message.answer(CHAT_USER_ERROR_MESSAGE)        # (2) a SECOND error msg

So a failure mid-stream shows the error both as the edited placeholder AND as a
brand-new message. We simulate handle_streaming's except path + the outer handler
to count how many error surfaces the user sees.

We use a fake Message/sent_msg that record calls, and a client whose stream raises
after the first delta.
"""
import asyncio
import os

os.environ.setdefault("FREE_CLAUDE_BASE_URL", "http://localhost")
os.environ.setdefault("FREE_CLAUDE_AUTH_TOKEN", "tok")
os.environ.setdefault("FREE_CLAUDE_DEFAULT_MODEL", "claude-x")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123:abc")

from bot.handlers.chat import handle_streaming, CHAT_USER_ERROR_MESSAGE


class FakeSent:
    def __init__(self):
        self.edits = []
    async def edit_text(self, text, **kw):
        self.edits.append(text)


class FakeMessage:
    def __init__(self):
        self.answers = []
        self._sent = FakeSent()
    async def answer(self, text, **kw):
        self.answers.append(text)
        return self._sent


class FakeStream:
    def __aiter__(self):
        return self
    async def __anext__(self):
        # yield one delta, then blow up like a dropped upstream connection
        if not getattr(self, "_done", False):
            self._done = True
            return {"type": "content_block_delta", "index": 0,
                    "delta": {"type": "text_delta", "text": "partial"}}
        raise RuntimeError("upstream connection reset")
    async def aclose(self):
        pass


class FakeClient:
    async def send_message(self, **kw):
        return FakeStream()


async def main():
    msg = FakeMessage()
    client = FakeClient()

    # Emulate the outer handler's try/except around handle_streaming.
    try:
        await handle_streaming(msg, client, [{"role": "user", "content": "x"}], "m")
    except Exception:
        # outer handler does: await message.answer(CHAT_USER_ERROR_MESSAGE)
        await msg.answer(CHAT_USER_ERROR_MESSAGE)

    print("sent_msg.edit_text calls:", msg._sent.edits)
    print("message.answer calls:", msg.answers)

    edit_errors = sum(1 for t in msg._sent.edits if t == CHAT_USER_ERROR_MESSAGE)
    answer_errors = sum(1 for t in msg.answers if t == CHAT_USER_ERROR_MESSAGE)
    total = edit_errors + answer_errors
    print()
    print(f"error shown via edit_text: {edit_errors}")
    print(f"error shown via answer:    {answer_errors}")
    print(f"TOTAL error surfaces shown to user: {total}")
    if total >= 2:
        print(">>> RESULT: a single mid-stream failure shows the SAME error to the")
        print(">>>         user TWICE: once as the edited '…' placeholder and once as a")
        print(">>>         new message. Confusing UX / duplicate error.")


if __name__ == "__main__":
    asyncio.run(main())
