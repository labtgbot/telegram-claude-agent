from bot.handlers.chat import _split_for_telegram, md_to_html

# code block: chunk0 should end with </code></pre>, chunk1 start with <pre><code>
code = "x = 1\n" * 1000
chunks = _split_for_telegram(md_to_html(f"```python\n{code}```"))
print("code chunk0 ends:", repr(chunks[0][-20:]))
print("code chunk1 starts:", repr(chunks[1][:20]))

# bold
chunks = _split_for_telegram(md_to_html(("a" * 4090) + "**boldtext**"))
print("\nbold chunk0 ends:", repr(chunks[0][-15:]))
print("bold chunk1:", repr(chunks[1]))

# entity not split
chunks = _split_for_telegram(md_to_html("x" * 4095 + "&" + "y" * 100))
print("\nentity chunk0 ends:", repr(chunks[0][-12:]))
print("entity chunk1 starts:", repr(chunks[1][:12]))

# Content round-trips: stripping reopened/closed pre/code wrappers
def strip_text(html):
    import re
    # remove tags
    t = re.sub(r"<[^>]+>", "", html)
    from html import unescape
    return unescape(t)

full = md_to_html(f"```python\n{code}```")
joined = "".join(strip_text(c) for c in _split_for_telegram(full))
print("\ncode text roundtrip:", joined == strip_text(full))
