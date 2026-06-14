"""Probe for VISIBLE-TEXT LOSS or duplication in _split_for_telegram across a
range of adversarial rendered inputs, including italic-mangled spans (stray <i>
from single '*') that straddle the split boundary.

We compare the concatenated visible text (tags stripped, entities unescaped) of
all chunks against the visible text of the whole rendered string.

Run: PYTHONPATH=. python experiments/exp_md_split_textloss.py
"""
from html.parser import HTMLParser
from bot.handlers.chat import md_to_html, _split_for_telegram, TELEGRAM_MESSAGE_LIMIT


def visible(html):
    out = []

    class P(HTMLParser):
        def handle_data(self, d):
            out.append(d)

    p = P()
    p.feed(html)
    return "".join(out)


def probe(name, rendered):
    chunks = _split_for_telegram(rendered)
    whole = visible(rendered)
    joined = "".join(visible(c) for c in chunks)
    loss = whole != joined
    overlong = [len(c) for c in chunks if len(c) > TELEGRAM_MESSAGE_LIMIT]
    print(f"--- {name}: rlen={len(rendered)} chunks={len(chunks)} ---")
    print("   text preserved:", not loss, "| overlong chunks:", overlong or "none")
    if loss:
        # show first divergence
        for i, (a, b) in enumerate(zip(whole, joined)):
            if a != b:
                print("   first diff at", i, "whole=", repr(whole[i:i+15]),
                      "joined=", repr(joined[i:i+15]))
                break
        print("   len(whole)=", len(whole), "len(joined)=", len(joined))


# 1) italic-mangled multiplication that crosses the boundary
probe("mangled italic across boundary",
      md_to_html("a * " + ("Z" * 4090) + " more * b"))

# 2) bold span that crosses the boundary repeatedly
probe("many bold spans",
      md_to_html("".join(f"**w{i}** " + "y" * 50 for i in range(120))))

# 3) text with many entities near the boundary
probe("entities near boundary",
      md_to_html("<&>" * 1500))

# 4) fenced code with no trailing newline before ```
probe("code no trailing newline",
      md_to_html("```\n" + ("c" * 9000) + "```"))

# 5) a long line with NO newline at all (forces non-newline cut)
probe("single long line no newline",
      md_to_html("Q" * 9000))
