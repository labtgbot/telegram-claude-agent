from bot.handlers.chat import _split_for_telegram, _strip_bot_mention, md_to_html


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
