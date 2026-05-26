from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import GetMyDescription
from aiogram.types import BotDescription

from bot.handlers import commands
from bot.services.get_my_description import (
    audit_configured_bot_description,
    format_get_my_description_result,
    perform_get_my_description,
)


def _message(text: str = "/getmydescription", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_perform_get_my_description_uses_typed_aiogram_api():
    expected = BotDescription(description="Claude agent for Telegram")
    bot = SimpleNamespace(get_my_description=AsyncMock(return_value=expected))

    result = await perform_get_my_description(bot, language_code=" en ")

    assert result == expected
    bot.get_my_description.assert_awaited_once_with(language_code="en")


async def test_perform_get_my_description_reraises_bad_request():
    error = TelegramBadRequest(
        method=GetMyDescription(language_code="bad"),
        message="Bad Request: language code is invalid",
    )
    bot = SimpleNamespace(get_my_description=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_get_my_description(bot, language_code="bad")


async def test_perform_get_my_description_reraises_forbidden():
    error = TelegramForbiddenError(
        method=GetMyDescription(),
        message="Forbidden: bot was blocked by the user",
    )
    bot = SimpleNamespace(get_my_description=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_get_my_description(bot)


async def test_audit_configured_bot_description_fetches_language_variant():
    expected = BotDescription(description="Claude agent for Telegram")
    bot = SimpleNamespace(get_my_description=AsyncMock(return_value=expected))

    result = await audit_configured_bot_description(bot, language_code="ru")

    assert result == expected
    bot.get_my_description.assert_awaited_once_with(language_code="ru")


def test_format_get_my_description_result_escapes_fields():
    text = format_get_my_description_result(
        BotDescription(description="Claude <Agent>"),
        language_code="pt-BR",
    )

    assert "getMyDescription" in text
    assert "Claude &lt;Agent&gt;" in text
    assert "<code>pt-BR</code>" in text


async def test_cmd_get_my_description_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_get_my_description", AsyncMock())
    message = _message(chat_id=42)

    await commands.cmd_get_my_description(message)

    commands.perform_get_my_description.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_get_my_description_calls_service_with_defaults(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_get_my_description",
        AsyncMock(return_value=BotDescription(description="Claude Agent")),
    )
    monkeypatch.setattr(
        commands, "format_get_my_description_result", lambda *_, **__: "ok"
    )
    message = _message(text="/getmydescription", chat_id=42)

    await commands.cmd_get_my_description(message)

    commands.perform_get_my_description.assert_awaited_once_with(
        message.bot,
        language_code=None,
    )
    message.answer.assert_awaited_once_with("ok", parse_mode="HTML")


async def test_cmd_get_my_description_calls_service_with_language(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_get_my_description",
        AsyncMock(return_value=BotDescription(description="Claude Agent")),
    )
    monkeypatch.setattr(
        commands, "format_get_my_description_result", lambda *_, **__: "ok"
    )
    message = _message(text="/getmydescription language=en", chat_id=42)

    await commands.cmd_get_my_description(message)

    commands.perform_get_my_description.assert_awaited_once_with(
        message.bot,
        language_code="en",
    )
    message.answer.assert_awaited_once_with("ok", parse_mode="HTML")


async def test_cmd_get_my_description_shows_usage_for_invalid_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_get_my_description", AsyncMock())
    message = _message(text="/getmydescription scope=default", chat_id=42)

    await commands.cmd_get_my_description(message)

    commands.perform_get_my_description.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "getmydescription usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_get_my_description_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(
        method=GetMyDescription(language_code="bad"),
        message="Bad Request: language code is invalid",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_get_my_description", AsyncMock(side_effect=error)
    )
    message = _message(text="/getmydescription language=bad", chat_id=42)

    await commands.cmd_get_my_description(message)

    args, _ = message.answer.await_args
    assert "Could not get bot description" in args[0]
    assert "language code is invalid" in args[0]


def test_parse_get_my_description_args_defaults():
    assert commands._parse_get_my_description_args("/getmydescription") is None


def test_parse_get_my_description_args_supports_language():
    assert commands._parse_get_my_description_args(
        "/getmydescription language=uk"
    ) == "uk"


def test_parse_get_my_description_args_rejects_invalid_language():
    assert commands._parse_get_my_description_args(
        "/getmydescription language=*"
    ) is False
