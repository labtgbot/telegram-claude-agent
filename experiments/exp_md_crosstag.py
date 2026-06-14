"""Probe interactions between the bold/italic regexes and other emitted tags.

Hypotheses:
A) A single '*' that appears in plain prose on either side of a code span or a
   bold span can pull the '<' or '>' of those emitted tags into an italic
   capture, producing structurally broken / wrongly-nested HTML.
B) Asterisks emphasis wrapping content that contains an already-emitted <code>
   placeholder yields tags interleaved with <i>, breaking nesting.

We validate with a strict nesting checker (Telegram-like).

Run: PYTHONPATH=. python experiments/exp_md_crosstag.py
"""
from html.parser import HTMLParser
from bot.handlers.chat import md_to_html


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


cases = [
    # one stray star before bold, one after  -> italic captures across **..**
    ("stray stars around bold", "an * asterisk then **bold** and * another"),
    # stray stars around inline code
    ("stray stars around code", "a * b then `code` then c * d"),
    # emphasis literally wrapping an inline-code token
    ("italic wrapping code", "see *`x`* now"),
    # bold wrapping inline code (common: **`flag`**)
    ("bold wrapping code", "use **`--verbose`** flag"),
    # multiplication chain producing odd number of stars around a tag
    ("odd stars around bold", "2 * 3 and **x** and 4 * 5 and 6 * 7"),
]

for desc, text in cases:
    html = md_to_html(text)
    err = valid(html)
    print(f"--- {desc} ---")
    print("INPUT :", repr(text))
    print("OUTPUT:", repr(html))
    print("HTML VALID:", "YES" if err is None else f"NO -> {err}")
    print()
