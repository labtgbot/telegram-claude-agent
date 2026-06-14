from types import SimpleNamespace
from unittest.mock import AsyncMock

from bot.handlers import commands
from bot.utils.storage import MemoryStorage


def _message(text: str, user_id: int = 7):
    return SimpleNamespace(
        text=text,
        from_user=SimpleNamespace(id=user_id),
        chat=SimpleNamespace(id=user_id),
        answer=AsyncMock(),
    )


class _FakeClaudeProxyClient:
    closed = False

    def __init__(self, *args, **kwargs):
        pass

    async def list_models(self):
        return [
            "plain-model",
            "<b>evil</b>&broken",
        ]

    async def close(self):
        type(self).closed = True


async def test_model_command_escapes_current_and_listed_models(monkeypatch):
    storage = MemoryStorage()
    storage.set_setting(7, "model", "<i>current</i>&broken")
    _FakeClaudeProxyClient.closed = False
    monkeypatch.setattr(commands, "storage", storage)
    monkeypatch.setattr(commands, "ClaudeProxyClient", _FakeClaudeProxyClient)
    message = _message("/model")

    await commands.cmd_model(message)

    text = message.answer.await_args.args[0]
    assert "Current model: &lt;i&gt;current&lt;/i&gt;&amp;broken" in text
    assert "- plain-model" in text
    assert "- &lt;b&gt;evil&lt;/b&gt;&amp;broken" in text
    assert "<i>current</i>" not in text
    assert "<b>evil</b>" not in text
    assert _FakeClaudeProxyClient.closed is True


async def test_model_command_escapes_set_model_echo(monkeypatch):
    storage = MemoryStorage()
    monkeypatch.setattr(commands, "storage", storage)
    message = _message("/model <b>evil</b>&broken")

    await commands.cmd_model(message)

    assert storage.get_setting(7, "model") == "<b>evil</b>&broken"
    message.answer.assert_awaited_once_with(
        "Model set to: &lt;b&gt;evil&lt;/b&gt;&amp;broken"
    )


async def test_settings_command_escapes_current_model(monkeypatch):
    storage = MemoryStorage()
    storage.set_setting(7, "model", "<b>evil</b>&broken")
    monkeypatch.setattr(commands, "storage", storage)
    message = _message("/settings")

    await commands.cmd_settings(message)

    text = message.answer.await_args.args[0]
    assert "Model: &lt;b&gt;evil&lt;/b&gt;&amp;broken" in text
    assert "<b>evil</b>" not in text
