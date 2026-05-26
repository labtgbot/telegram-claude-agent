from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import SetChatDescription

from bot.handlers import commands
from bot.services.set_chat_description import (
    SET_CHAT_DESCRIPTION_LIMIT,
    format_set_chat_description_result,
    perform_set_chat_description,
)


def _message(text: str = "/setchatdescription", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_perform_set_chat_description_uses_typed_aiogram_api():
    bot = SimpleNamespace(set_chat_description=AsyncMock(return_value=True))

    result = await perform_set_chat_description(
        bot,
        chat_id=-100123,
        description="Project support chat",
    )

    assert result is True
    bot.set_chat_description.assert_awaited_once_with(
        chat_id=-100123,
        description="Project support chat",
    )


async def test_perform_set_chat_description_reraises_bad_request():
    error = TelegramBadRequest(
        method=SetChatDescription(
            chat_id=-100123,
            description="Project support chat",
        ),
        message="Bad Request: CHAT_ADMIN_REQUIRED",
    )
    bot = SimpleNamespace(set_chat_description=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_set_chat_description(
            bot,
            chat_id=-100123,
            description="Project support chat",
        )


async def test_perform_set_chat_description_reraises_forbidden():
    error = TelegramForbiddenError(
        method=SetChatDescription(chat_id=-100123, description="Project"),
        message="Forbidden: bot is not an administrator",
    )
    bot = SimpleNamespace(set_chat_description=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_set_chat_description(
            bot,
            chat_id=-100123,
            description="Project",
        )


def test_format_set_chat_description_result_escapes_fields():
    text = format_set_chat_description_result(
        chat_id=-100123,
        description="Support <&> operations",
    )

    assert "setChatDescription" in text
    assert "-100123" in text
    assert "Support &lt;&amp;&gt; operations" in text
    assert "chat description updated" in text


def test_format_set_chat_description_result_marks_empty_description():
    text = format_set_chat_description_result(chat_id=-100123, description="")

    assert "<i>empty</i>" in text


async def test_cmd_set_chat_description_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_set_chat_description", AsyncMock())
    message = _message(
        text="/setchatdescription -100123 Project support chat",
        chat_id=42,
    )

    await commands.cmd_set_chat_description(message)

    commands.perform_set_chat_description.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_set_chat_description_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_set_chat_description", AsyncMock())
    message = _message(text="/setchatdescription", chat_id=42)

    await commands.cmd_set_chat_description(message)

    commands.perform_set_chat_description.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "setchatdescription usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_set_chat_description_calls_service(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_set_chat_description", AsyncMock(return_value=True)
    )
    monkeypatch.setattr(commands, "format_set_chat_description_result", lambda **_: "ok")
    message = _message(
        text="/setchatdescription -100123 Project support chat",
        chat_id=42,
    )

    await commands.cmd_set_chat_description(message)

    commands.perform_set_chat_description.assert_awaited_once_with(
        message.bot,
        chat_id=-100123,
        description="Project support chat",
    )
    message.answer.assert_awaited_once_with("ok", parse_mode="HTML")


async def test_cmd_set_chat_description_can_clear_description(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_set_chat_description", AsyncMock(return_value=True)
    )
    monkeypatch.setattr(commands, "format_set_chat_description_result", lambda **_: "ok")
    message = _message(text="/setchatdescription -100123", chat_id=42)

    await commands.cmd_set_chat_description(message)

    commands.perform_set_chat_description.assert_awaited_once_with(
        message.bot,
        chat_id=-100123,
        description="",
    )


async def test_cmd_set_chat_description_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(
        method=SetChatDescription(chat_id=-100123, description="Project"),
        message="Bad Request: CHAT_ADMIN_REQUIRED",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_set_chat_description", AsyncMock(side_effect=error)
    )
    message = _message(text="/setchatdescription -100123 Project", chat_id=42)

    await commands.cmd_set_chat_description(message)

    args, _ = message.answer.await_args
    assert "Could not set the chat description" in args[0]
    assert "CHAT_ADMIN_REQUIRED" in args[0]


def test_parse_set_chat_description_args_required_only():
    result = commands._parse_set_chat_description_args(
        "/setchatdescription -100123 Project support chat"
    )

    assert result == (-100123, "Project support chat")


def test_parse_set_chat_description_args_empty_description_clears():
    result = commands._parse_set_chat_description_args("/setchatdescription -100123")

    assert result == (-100123, "")


def test_parse_set_chat_description_args_invalid_chat_id():
    assert (
        commands._parse_set_chat_description_args(
            "/setchatdescription not-a-chat Project"
        )
        is None
    )


def test_parse_set_chat_description_args_rejects_too_long_description():
    text = "/setchatdescription -100123 " + "x" * (SET_CHAT_DESCRIPTION_LIMIT + 1)

    assert commands._parse_set_chat_description_args(text) is None
