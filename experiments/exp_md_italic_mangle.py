"""Prove that the italic regex mangles text containing single '*' used for
multiplication / math / glob paths, producing wrong (and sometimes invalid)
Telegram HTML.

Run: PYTHONPATH=. python experiments/exp_md_italic_mangle.py
"""
from bot.handlers.chat import md_to_html

cases = [
    # (description, llm_text)
    ("multiplication across lines",
     "The area is a * b where a=2.\nThen multiply c * d to get the result."),
    ("glob path list",
     "Run on src/*.py and tests/*.py to lint everything."),
    ("two separate emphasised words",
     "This is *really* and *very* important."),
    ("single unmatched star (unclosed emphasis)",
     "Use 5 * 3 = 15 in your head."),
    ("markdown bullet list with asterisks",
     "Shopping list:\n* milk\n* eggs\n* bread"),
]

for desc, text in cases:
    html = md_to_html(text)
    print(f"--- {desc} ---")
    print("INPUT :", repr(text))
    print("OUTPUT:", repr(html))
    # crude check: did we wrap unintended spans in <i>?
    print("contains <i>:", "<i>" in html)
    print()
