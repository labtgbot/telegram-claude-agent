from html.parser import HTMLParser
from bot.handlers.chat import _split_for_telegram, md_to_html, TELEGRAM_MESSAGE_LIMIT

class Validator(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.ok = True
        self.err = None
    def handle_starttag(self, tag, attrs):
        self.stack.append(tag)
    def handle_endtag(self, tag):
        if not self.stack or self.stack[-1] != tag:
            self.ok = False
            self.err = f"mismatched </{tag}> stack={self.stack}"
        else:
            self.stack.pop()

def validate(chunk):
    v = Validator()
    v.feed(chunk)
    if v.stack:
        return f"unclosed {v.stack}"
    if not v.ok:
        return v.err
    return None

def check(name, rendered):
    chunks = _split_for_telegram(rendered)
    print(f"\n{name}: rendered={len(rendered)} chunks={len(chunks)}")
    all_ok = True
    for i, c in enumerate(chunks):
        err = validate(c)
        too_long = len(c) > TELEGRAM_MESSAGE_LIMIT
        status = "OK" if (err is None and not too_long) else f"BAD len={len(c)} err={err}"
        if err or too_long:
            all_ok = False
        print(f"  chunk {i}: len={len(c)} {status}")
    print(f"  => {'ALL VALID' if all_ok else 'INVALID'}")

# 1. Long fenced code block
code = "x = 1\n" * 1000
check("code block", md_to_html(f"```python\n{code}```"))
# 2. bold crossing boundary
check("bold span", md_to_html(("a" * 4090) + "**boldtext**"))
# 3. entity at boundary
check("entity boundary", md_to_html("x" * 4095 + "&" + "y" * 100))
# 4. plain text
check("plain", ("a" * 4000) + "\n" + ("b" * 4000))
