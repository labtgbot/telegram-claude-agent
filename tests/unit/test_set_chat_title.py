from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import SetChatTitle

from bot.handlers import commands
from bot.services.set_chat_title import (
    SET_CHAT_TITLE_LIMIT,
    format_set_chat_title_result,
    perform_set_chat_title,
)


def _message(text: str = "/setchattitle", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_perform_set_chat_title_uses_typed_aiogram_api():
    bot = SimpleNamespace(set_chat_title=AsyncMock(return_value=True))

    result = await perform_set_chat_title(
        bot,
        chat_id=-100123,
        title="Project Support",
    )

    assert result is True
    bot.set_chat_title.assert_awaited_once_with(
        chat_id=-100123,
        title="Project Support",
    )


async def test_perform_set_chat_title_reraises_bad_request():
    error = TelegramBadRequest(
        method=SetChatTitle(chat_id=-100123, title="Project Support"),
        message="Bad Request: CHAT_ADMIN_REQUIRED",
    )
    bot = SimpleNamespace(set_chat_title=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_set_chat_title(
            bot,
            chat_id=-100123,
            title="Project Support",
        )


async def test_perform_set_chat_title_reraises_forbidden():
    error = TelegramForbiddenError(
        method=SetChatTitle(chat_id=-100123, title="Project"),
        message="Forbidden: bot is not an administrator",
    )
    bot = SimpleNamespace(set_chat_title=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_set_chat_title(
            bot,
            chat_id=-100123,
            title="Project",
        )


def test_format_set_chat_title_result_escapes_fields():
    text = format_set_chat_title_result(
        chat_id=-100123,
        title="Support <&> operations",
    )

    assert "setChatTitle" in text
    assert "-100123" in text
    assert "Support &lt;&amp;&gt; operations" in text
    assert "chat title updated" in text


async def test_cmd_set_chat_title_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_set_chat_title", AsyncMock())
    message = _message(text="/setchattitle -100123 Project Support", chat_id=42)

    await commands.cmd_set_chat_title(message)

    commands.perform_set_chat_title.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_set_chat_title_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_set_chat_title", AsyncMock())
    message = _message(text="/setchattitle", chat_id=42)

    await commands.cmd_set_chat_title(message)

    commands.perform_set_chat_title.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "setchattitle usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_set_chat_title_calls_service(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_set_chat_title", AsyncMock(return_value=True))
    monkeypatch.setattr(commands, "format_set_chat_title_result", lambda **_: "ok")
    message = _message(text="/setchattitle -100123 Project Support", chat_id=42)

    await commands.cmd_set_chat_title(message)

    commands.perform_set_chat_title.assert_awaited_once_with(
        message.bot,
        chat_id=-100123,
        title="Project Support",
    )
    message.answer.assert_awaited_once_with("ok", parse_mode="HTML")


async def test_cmd_set_chat_title_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(
        method=SetChatTitle(chat_id=-100123, title="Project"),
        message="Bad Request: CHAT_ADMIN_REQUIRED",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_set_chat_title", AsyncMock(side_effect=error))
    message = _message(text="/setchattitle -100123 Project", chat_id=42)

    await commands.cmd_set_chat_title(message)

    args, _ = message.answer.await_args
    assert "Could not set the chat title" in args[0]
    assert "CHAT_ADMIN_REQUIRED" in args[0]


def test_parse_set_chat_title_args_required_only():
    result = commands._parse_set_chat_title_args("/setchattitle -100123 Project Support")

    assert result == (-100123, "Project Support")


def test_parse_set_chat_title_args_requires_title():
    assert commands._parse_set_chat_title_args("/setchattitle -100123") is None


def test_parse_set_chat_title_args_invalid_chat_id():
    assert commands._parse_set_chat_title_args("/setchattitle not-a-chat Project") is None


def test_parse_set_chat_title_args_rejects_too_long_title():
    text = "/setchattitle -100123 " + "x" * (SET_CHAT_TITLE_LIMIT + 1)

    assert commands._parse_set_chat_title_args(text) is None
