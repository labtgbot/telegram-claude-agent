"""Show that the italic regex can not only mangle but combine with bold to
produce structurally INVALID (overlapping) HTML in realistic LLM prose, beyond
the ***...*** case.

Also: a single stray '*' inside a **bold** region's text can split the bold
capture such that '<i>' opens but the matching '</i>' lands outside the bold,
creating overlap.

Run: PYTHONPATH=. python experiments/exp_md_italic_invalid.py
"""
from html.parser import HTMLParser
from bot.handlers.chat import md_to_html


class Strict(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.error = None

    def handle_starttag(self, tag, attrs):
        self.stack.append(tag)

    def handle_endtag(self, tag):
        if not self.stack or self.stack[-1] != tag:
            self.error = f"overlap/mismatch </{tag}> stack={self.stack}"
        else:
            self.stack.pop()


def reject(html):
    p = Strict()
    p.feed(html)
    return p.error or (f"unclosed {p.stack}" if p.stack else None)


cases = [
    # bold whose inner text contains a stray pair of stars far apart
    ("stars inside bold prose",
     "**Compute a * b first, then c * d at the end**"),
    # an asterisk just before a bold open and inside it
    ("star then bold with inner star",
     "value * and **x * y** done"),
    # heading-style triple, very common from LLMs
    ("triple star heading", "## ***Summary***"),
    # bold-italic markdown the GitHub way
    ("github bold italic", "**_strong emphasis_**"),
    ("github italic bold", "_**strong emphasis**_"),
]

any_bad = False
for desc, text in cases:
    html = md_to_html(text)
    why = reject(html)
    bad = why is not None
    any_bad = any_bad or bad
    print(f"--- {desc} ---")
    print("INPUT :", repr(text))
    print("OUTPUT:", repr(html))
    print("TELEGRAM:", "REJECTS -> " + why if bad else "accepts")
    print()

print("ANY INVALID OUTPUT:", any_bad)
