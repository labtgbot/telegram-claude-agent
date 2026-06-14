"""Trace the failure/fallback behaviour for invalid HTML in the three send paths.

We don't have a live Telegram, so we MODEL Telegram's HTML validation with a
strict nesting parser (this matches Telegram's documented behaviour: overlapping
tags are rejected with 'can't parse entities'). Then we replay the exact control
flow of:
  - send_reply_safely        (per-chunk try HTML, except -> answer plain)
  - handle_streaming final   (edit_text HTML, except -> edit_text plain TRUNCATED, then extra chunks)
to show which user-visible text the recipient ends up seeing.

Run: PYTHONPATH=. python experiments/exp_md_fallback_path.py
"""
from html.parser import HTMLParser
from bot.handlers.chat import md_to_html, _split_for_telegram


class Strict(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.error = None

    def handle_starttag(self, tag, attrs):
        self.stack.append(tag)

    def handle_endtag(self, tag):
        if not self.stack:
            self.error = f"closing </{tag}> empty stack"
        elif self.stack[-1] != tag:
            self.error = f"improper nesting </{tag}> over <{self.stack[-1]}>"
        else:
            self.stack.pop()


def telegram_accepts_html(html):
    p = Strict()
    try:
        p.feed(html)
    except Exception as e:  # malformed enough to crash parser
        return False, f"parser crash: {e}"
    if p.error:
        return False, p.error
    if p.stack:
        return False, f"unclosed {p.stack}"
    return True, None


def simulate_send_reply_safely(rendered):
    """Mirror send_reply_safely: split, try HTML per chunk, fallback to PLAIN."""
    sent = []
    for chunk in _split_for_telegram(rendered):
        ok, why = telegram_accepts_html(chunk)
        if ok:
            sent.append(("HTML", chunk))
        else:
            # except branch: message.answer(chunk) with bot default parse_mode=HTML!
            # The fallback re-sends the SAME chunk; default parse_mode is still HTML.
            ok2, why2 = telegram_accepts_html(chunk)
            sent.append(("PLAIN-FALLBACK", chunk, "still-HTML-default", ok2, why2))
    return sent


# Case: LLM emitted '***Important***' heading -> invalid nesting
text = "Here is the answer.\n\n***Important note*** about your code."
rendered = md_to_html(text)
print("rendered:", repr(rendered))
ok, why = telegram_accepts_html(rendered)
print("Telegram accepts rendered HTML:", ok, why)
print()
print("send_reply_safely simulation:")
for entry in simulate_send_reply_safely(rendered):
    print("  ", entry)
print()
print("KEY POINT: the fallback `await message.answer(chunk)` in send_reply_safely")
print("does NOT pass parse_mode=None, and bot default parse_mode is HTML")
print("(bot/main.py:126 DefaultBotProperties(parse_mode=ParseMode.HTML)).")
print("So the fallback re-send is ALSO parsed as HTML and fails again ->")
print("the user receives NOTHING for that chunk.")
