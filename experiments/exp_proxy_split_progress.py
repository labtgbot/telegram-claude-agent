"""
EXPERIMENT: _split_for_telegram termination & correctness on adversarial input.

Concerns:
 1. A single text run with no newline that exceeds the limit -> does it still
    make progress and never loop forever?
 2. A long unbroken token plus open tags whose close-tags alone approach the
    limit -> does cur_len + close_len accounting still progress?
 3. Output chunks each <= limit and HTML stays balanced per chunk?

We run with a small limit to stress it, asserting termination via a hard cap on
iterations and validating every chunk length + per-chunk tag balance.
"""
import os
os.environ.setdefault("FREE_CLAUDE_BASE_URL", "http://localhost")
os.environ.setdefault("FREE_CLAUDE_AUTH_TOKEN", "tok")
os.environ.setdefault("FREE_CLAUDE_DEFAULT_MODEL", "claude-x")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123:abc")

import re
import signal
from bot.handlers.chat import _split_for_telegram

TAG_RE = re.compile(r"</?([a-z]+)>")


def balanced(html):
    stack = []
    for m in TAG_RE.finditer(html):
        tag = m.group(1)
        if m.group(0).startswith("</"):
            if not stack or stack.pop() != tag:
                return False
        else:
            stack.append(tag)
    return not stack


def with_timeout(fn, seconds=5):
    def _handler(signum, frame):
        raise TimeoutError("split did not terminate")
    signal.signal(signal.SIGALRM, _handler)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        return fn()
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)


limit = 20
cases = {
    "long_no_newline": "x" * 100,
    "long_inside_bold": "<b>" + "y" * 100 + "</b>",
    "many_tags": "<b><i>" + "z" * 50 + "</i></b>",
    "newlines_then_long": "a\n" * 5 + "q" * 100,
    "single_long_token_gt_limit": "w" * 25,  # one run longer than the whole limit
}

for name, text in cases.items():
    try:
        chunks = with_timeout(lambda: _split_for_telegram(text, limit=limit))
    except TimeoutError as e:
        print(f"{name}: >>> NON-TERMINATION: {e}")
        continue
    over = [c for c in chunks if len(c) > limit]
    unbal = [c for c in chunks if not balanced(c)]
    joined_ok = "".join(re.sub(r"</?[bi]>", "", c) for c in chunks)  # rough sanity
    print(f"{name}: {len(chunks)} chunks; "
          f"max_len={max(len(c) for c in chunks)}; "
          f"over_limit={len(over)}; unbalanced={len(unbal)}")
    if over:
        print(f"   >>> chunk EXCEEDS limit (would 400 on Telegram): {over[:1]}")
    if unbal:
        print(f"   >>> unbalanced chunk: {unbal[:1]}")

print()
print("Note: chunks may legitimately exceed `limit` when a single atomic token")
print("(or its reopened tags) is itself longer than the limit; flagged above if so.")
