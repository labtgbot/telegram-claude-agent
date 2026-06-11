import base64
import io
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

import bot.handlers.chat as chat
from bot.handlers.chat import handle_chat_message
from bot.utils.storage import MemoryStorage


def _contains_string(value, needle: str) -> bool:
    if isinstance(value, str):
        return needle in value
    if isinstance(value, dict):
        return any(_contains_string(item, needle) for item in value.values())
    if isinstance(value, list):
        return any(_contains_string(item, needle) for item in value)
    return False


def _bot_with_photo_download(image_bytes: bytes):
    return SimpleNamespace(
        username="testbot",
        get_me=AsyncMock(),
        get_file=AsyncMock(return_value=SimpleNamespace(file_path="photos/full.jpg")),
        download_file=AsyncMock(return_value=io.BytesIO(image_bytes)),
    )


def _make_photo_message(image_bytes: bytes, caption: str = "what is in this image?"):
    return SimpleNamespace(
        text=None,
        photo=[
            SimpleNamespace(file_id="small-photo"),
            SimpleNamespace(file_id="full-photo"),
        ],
        voice=None,
        document=None,
        caption=caption,
        reply_to_message=None,
        message_id=1,
        from_user=SimpleNamespace(id=42),
        chat=SimpleNamespace(id=100, type="private"),
        bot=_bot_with_photo_download(image_bytes),
        answer=AsyncMock(),
    )


def _make_text_message(text: str):
    return SimpleNamespace(
        text=text,
        photo=None,
        voice=None,
        document=None,
        caption=None,
        reply_to_message=None,
        message_id=2,
        from_user=SimpleNamespace(id=42),
        chat=SimpleNamespace(id=100, type="private"),
        bot=SimpleNamespace(username="testbot", get_me=AsyncMock()),
        answer=AsyncMock(),
    )


class _FakeProxyClient:
    calls = []

    def __init__(self, *args, **kwargs):
        pass

    async def send_message(self, *, messages, model, stream=False):
        self.__class__.calls.append(messages)
        return {"content": [{"type": "text", "text": "ok"}]}

    async def close(self):
        pass


@pytest.fixture
def patched_chat(monkeypatch):
    fresh_storage = MemoryStorage()
    monkeypatch.setattr(chat, "storage", fresh_storage)
    monkeypatch.setattr(chat, "ClaudeProxyClient", _FakeProxyClient)
    monkeypatch.setattr(chat.settings, "free_claude_streaming_enabled", False)
    monkeypatch.setattr(chat.settings, "telegram_chat_action_enabled", False)
    _FakeProxyClient.calls = []
    return fresh_storage


@pytest.mark.asyncio
async def test_photo_history_omits_base64_payload_and_next_turn_does_not_resend_it(
    patched_chat,
):
    image_bytes = b"fake image bytes"
    encoded_image = base64.b64encode(image_bytes).decode("utf-8")

    with patch.object(chat, "send_final_reply", new=AsyncMock()):
        await handle_chat_message(_make_photo_message(image_bytes))

    assert _contains_string(_FakeProxyClient.calls[0], encoded_image)
    history_after_photo = patched_chat.get_history(100, 42)
    assert not _contains_string(history_after_photo, encoded_image)
    assert history_after_photo[0]["content"][0] == {
        "type": "text",
        "text": "[image omitted from history]",
    }

    with patch.object(chat, "send_final_reply", new=AsyncMock()):
        await handle_chat_message(_make_text_message("continue"))

    assert len(_FakeProxyClient.calls) == 2
    assert not _contains_string(_FakeProxyClient.calls[1], encoded_image)
