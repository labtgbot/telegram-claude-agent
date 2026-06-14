"""
EXPERIMENT: extract_document_text MIME matching is exact-equality only.

_extract_sync normalizes mime to strip()+lower() then compares with `==` for
"application/pdf" and "text/plain", and `in (...)` for the docx/word set.

Telegram (and many clients) frequently send a media type WITH parameters, e.g.
    "text/plain; charset=utf-8"
    "application/pdf; qs=0.001"
or with the document's own declared subtype. Because the code uses exact
equality, any parameterized MIME (very common for .txt) falls through to the
"unknown mime" branch and returns "" -> chat.py then tells the user
"Could not extract text from document", even for a perfectly valid UTF-8 text
file whose bytes decode fine.

We feed real, valid bytes with realistic parameterized MIME types and show the
extractor returns "" purely because of the strict equality check.
"""
import asyncio
import sys

sys.path.insert(0, ".")

from bot.utils.media import extract_document_text  # noqa: E402


async def main():
    valid_text = "Hello, this is a perfectly readable text file.".encode("utf-8")

    cases = [
        ("text/plain", valid_text),
        ("text/plain; charset=utf-8", valid_text),
        ("text/plain;charset=UTF-8", valid_text),
        ("TEXT/PLAIN; charset=utf-8", valid_text),
        ("text/markdown", "# title\nbody".encode("utf-8")),
        ("text/csv", "a,b\n1,2".encode("utf-8")),
    ]

    print(f"{'mime':40s} -> extracted")
    fail = []
    for mime, data in cases:
        out = await extract_document_text(mime, data)
        ok = bool(out.strip())
        shown = repr(out) if ok else "EMPTY"
        print(f"{mime:40s} -> {shown}")
        if not ok:
            fail.append(mime)

    print("\n=== RESULT ===")
    # Specifically the parameterized text/plain is the undeniable real-world bug.
    param_fail = [m for m in fail if m.lower().split(";")[0].strip() == "text/plain"]
    if param_fail:
        print(
            "BUG CONFIRMED: valid text/plain documents whose MIME carries "
            f"parameters fail extraction due to exact-equality matching: {param_fail}. "
            "Result: user gets 'Could not extract text from document' for a valid "
            ".txt file."
        )
    else:
        print("text/plain parameter handling OK.")
    print(
        "Note: text/markdown, text/csv etc. are also rejected, but those are "
        "arguably out of declared scope (only PDF/TXT/DOCX are advertised)."
    )


asyncio.run(main())
