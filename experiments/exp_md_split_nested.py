"""Probe the splitter on nested-tag scenarios and bold spans that themselves
exceed the limit, to find cases where a chunk still exceeds TELEGRAM_MESSAGE_LIMIT
or breaks nesting order.

Run: PYTHONPATH=. python experiments/exp_md_split_nested.py
"""
from html.parser import HTMLParser
from bot.handlers.chat import md_to_html, _split_for_telegram, TELEGRAM_MESSAGE_LIMIT


class V(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.ok = True
        self.why = None

    def handle_starttag(self, tag, attrs):
        self.stack.append(tag)

    def handle_endtag(self, tag):
        if not self.stack or self.stack[-1] != tag:
            self.ok = False
            self.why = f"mismatched </{tag}> stack={self.stack}"
        else:
            self.stack.pop()


def valid(html):
    v = V()
    v.feed(html)
    if v.stack:
        return f"UNCLOSED {v.stack}"
    if not v.ok:
        return v.why
    return None


def check(name, rendered):
    chunks = _split_for_telegram(rendered)
    print(f"--- {name}: rendered_len={len(rendered)} chunks={len(chunks)} ---")
    bad = False
    for idx, c in enumerate(chunks):
        err = valid(c)
        too_long = len(c) > TELEGRAM_MESSAGE_LIMIT
        if err or too_long:
            bad = True
            print(f"  chunk {idx}: len={len(c)} VALID={err is None} too_long={too_long} err={err}")
    print("  RESULT:", "PROBLEM" if bad else "ok")
    return chunks


# A single bold span far longer than the limit (no newlines inside).
check("huge bold span no newline", md_to_html("**" + ("Z" * 9000) + "**"))

# A single inline-code token whose rendered form exceeds the limit by itself.
check("huge inline code no newline", md_to_html("`" + ("Q" * 9000) + "`"))

# Reopen order: verify <pre><code> reopen sequence after a split.
ch = check("fenced code split", md_to_html("```\n" + ("abcd\n" * 2000) + "```"))
if len(ch) >= 2:
    print("  chunk1 prefix:", repr(ch[1][:25]))
