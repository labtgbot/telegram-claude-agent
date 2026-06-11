from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import GetWebhookInfo, LogOut

import bot.handlers.callbacks as callbacks
import bot.handlers.chat as chat
from bot.handlers import commands
from bot.services.get_custom_emoji_stickers import GetCustomEmojiStickersValidationError
from bot.services.stop_poll import StopPollValidationError


INTERNAL_ERROR = "proxy failed at http://internal-proxy.local/v1/messages"


def _message(text: str = "hello", user_id: int = 42, chat_id: int = 42):
    bot = SimpleNamespace(username="testbot", get_me=AsyncMock())
    return SimpleNamespace(
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


class _FailingProxyClient:
    def __init__(self, *args, **kwargs):
        pass

    async def send_message(self, *args, **kwargs):
        raise RuntimeError(INTERNAL_ERROR)

    async def close(self):
        pass


@pytest.mark.asyncio
async def test_streaming_handler_does_not_expose_internal_exception_text():
    sent_message = SimpleNamespace(edit_text=AsyncMock())
    message = SimpleNamespace(answer=AsyncMock(return_value=sent_message))
    client = _FailingProxyClient()

    with pytest.raises(RuntimeError):
        await chat.handle_streaming(message, client, [], "claude-test")

    sent_message.edit_text.assert_awaited_once()
    args, _ = sent_message.edit_text.await_args
    assert "❌ Error" in args[0]
    assert INTERNAL_ERROR not in args[0]
    assert "http://internal-proxy.local" not in args[0]


@pytest.mark.asyncio
async def test_chat_handler_does_not_expose_internal_exception_text(monkeypatch):
    monkeypatch.setattr(chat, "ClaudeProxyClient", _FailingProxyClient)
    monkeypatch.setattr(chat.settings, "free_claude_streaming_enabled", False)
    monkeypatch.setattr(chat.settings, "telegram_chat_action_enabled", False)
    message = _message()

    await chat.handle_chat_message(message)

    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "❌ Error" in args[0]
    assert INTERNAL_ERROR not in args[0]
    assert "http://internal-proxy.local" not in args[0]


@pytest.mark.asyncio
async def test_command_handler_does_not_expose_internal_exception_text(monkeypatch):
    error = TelegramBadRequest(method=GetWebhookInfo(), message=INTERNAL_ERROR)
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "")
    monkeypatch.setattr(commands, "fetch_webhook_info", AsyncMock(side_effect=error))
    message = SimpleNamespace(chat=SimpleNamespace(id=42), bot=object(), answer=AsyncMock())

    await commands.cmd_webhook_info(message)

    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Could not fetch webhook diagnostics" in args[0]
    assert INTERNAL_ERROR not in args[0]
    assert "http://internal-proxy.local" not in args[0]


@pytest.mark.asyncio
async def test_command_validation_error_does_not_expose_exception_text(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_stop_poll",
        AsyncMock(side_effect=StopPollValidationError(INTERNAL_ERROR)),
    )
    message = SimpleNamespace(
        text="/stoppoll -100123 777",
        chat=SimpleNamespace(id=42),
        bot=object(),
        answer=AsyncMock(),
    )

    await commands.cmd_stop_poll(message)

    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Invalid stopPoll request" in args[0]
    assert INTERNAL_ERROR not in args[0]
    assert "http://internal-proxy.local" not in args[0]


@pytest.mark.asyncio
async def test_custom_emoji_validation_error_does_not_expose_exception_text(
    monkeypatch,
):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_get_custom_emoji_stickers",
        AsyncMock(side_effect=GetCustomEmojiStickersValidationError(INTERNAL_ERROR)),
    )
    message = SimpleNamespace(
        text="/customemojistickers id-1",
        chat=SimpleNamespace(id=42),
        bot=object(),
        answer=AsyncMock(),
    )

    await commands.cmd_custom_emoji_stickers(message)

    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Custom emoji sticker requests" in args[0]
    assert INTERNAL_ERROR not in args[0]
    assert "http://internal-proxy.local" not in args[0]


@pytest.mark.asyncio
async def test_callback_handler_does_not_expose_internal_exception_text(monkeypatch):
    error = TelegramBadRequest(method=LogOut(), message=INTERNAL_ERROR)
    monkeypatch.setattr(callbacks.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(callbacks, "perform_log_out", AsyncMock(side_effect=error))
    monkeypatch.setattr(callbacks, "perform_answer_callback_query", AsyncMock())
    message = SimpleNamespace(chat=SimpleNamespace(id=42), answer=AsyncMock())
    query = SimpleNamespace(
        id="callback-id",
        data=callbacks.CALLBACK_LOGOUT_CONFIRM,
        bot=object(),
        message=message,
    )

    await callbacks.handle_logout_confirm_callback(query)

    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Could not log out from the cloud Bot API" in args[0]
    assert INTERNAL_ERROR not in args[0]
    assert "http://internal-proxy.local" not in args[0]
