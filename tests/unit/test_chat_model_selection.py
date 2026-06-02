"""Tests that the chat pipeline honors the per-user model selection.

Regression coverage for issue #348: `/model <name>` and the inline model
buttons persist a choice via ``storage.set_setting(user_id, "model", ...)``,
but the chat pipeline never read that value — every request used
``settings.free_claude_default_model``. These tests assert that the proxy
client receives the per-user model id, falling back to the default only when
the user has not chosen one.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

import bot.handlers.chat as chat
from bot.handlers.chat import handle_chat_message
from bot.utils.storage import MemoryStorage


def _make_message(text="hello", user_id=42, chat_id=42):
    """Build a minimal private-chat ``Message`` stub for the chat handler."""
    bot = SimpleNamespace(username="testbot", get_me=AsyncMock())
    message = SimpleNamespace(
        text=text,
        photo=None,
        voice=None,
        document=None,
        caption=None,
        reply_to_message=None,
        message_id=1,
        from_user=SimpleNamespace(id=user_id),
        chat=SimpleNamespace(id=chat_id, type="private"),
        bot=bot,
        answer=AsyncMock(),
    )
    return message


class _FakeProxyClient:
    """Records the ``model`` passed to ``send_message`` and returns a canned reply."""

    last_model = None

    def __init__(self, *args, **kwargs):
        pass

    async def send_message(self, *, messages, model, stream=False):
        _FakeProxyClient.last_model = model
        return {"content": [{"type": "text", "text": "ok"}]}

    async def close(self):
        pass


@pytest.fixture
def patched_chat(monkeypatch):
    """Patch storage, the proxy client, and disable streaming for the handler."""
    fresh_storage = MemoryStorage()
    monkeypatch.setattr(chat, "storage", fresh_storage)
    monkeypatch.setattr(chat, "ClaudeProxyClient", _FakeProxyClient)
    monkeypatch.setattr(chat.settings, "free_claude_streaming_enabled", False)
    _FakeProxyClient.last_model = None
    return fresh_storage


@pytest.mark.asyncio
async def test_chat_uses_per_user_model(patched_chat):
    """A stored per-user model is sent to the proxy, not the default."""
    patched_chat.set_setting(42, "model", "claude-3-opus-20240229")

    message = _make_message(user_id=42)
    with patch.object(chat, "send_final_reply", new=AsyncMock()):
        await handle_chat_message(message)

    assert _FakeProxyClient.last_model == "claude-3-opus-20240229"
    assert _FakeProxyClient.last_model != chat.settings.free_claude_default_model


@pytest.mark.asyncio
async def test_chat_falls_back_to_default_model(patched_chat):
    """With no per-user model stored, the configured default is used."""
    message = _make_message(user_id=99)
    with patch.object(chat, "send_final_reply", new=AsyncMock()):
        await handle_chat_message(message)

    assert _FakeProxyClient.last_model == chat.settings.free_claude_default_model
