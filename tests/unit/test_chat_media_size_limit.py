import io
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import bot.handlers.chat as chat
from bot.handlers.chat import handle_chat_message
from bot.utils.storage import MemoryStorage


MEDIA_LIMIT_BYTES = 10


class _SettingsStub:
    allowed_chat_ids = []
    free_claude_base_url = "http://localhost:8082"
    free_claude_auth_token = "token"
    free_claude_default_model = "test-model"
    free_claude_streaming_enabled = False
    free_claude_timeout_seconds = 1
    telegram_chat_action_enabled = False
    telegram_guest_mode_enabled = True
    telegram_media_download_max_bytes = MEDIA_LIMIT_BYTES
    telegram_message_draft_enabled = False


class _FakeProxyClient:
    calls = []

    def __init__(self, *args, **kwargs):
        pass

    async def send_message(self, *, messages, model, stream=False):
        self.__class__.calls.append(messages)
        return {"content": [{"type": "text", "text": "ok"}]}

    async def close(self):
        pass


def _media_message(kind: str, *, file_size: int, payload: bytes = b"small file"):
    bot = SimpleNamespace(
        username="testbot",
        get_me=AsyncMock(),
        get_file=AsyncMock(
            return_value=SimpleNamespace(file_path=f"{kind}/file", file_size=file_size)
        ),
        download_file=AsyncMock(return_value=io.BytesIO(payload)),
    )
    message = SimpleNamespace(
        text=None,
        photo=None,
        voice=None,
        document=None,
        caption=None,
        reply_to_message=None,
        message_id=1,
        from_user=SimpleNamespace(id=42),
        chat=SimpleNamespace(id=100, type="private"),
        bot=bot,
        answer=AsyncMock(),
    )
    media = SimpleNamespace(
        file_id=f"{kind}-file-id",
        file_name=f"{kind}.txt",
        file_size=file_size,
        mime_type="text/plain",
    )
    if kind == "photo":
        message.photo = [media]
    elif kind == "voice":
        message.voice = media
    elif kind == "document":
        message.document = media
    else:
        raise AssertionError(f"unknown media kind: {kind}")
    return message


@pytest.fixture
def patched_chat(monkeypatch):
    monkeypatch.setattr(chat, "settings", _SettingsStub())
    monkeypatch.setattr(chat, "storage", MemoryStorage())
    monkeypatch.setattr(chat, "ClaudeProxyClient", _FakeProxyClient)
    monkeypatch.setattr(chat, "transcribe_voice", AsyncMock(return_value="voice text"))
    monkeypatch.setattr(chat, "extract_document_text", AsyncMock(return_value="document text"))
    _FakeProxyClient.calls = []


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["photo", "voice", "document"])
async def test_oversized_media_is_rejected_before_download(patched_chat, kind):
    message = _media_message(kind, file_size=MEDIA_LIMIT_BYTES + 1)

    await handle_chat_message(message)

    message.bot.get_file.assert_not_awaited()
    message.bot.download_file.assert_not_awaited()
    assert _FakeProxyClient.calls == []
    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "too large" in args[0]
    assert "10 bytes" in args[0]


@pytest.mark.asyncio
async def test_media_at_configured_limit_is_downloaded(patched_chat):
    message = _media_message("document", file_size=MEDIA_LIMIT_BYTES)

    await handle_chat_message(message)

    message.bot.get_file.assert_awaited_once_with("document-file-id")
    message.bot.download_file.assert_awaited_once_with("document/file")
    assert _FakeProxyClient.calls


@pytest.mark.asyncio
async def test_oversized_get_file_result_is_rejected_before_download(patched_chat):
    message = _media_message("document", file_size=0)
    message.document.file_size = None
    message.bot.get_file.return_value.file_size = MEDIA_LIMIT_BYTES + 1

    await handle_chat_message(message)

    message.bot.get_file.assert_awaited_once_with("document-file-id")
    message.bot.download_file.assert_not_awaited()
    assert _FakeProxyClient.calls == []
    message.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_oversized_download_without_metadata_is_rejected_after_read(patched_chat):
    message = _media_message("document", file_size=0, payload=b"x" * (MEDIA_LIMIT_BYTES + 1))
    message.document.file_size = None
    message.bot.get_file.return_value.file_size = None

    await handle_chat_message(message)

    message.bot.get_file.assert_awaited_once_with("document-file-id")
    message.bot.download_file.assert_awaited_once_with("document/file")
    assert _FakeProxyClient.calls == []
    message.answer.assert_awaited_once()
