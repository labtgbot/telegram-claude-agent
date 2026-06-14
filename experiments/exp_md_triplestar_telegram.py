"""Confirm that md_to_html output for common LLM emphasis (***text***, and
combined **_bold italic_**) is INVALID per Telegram's documented HTML rules.

Telegram parses message HTML with a strict stack and requires proper nesting;
`<b><i>x</b></i>` is rejected with 'Bad Request: can't parse entities'.

We approximate Telegram's parser with aiogram's own HTML unparse/quote? aiogram
doesn't ship a strict validator, so we use a strict nesting checker AND print the
raw bytes so the wrong-nesting is unambiguous.

Run: PYTHONPATH=. python experiments/exp_md_triplestar_telegram.py
"""
from html.parser import HTMLParser
from bot.handlers.chat import md_to_html, _split_for_telegram


class Strict(HTMLParser):
    """Reject improperly nested tags exactly like Telegram does."""

    def __init__(self):
        super().__init__()
        self.stack = []
        self.error = None

    def handle_starttag(self, tag, attrs):
        self.stack.append(tag)

    def handle_endtag(self, tag):
        if not self.stack:
            self.error = f"closing </{tag}> with empty stack"
        elif self.stack[-1] != tag:
            self.error = f"improper nesting: </{tag}> but top of stack is <{self.stack[-1]}>"
        else:
            self.stack.pop()


def telegram_would_reject(html):
    p = Strict()
    p.feed(html)
    if p.error:
        return p.error
    if p.stack:
        return f"unclosed tags remain: {p.stack}"
    return None


samples = [
    "***bold italic***",
    "A heading: ***Important***\nbody text",
    "***a*** and ***b***",
    "mix **bold** *italic* ***both***",
]

for s in samples:
    html = md_to_html(s)
    reason = telegram_would_reject(html)
    print("INPUT :", repr(s))
    print("HTML  :", repr(html))
    if reason:
        print("  => TELEGRAM REJECTS: ", reason)
    else:
        print("  => ok")
    # also confirm the splitter does not rescue it (single-chunk path)
    chunks = _split_for_telegram(html)
    print("  chunks:", len(chunks), "(single-chunk path returns it verbatim:",
          chunks[0] == html, ")")
    print()
