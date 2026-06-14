"""
REGRESSION CHECK: Guest Mode answers are HTML-rendered and sent through
answerGuestQuery as an InlineQueryResultArticle whose InputTextMessageContent
uses parse_mode="HTML".

Chain (chat.py):
  handle_streaming_with_draft / non-stream branch:
      reply_text = full_text or "..."
      await send_final_reply(message, md_to_html(reply_text))   # <-- HTML
  send_final_reply:
      if guest_query_id:
          await perform_answer_guest_query(
              bot,
              guest_query_id=...,
              text=text[:4096],
              parse_mode="HTML",
          )
          return
      # else: send_reply_safely(message, text, parse_mode="HTML")

  perform_answer_guest_query payload =
    {"guest_query_id":..., "result": "{\"type\":\"article\",...}"}
    where result.input_message_content.parse_mode == "HTML".

So for a guest, md_to_html('**hi** <b>') is delivered as Telegram HTML inside
InputTextMessageContent, matching the non-guest path.

Contrast: the non-guest path passes the SAME md_to_html output with
parse_mode="HTML", so both paths now render formatted text consistently.
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
    result = json.loads(captured.get("body", {}).get("result", "{}"))
    content = result.get("input_message_content", {})
    sent_text = content.get("message_text", "")
    parse_mode = content.get("parse_mode")
    print()
    print(f"result type: {result.get('type')!r}")
    print(f"parse_mode: {parse_mode!r}")
    print(f"guest message_text: {sent_text!r}")
    if parse_mode == "HTML" and ("<b>" in sent_text or "&amp;" in sent_text or "&lt;" in sent_text):
        print(">>> RESULT: Guest gets Telegram HTML with parse_mode='HTML',")
        print(">>>         so tags/entities are rendered instead of shown literally.")
    # also confirm fallback message.answer was NOT used (guest path returns early)
    print("fallback message.answer used?", bool(msg.answers))


if __name__ == "__main__":
    asyncio.run(main())
