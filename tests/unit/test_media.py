import io
import pytest
from bot.utils.media import extract_document_text


def _make_pdf(text: str) -> bytes:
    """Create a minimal single-page PDF containing the given text."""
    from PyPDF2 import PdfWriter
    from reportlab.pdfgen import canvas  # type: ignore

    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(72, 720, text)
    c.save()
    buf.seek(0)
    return buf.read()


async def test_extract_plain_text():
    data = "Hello, world!".encode("utf-8")
    result = await extract_document_text("text/plain", data)
    assert result == "Hello, world!"


async def test_extract_unknown_mime_returns_empty():
    result = await extract_document_text("application/octet-stream", b"\x00\x01")
    assert result == ""


async def test_extract_empty_plain_text():
    result = await extract_document_text("text/plain", b"")
    assert result == ""
