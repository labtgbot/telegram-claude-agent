"""
EXPERIMENT: Guest Mode answers are HTML-rendered but sent WITHOUT parse_mode,
so the guest sees literal HTML markup.

Chain (chat.py):
  handle_streaming_with_draft / non-stream branch:
      reply_text = full_text or "..."
      await send_final_reply(message, md_to_html(reply_text))   # <-- HTML
  send_final_reply:
      if guest_query_id:
          await perform_answer_guest_query(bot, guest_query_id=..., text=text[:4096])
          return
      # else: send_reply_safely(message, text, parse_mode="HTML")

perform_answer_guest_query payload = {"guest_query_id":..., "text": text}
  -> NO parse_mode, NO entities. Telegram renders it as PLAIN TEXT.

So for a guest, md_to_html('**hi** <b>') is delivered as the literal string
'<b>hi</b> &lt;b&gt;' instead of formatted text. We demonstrate the exact bytes
that would be POSTed to answerGuestQuery and show they contain raw HTML tags and
escaped entities that the guest will see verbatim.

Contrast: the non-guest path passes the SAME md_to_html output with
parse_mode="HTML", so it renders correctly. The guest path is inconsistent.
"""
import os
os.environ.setdefault("FREE_CLAUDE_BASE_URL", "http://localhost")
os.environ.setdefault("FREE_CLAUDE_AUTH_TOKEN", "tok")
os.environ.setdefault("FREE_CLAUDE_DEFAULT_MODEL", "claude-x")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123:abc")

import asyncio
import json

import httpx

from bot.handlers.chat import md_to_html, send_final_reply


class FakeApi:
    def api_url(self, token, method):
        return f"http://local/bot{token}/{method}"


class FakeSession:
    api = FakeApi()


class FakeBot:
    token = "123:abc"
    session = FakeSession()


class FakeMessage:
    """A message carrying a guest_query_id, routed to answerGuestQuery."""
    def __init__(self):
        self.bot = FakeBot()
        self.guest_query_id = "gq_test_123"
        self.answers = []

    async def answer(self, text, **kw):
        self.answers.append((text, kw))


captured = {}


async def main():
    # Intercept the outbound answerGuestQuery POST to capture the exact payload.
    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content.decode())
        return httpx.Response(200, json={"ok": True, "result": True})

    transport = httpx.MockTransport(handler)

    # Monkeypatch httpx.AsyncClient used inside perform_answer_guest_query so it
    # uses our mock transport (it constructs its own client internally).
    real_async_client = httpx.AsyncClient

    def patched_async_client(*a, **k):
        k["transport"] = transport
        return real_async_client(*a, **k)

    httpx.AsyncClient = patched_async_client
    try:
        model_markdown = "Result: **important** & `code` and <tag>"
        rendered = md_to_html(model_markdown)
        print("model markdown :", repr(model_markdown))
        print("md_to_html out :", repr(rendered))
        msg = FakeMessage()
        await send_final_reply(msg, rendered)  # guest path
    finally:
        httpx.AsyncClient = real_async_client

    print()
    print("POST url :", captured.get("url"))
    print("POST body:", json.dumps(captured.get("body"), ensure_ascii=False))
    sent_text = captured.get("body", {}).get("text", "")
    has_parse_mode = "parse_mode" in captured.get("body", {})
    print()
    print(f"parse_mode present in payload? {has_parse_mode}")
    print(f"guest receives literal text  : {sent_text!r}")
    if not has_parse_mode and ("<b>" in sent_text or "&amp;" in sent_text or "&lt;" in sent_text):
        print(">>> RESULT: Guest gets HTML-rendered text with NO parse_mode, so the")
        print(">>>         literal '<b>', '&amp;', '&lt;' are shown to the guest instead")
        print(">>>         of formatted output. The non-guest path renders the same")
        print(">>>         string with parse_mode='HTML'. Guest output is garbled.")
    # also confirm fallback message.answer was NOT used (guest path returns early)
    print("fallback message.answer used?", bool(msg.answers))


if __name__ == "__main__":
    asyncio.run(main())
