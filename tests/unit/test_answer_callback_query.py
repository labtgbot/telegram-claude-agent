from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import AnswerCallbackQuery

from bot.handlers import callbacks
from bot.services.answer_callback_query import (
    ANSWER_CALLBACK_QUERY_TEXT_LIMIT,
    AnswerCallbackQueryError,
    perform_answer_callback_query,
)


async def test_perform_answer_callback_query_uses_typed_aiogram_api():
    bot = SimpleNamespace(answer_callback_query=AsyncMock(return_value=True))

    result = await perform_answer_callback_query(
        bot,
        callback_query_id="callback-1",
        text="Done",
        show_alert=False,
        cache_time=0,
    )

    assert result is True
    bot.answer_callback_query.assert_awaited_once_with(
        callback_query_id="callback-1",
        text="Done",
        show_alert=False,
        url=None,
        cache_time=0,
    )


async def test_perform_answer_callback_query_rejects_missing_id():
    bot = SimpleNamespace(answer_callback_query=AsyncMock(return_value=True))

    with pytest.raises(AnswerCallbackQueryError):
        await perform_answer_callback_query(bot, callback_query_id="")

    bot.answer_callback_query.assert_not_awaited()


async def test_perform_answer_callback_query_rejects_too_long_text():
    bot = SimpleNamespace(answer_callback_query=AsyncMock(return_value=True))

    with pytest.raises(AnswerCallbackQueryError):
        await perform_answer_callback_query(
            bot,
            callback_query_id="callback-1",
            text="x" * (ANSWER_CALLBACK_QUERY_TEXT_LIMIT + 1),
        )

    bot.answer_callback_query.assert_not_awaited()


async def test_perform_answer_callback_query_reraises_telegram_errors():
    error = TelegramBadRequest(
        method=AnswerCallbackQuery(callback_query_id="callback-1"),
        message="Bad Request: query is too old",
    )
    bot = SimpleNamespace(answer_callback_query=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_answer_callback_query(bot, callback_query_id="callback-1")


def _query(data: str, chat_id: int = 42, user_id: int = 7):
    return SimpleNamespace(
        id="callback-1",
        data=data,
        from_user=SimpleNamespace(id=user_id),
        message=SimpleNamespace(chat=SimpleNamespace(id=chat_id), answer=AsyncMock()),
        bot=SimpleNamespace(answer_callback_query=AsyncMock(return_value=True)),
    )


async def test_model_callback_sets_user_model(monkeypatch):
    monkeypatch.setattr(callbacks.storage, "set_setting", Mock())
    query = _query("model:set:claude-3-opus")

    await callbacks.handle_model_set_callback(query)

    callbacks.storage.set_setting.assert_called_once_with(7, "model", "claude-3-opus")
    query.bot.answer_callback_query.assert_awaited_once()
    query.message.answer.assert_awaited_once_with("Model set to: claude-3-opus")


async def test_clear_history_callback_clears_current_chat_history(monkeypatch):
    monkeypatch.setattr(callbacks.storage, "clear_history", Mock())
    query = _query("history:clear", chat_id=100)

    await callbacks.handle_clear_history_callback(query)

    callbacks.storage.clear_history.assert_called_once_with(100, 7)
    query.bot.answer_callback_query.assert_awaited_once()
    query.message.answer.assert_awaited_once_with("Conversation history cleared.")


async def test_logout_callback_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(callbacks.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(callbacks, "perform_log_out", AsyncMock(return_value=True))
    query = _query("admin:logout:confirm", chat_id=42)

    await callbacks.handle_logout_confirm_callback(query)

    callbacks.perform_log_out.assert_not_awaited()
    query.bot.answer_callback_query.assert_awaited_once()
    _, kwargs = query.bot.answer_callback_query.await_args
    assert kwargs["show_alert"] is True


async def test_logout_callback_rejects_non_admin_user_in_admin_group(monkeypatch):
    monkeypatch.setattr(callbacks.settings, "telegram_admin_chat_ids", "-10042")
    monkeypatch.setattr(callbacks.settings, "telegram_admin_user_ids", "")
    monkeypatch.setattr(callbacks, "perform_log_out", AsyncMock(return_value=True))
    query = _query("admin:logout:confirm", chat_id=-10042, user_id=7)

    await callbacks.handle_logout_confirm_callback(query)

    callbacks.perform_log_out.assert_not_awaited()
    query.bot.answer_callback_query.assert_awaited_once()
    _, kwargs = query.bot.answer_callback_query.await_args
    assert kwargs["show_alert"] is True


async def test_logout_callback_performs_admin_action(monkeypatch):
    monkeypatch.setattr(callbacks.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(callbacks.settings, "telegram_admin_user_ids", "")
    monkeypatch.setattr(callbacks, "perform_log_out", AsyncMock(return_value=True))
    query = _query("admin:logout:confirm", chat_id=42, user_id=42)

    await callbacks.handle_logout_confirm_callback(query)

    callbacks.perform_log_out.assert_awaited_once_with(query.bot)
    query.bot.answer_callback_query.assert_awaited_once()
    query.message.answer.assert_awaited_once()


async def test_logout_callback_allows_admin_user_in_admin_group(monkeypatch):
    monkeypatch.setattr(callbacks.settings, "telegram_admin_chat_ids", "-10042")
    monkeypatch.setattr(callbacks.settings, "telegram_admin_user_ids", "7")
    monkeypatch.setattr(callbacks, "perform_log_out", AsyncMock(return_value=True))
    query = _query("admin:logout:confirm", chat_id=-10042, user_id=7)

    await callbacks.handle_logout_confirm_callback(query)

    callbacks.perform_log_out.assert_awaited_once_with(query.bot)
    query.bot.answer_callback_query.assert_awaited_once()
    query.message.answer.assert_awaited_once()
