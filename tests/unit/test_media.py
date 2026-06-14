import concurrent.futures
import sys
import threading
import time
import types

from bot.utils import media
from bot.utils.media import extract_document_text


def _clear_transcribe_model_cache():
    if hasattr(media._transcribe_sync, "model"):
        delattr(media._transcribe_sync, "model")


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


def test_transcribe_sync_loads_whisper_model_once_on_cold_cache(monkeypatch):
    workers = 8
    start_barrier = threading.Barrier(workers)
    original_named_temporary_file = media.tempfile.NamedTemporaryFile
    load_calls = []
    load_calls_lock = threading.Lock()

    class BarrierNamedTemporaryFile:
        def __init__(self, *args, **kwargs):
            self._temporary_file = original_named_temporary_file(*args, **kwargs)

        def __enter__(self):
            opened_file = self._temporary_file.__enter__()
            start_barrier.wait(timeout=5)
            return opened_file

        def __exit__(self, *args):
            return self._temporary_file.__exit__(*args)

    class FakeWhisperModel:
        def transcribe(self, path):
            return {"text": "ok"}

    def load_model(name):
        with load_calls_lock:
            load_calls.append(name)
        time.sleep(0.1)
        return FakeWhisperModel()

    _clear_transcribe_model_cache()
    monkeypatch.setattr(media.tempfile, "NamedTemporaryFile", BarrierNamedTemporaryFile)
    monkeypatch.setitem(
        sys.modules,
        "whisper",
        types.SimpleNamespace(load_model=load_model),
    )

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            results = list(
                executor.map(media._transcribe_sync, [b"fake voice"] * workers)
            )

        assert results == ["ok"] * workers
        assert load_calls == ["base"]
    finally:
        _clear_transcribe_model_cache()
