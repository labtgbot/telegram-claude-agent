from bot.utils.media import extract_document_text


async def test_extract_plain_text():
    data = "Hello, world!".encode("utf-8")
    result = await extract_document_text("text/plain", data)
    assert result == "Hello, world!"


async def test_extract_plain_text_with_mime_parameters():
    data = "Hello, parameterized world!".encode("utf-8")
    for mime_type in (
        "text/plain; charset=utf-8",
        "text/plain;charset=UTF-8",
        "TEXT/PLAIN; charset=utf-8",
    ):
        result = await extract_document_text(mime_type, data)
        assert result == "Hello, parameterized world!"


async def test_extract_unknown_mime_returns_empty():
    result = await extract_document_text("application/octet-stream", b"\x00\x01")
    assert result == ""


async def test_extract_empty_plain_text():
    result = await extract_document_text("text/plain", b"")
    assert result == ""
