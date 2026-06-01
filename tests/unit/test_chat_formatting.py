from html.parser import HTMLParser

from bot.handlers.chat import (
    TELEGRAM_MESSAGE_LIMIT,
    _split_for_telegram,
    _strip_bot_mention,
    md_to_html,
)


class _HtmlValidator(HTMLParser):
    """Minimal validator that flags unbalanced/mismatched Telegram HTML tags."""

    def __init__(self) -> None:
        super().__init__()
        self.stack: list[str] = []
        self.balanced = True

    def handle_starttag(self, tag, attrs):
        self.stack.append(tag)

    def handle_endtag(self, tag):
        if not self.stack or self.stack[-1] != tag:
            self.balanced = False
        else:
            self.stack.pop()


def _is_valid_html(chunk: str) -> bool:
    parser = _HtmlValidator()
    parser.feed(chunk)
    return parser.balanced and not parser.stack


def test_md_to_html_bold_italic_code():
    assert md_to_html("**bold**") == "<b>bold</b>"
    assert md_to_html("*italic*") == "<i>italic</i>"
    assert md_to_html("inline `code` here") == "inline <code>code</code> here"


def test_md_to_html_fenced_code_block_preserves_content():
    rendered = md_to_html("```python\nprint('hi')\n```")
    assert "<pre><code>" in rendered
    assert "print(&#x27;hi&#x27;)" in rendered or "print('hi')" in rendered


def test_md_to_html_escapes_raw_html():
    rendered = md_to_html("<script>alert(1)</script>")
    assert "<script>" not in rendered
    assert "&lt;script&gt;" in rendered


def test_md_to_html_handles_empty_string():
    assert md_to_html("") == ""


def test_strip_bot_mention_removes_leading_handle():
    assert _strip_bot_mention("@MyBot привет", "MyBot") == "привет"


def test_strip_bot_mention_keeps_text_if_no_handle():
    assert _strip_bot_mention("просто текст", "MyBot") == "просто текст"


def test_split_for_telegram_short_text_returns_single_chunk():
    assert _split_for_telegram("short") == ["short"]


def test_split_for_telegram_splits_long_text():
    text = ("a" * 4000) + "\n" + ("b" * 4000)
    parts = _split_for_telegram(text)
    assert len(parts) >= 2
    assert all(len(p) <= 4096 for p in parts)
    assert "".join(p for p in parts).replace("\n", "") == text.replace("\n", "")


def test_split_for_telegram_fenced_code_block_over_limit_stays_valid():
    """A >4096-char code block must split into balanced ``<pre><code>`` chunks."""
    rendered = md_to_html("```python\n" + ("x = 1\n" * 1000) + "```")
    parts = _split_for_telegram(rendered)
    assert len(parts) >= 2
    assert all(len(p) <= TELEGRAM_MESSAGE_LIMIT for p in parts)
    assert all(_is_valid_html(p) for p in parts)
    # Every chunk is wrapped in its own balanced code block.
    assert parts[0].rstrip().endswith("</code></pre>")
    assert parts[1].lstrip().startswith("<pre><code>")


def test_split_for_telegram_bold_span_crossing_boundary_stays_valid():
    """A bold span straddling the 4096 boundary must not break the tags."""
    rendered = md_to_html(("a" * 4090) + "**boldtext**")
    parts = _split_for_telegram(rendered)
    assert len(parts) >= 2
    assert all(len(p) <= TELEGRAM_MESSAGE_LIMIT for p in parts)
    assert all(_is_valid_html(p) for p in parts)
    # No chunk ends mid-tag like ``<b>bol``.
    assert all("<b>" not in p or "</b>" in p for p in parts)


def test_split_for_telegram_entity_at_boundary_not_split():
    """An HTML entity landing on the boundary must stay intact."""
    rendered = md_to_html("x" * 4095 + "&" + "y" * 100)
    parts = _split_for_telegram(rendered)
    assert len(parts) >= 2
    assert all(len(p) <= TELEGRAM_MESSAGE_LIMIT for p in parts)
    assert all(_is_valid_html(p) for p in parts)
    # The ``&amp;`` entity is never cut into ``&`` + ``amp;``.
    assert "&amp;" in "".join(parts)
    assert not any(p.endswith("&") for p in parts)


def test_split_for_telegram_preserves_visible_text():
    """Splitting must not lose or duplicate any visible content."""
    rendered = md_to_html("```\n" + ("line of code here\n" * 500) + "```")
    parts = _split_for_telegram(rendered)

    def visible(html: str) -> str:
        parser = _HtmlValidator()
        captured: list[str] = []
        parser.handle_data = captured.append  # type: ignore[method-assign]
        parser.feed(html)
        return "".join(captured)

    assert visible("".join(parts)) == visible(rendered)
