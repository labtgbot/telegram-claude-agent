"""Check what md_to_html emits for *unbalanced* / partial markdown and whether
Telegram's HTML parser would reject it. We validate with a strict stack-based
HTML checker (same idea Telegram uses: every opened tag must be closed and
properly nested).

Run: PYTHONPATH=. python experiments/exp_md_unbalanced.py
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
    ("unclosed bold", "Here is **bold without close"),
    ("unclosed italic", "Here is *italic without close"),
    ("nested bold inside italic via overlap", "*a **b** c*"),
    ("bold then stray single star", "**done** and 5 * 3"),
    ("triple star", "***wow***"),
    ("italic spanning a real tag region", "x **y** z * w * q"),
]

for desc, text in cases:
    html = md_to_html(text)
    err = valid(html)
    print(f"--- {desc} ---")
    print("INPUT :", repr(text))
    print("OUTPUT:", repr(html))
    print("HTML VALID:", "YES" if err is None else f"NO -> {err}")
    print()
