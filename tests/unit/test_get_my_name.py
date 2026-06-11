from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import GetMyName
from aiogram.types import BotName

from bot.handlers import commands
from bot.services.get_my_name import (
    audit_configured_bot_name,
    format_get_my_name_result,
    perform_get_my_name,
)


def _message(text: str = "/getmyname", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_perform_get_my_name_uses_typed_aiogram_api():
    expected = BotName(name="Claude Agent")
    bot = SimpleNamespace(get_my_name=AsyncMock(return_value=expected))

    result = await perform_get_my_name(bot, language_code=" en ")

    assert result == expected
    bot.get_my_name.assert_awaited_once_with(language_code="en")


async def test_perform_get_my_name_reraises_bad_request():
    error = TelegramBadRequest(
        method=GetMyName(language_code="bad"),
        message="Bad Request: language code is invalid",
    )
    bot = SimpleNamespace(get_my_name=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_get_my_name(bot, language_code="bad")


async def test_perform_get_my_name_reraises_forbidden():
    error = TelegramForbiddenError(
        method=GetMyName(),
        message="Forbidden: bot was blocked by the user",
    )
    bot = SimpleNamespace(get_my_name=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_get_my_name(bot)


async def test_audit_configured_bot_name_fetches_language_variant():
    expected = BotName(name="Claude Agent")
    bot = SimpleNamespace(get_my_name=AsyncMock(return_value=expected))

    result = await audit_configured_bot_name(bot, language_code="ru")

    assert result == expected
    bot.get_my_name.assert_awaited_once_with(language_code="ru")


def test_format_get_my_name_result_escapes_fields():
    text = format_get_my_name_result(
        BotName(name="Claude <Agent>"),
        language_code="pt-BR",
    )

    assert "getMyName" in text
    assert "Claude &lt;Agent&gt;" in text
    assert "<code>pt-BR</code>" in text


async def test_cmd_get_my_name_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_get_my_name", AsyncMock())
    message = _message(chat_id=42)

    await commands.cmd_get_my_name(message)

    commands.perform_get_my_name.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_get_my_name_calls_service_with_defaults(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_get_my_name",
        AsyncMock(return_value=BotName(name="Claude Agent")),
    )
    monkeypatch.setattr(commands, "format_get_my_name_result", lambda *_, **__: "ok")
    message = _message(text="/getmyname", chat_id=42)

    await commands.cmd_get_my_name(message)

    commands.perform_get_my_name.assert_awaited_once_with(
        message.bot,
        language_code=None,
    )
    message.answer.assert_awaited_once_with("ok", parse_mode="HTML")


async def test_cmd_get_my_name_calls_service_with_language(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_get_my_name",
        AsyncMock(return_value=BotName(name="Claude Agent")),
    )
    monkeypatch.setattr(commands, "format_get_my_name_result", lambda *_, **__: "ok")
    message = _message(text="/getmyname language=en", chat_id=42)

    await commands.cmd_get_my_name(message)

    commands.perform_get_my_name.assert_awaited_once_with(
        message.bot,
        language_code="en",
    )
    message.answer.assert_awaited_once_with("ok", parse_mode="HTML")


async def test_cmd_get_my_name_shows_usage_for_invalid_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_get_my_name", AsyncMock())
    message = _message(text="/getmyname scope=default", chat_id=42)

    await commands.cmd_get_my_name(message)

    commands.perform_get_my_name.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "getmyname usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_get_my_name_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(
        method=GetMyName(language_code="bad"),
        message="Bad Request: language code is invalid",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_get_my_name", AsyncMock(side_effect=error))
    message = _message(text="/getmyname language=bad", chat_id=42)

    await commands.cmd_get_my_name(message)

    args, _ = message.answer.await_args
    assert "Could not get bot name" in args[0]
    assert "language code is invalid" not in args[0]
    assert "Please try again later" in args[0]


def test_parse_get_my_name_args_defaults():
    assert commands._parse_get_my_name_args("/getmyname") is None


def test_parse_get_my_name_args_supports_language():
    assert commands._parse_get_my_name_args("/getmyname language=uk") == "uk"


def test_parse_get_my_name_args_rejects_invalid_language():
    assert commands._parse_get_my_name_args("/getmyname language=*") is False
