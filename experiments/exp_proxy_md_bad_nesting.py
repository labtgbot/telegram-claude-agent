"""
EXPERIMENT: md_to_html emits improperly nested <b>/<i> for ***triple*** markdown.

Telegram Bot API HTML requires properly NESTED tags. '<b><i>x</b></i>' is
malformed (interleaved, not nested) and Telegram replies with HTTP 400
"Bad Request: can't parse entities". The handler then falls back to sending the
chunk WITHOUT parse_mode, so the user sees the literal '<b><i>...' markup.

We:
 1. show md_to_html('***both***') is interleaved, not nested,
 2. show the same for common LLM emphasis like '**_x_**'-ish patterns,
 3. demonstrate a minimal well-formed-nesting checker rejecting the output.
"""
import os
os.environ.setdefault("FREE_CLAUDE_BASE_URL", "http://localhost")
os.environ.setdefault("FREE_CLAUDE_AUTH_TOKEN", "tok")
os.environ.setdefault("FREE_CLAUDE_DEFAULT_MODEL", "claude-x")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123:abc")

import re
from bot.handlers.chat import md_to_html

TAG_RE = re.compile(r"</?([a-z]+)>")


def is_well_nested(html: str) -> bool:
    stack = []
    for m in TAG_RE.finditer(html):
        tag = m.group(1)
        if m.group(0).startswith("</"):
            if not stack or stack[-1] != tag:
                return False
            stack.pop()
        else:
            stack.append(tag)
    return not stack


cases = [
    "***both***",
    "Here is ***very important*** text",
    "***a*** and ***b***",
]

bad = 0
for src in cases:
    out = md_to_html(src)
    ok = is_well_nested(out)
    if not ok:
        bad += 1
    print(f"in : {src!r}")
    print(f"out: {out!r}")
    print(f"well-nested (Telegram-acceptable)? {ok}")
    print()

if bad:
    print(f">>> RESULT: {bad}/{len(cases)} produced INTERLEAVED tags like")
    print(">>>         '<b><i>both</b></i>'. Telegram parse_mode=HTML rejects these")
    print(">>>         with HTTP 400; the handler's fallback then posts the message")
    print(">>>         WITHOUT formatting, so the user sees literal '<b><i>' markup.")
    print(">>>         '***text***' is extremely common LLM Markdown (bold+italic).")
else:
    print(">>> All well-nested.")
