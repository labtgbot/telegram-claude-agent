"""
EXPERIMENT: Can model/user output break out of md_to_html into raw HTML, or
produce HTML that Telegram's parser rejects (causing the visible-error fallback)?

md_to_html order:
  1. extract ```fenced``` -> <pre><code>{escape(body)}</code></pre> placeholder
  2. extract `inline`     -> <code>{escape(body)}</code> placeholder
  3. html_escape(whole remaining text)
  4. **bold** -> <b>..</b>   (on escaped text)
  5. *italic* -> <i>..</i>   (on escaped text)
  6. restore placeholders

We probe a battery of adversarial inputs (the kind an LLM might emit, or a user
could coax it to emit) and check:
  - Does any raw '<script' / '<a href' / unescaped '<' survive into output?
  - Does the bold/italic substitution ever create UNBALANCED or NESTED tags that
    Telegram's HTML parser would reject (e.g. <b><b> or <i> without close)?

Telegram allows <b>,<i>,<code>,<pre>; it does NOT allow nested identical tags in
some clients and rejects malformed entities. We at least flag unbalanced tags.
"""
import os
os.environ.setdefault("FREE_CLAUDE_BASE_URL", "http://localhost")
os.environ.setdefault("FREE_CLAUDE_AUTH_TOKEN", "tok")
os.environ.setdefault("FREE_CLAUDE_DEFAULT_MODEL", "claude-x")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123:abc")

import re
from bot.handlers.chat import md_to_html

CASES = {
    "raw_script_tag": "<script>alert(1)</script>",
    "raw_anchor": '<a href="http://evil">click</a>',
    "img_onerror": '<img src=x onerror=alert(1)>',
    "bold_with_tag_inside": "**<b>x</b>**",
    "italic_unbalanced_star": "a * b",                      # single stray star
    "nested_bold_italic": "***both***",
    "bold_spanning_code": "**before `code` after**",
    "ampersand_entity": "Tom & Jerry < 5 > 3",
    "fake_entity": "100&euro; and &#xZZ; junk",
    "lt_in_text": "if a < b and b > c then",
    "star_at_edges": "*it works* but **bold** and *again*",
    "asterisk_math": "2 * 3 * 4 = 24",
    "pre_with_html": "```\n<div onclick='x'>hi</div>\n```",
}


def tag_balance(html: str):
    """Return list of (tag, opens, closes) for b/i/code/pre."""
    out = []
    for tag in ("b", "i", "code", "pre"):
        opens = len(re.findall(rf"<{tag}>", html))
        closes = len(re.findall(rf"</{tag}>", html))
        if opens != closes:
            out.append((tag, opens, closes))
    return out


print("=== md_to_html battery ===")
any_raw = False
any_unbalanced = False
for name, src in CASES.items():
    html = md_to_html(src)
    # any raw dangerous '<' that's NOT one of our allowed tags?
    raw_danger = re.findall(r"<(?!/?(?:b|i|code|pre)>)[^>]*>", html)
    bal = tag_balance(html)
    flag = ""
    if raw_danger:
        any_raw = True
        flag += " [RAW-HTML!]"
    if bal:
        any_unbalanced = True
        flag += f" [UNBALANCED {bal}]"
    print(f"\n{name}:")
    print(f"  in : {src!r}")
    print(f"  out: {html!r}{flag}")

print()
print("=== Summary ===")
print(f"Any raw/unescaped HTML survived: {any_raw}")
print(f"Any unbalanced allowed-tag output: {any_unbalanced}")
if any_unbalanced:
    print(">>> Unbalanced <b>/<i> output means Telegram parse_mode=HTML would 400,")
    print(">>>     triggering the plain-text fallback (so the user sees raw markup/")
    print(">>>     literal tags rather than formatting). Not an injection, but a")
    print(">>>     correctness/formatting bug for plausible LLM output.")
if not any_raw:
    print(">>> No raw HTML injection: html_escape neutralizes <script>/<a>/<img>. Good.")
