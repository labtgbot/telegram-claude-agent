from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import SendDocument

from bot.handlers import commands
from bot.services.send_document import perform_send_document

DOCUMENT_URL = "https://example.com/report.pdf"


async def test_perform_send_document_uses_typed_aiogram_api():
    sent = SimpleNamespace(message_id=909)
    bot = SimpleNamespace(send_document=AsyncMock(return_value=sent))

    result = await perform_send_document(
        bot,
        chat_id=42,
        document=DOCUMENT_URL,
        caption="hello",
    )

    assert result is sent
    bot.send_document.assert_awaited_once_with(
        chat_id=42,
        document=DOCUMENT_URL,
        caption="hello",
        parse_mode=None,
        thumbnail=None,
        message_thread_id=None,
        disable_content_type_detection=None,
        disable_notification=None,
        protect_content=None,
    )


async def test_perform_send_document_reraises_telegram_errors():
    error = TelegramBadRequest(
        method=SendDocument(chat_id=1, document=DOCUMENT_URL),
        message="Bad Request: wrong file identifier/HTTP URL specified",
    )
    bot = SimpleNamespace(send_document=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_send_document(bot, chat_id=1, document=DOCUMENT_URL)


async def test_perform_send_document_reraises_forbidden():
    error = TelegramForbiddenError(
        method=SendDocument(chat_id=1, document=DOCUMENT_URL),
        message="Forbidden: bot was blocked by the user",
    )
    bot = SimpleNamespace(send_document=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_send_document(bot, chat_id=1, document=DOCUMENT_URL)


def _message(text: str = "/document", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_document_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_document", AsyncMock())
    message = _message(text=f"/document {DOCUMENT_URL}", chat_id=42)

    await commands.cmd_document(message)

    commands.perform_send_document.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_document_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_document", AsyncMock())
    message = _message(text="/document", chat_id=42)

    await commands.cmd_document(message)

    commands.perform_send_document.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "document usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_document_rejects_too_long_caption(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_document", AsyncMock())
    long_caption = "x" * (commands.DOCUMENT_CAPTION_LIMIT + 1)
    message = _message(text=f"/document {DOCUMENT_URL} {long_caption}", chat_id=42)

    await commands.cmd_document(message)

    commands.perform_send_document.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Caption is too long" in args[0]


async def test_cmd_document_sends_with_caption(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_send_document", AsyncMock(return_value=object())
    )
    message = _message(text=f"/document {DOCUMENT_URL} quarterly report", chat_id=42)

    await commands.cmd_document(message)

    commands.perform_send_document.assert_awaited_once_with(
        message.bot,
        chat_id=42,
        document=DOCUMENT_URL,
        caption="quarterly report",
    )
    args, _ = message.answer.await_args
    assert "Sent document with caption." in args[0]


async def test_cmd_document_sends_without_caption(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_send_document", AsyncMock(return_value=object())
    )
    message = _message(text=f"/document {DOCUMENT_URL}", chat_id=42)

    await commands.cmd_document(message)

    commands.perform_send_document.assert_awaited_once_with(
        message.bot,
        chat_id=42,
        document=DOCUMENT_URL,
        caption=None,
    )
    args, _ = message.answer.await_args
    assert args[0] == "Sent document."


async def test_cmd_document_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(
        method=SendDocument(chat_id=42, document=DOCUMENT_URL),
        message="Bad Request: wrong file identifier/HTTP URL specified",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_send_document", AsyncMock(side_effect=error)
    )
    message = _message(text=f"/document {DOCUMENT_URL}", chat_id=42)

    await commands.cmd_document(message)

    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Could not send the document" in args[0]
