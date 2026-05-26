from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import SetMyDescription

from bot.handlers import commands
from bot.services.set_my_description import (
    SET_MY_DESCRIPTION_LIMIT,
    SetMyDescriptionValidationError,
    format_set_my_description_result,
    perform_set_my_description,
    sync_configured_bot_description,
    validate_bot_description,
)


def _message(text: str = "/setmydescription Claude agent for Telegram", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_perform_set_my_description_uses_typed_aiogram_api():
    bot = SimpleNamespace(set_my_description=AsyncMock(return_value=True))

    result = await perform_set_my_description(
        bot,
        description=" Claude agent for Telegram ",
        language_code=" en ",
    )

    assert result is True
    bot.set_my_description.assert_awaited_once_with(
        description="Claude agent for Telegram",
        language_code="en",
    )


async def test_perform_set_my_description_reraises_bad_request():
    error = TelegramBadRequest(
        method=SetMyDescription(description="Claude agent for Telegram"),
        message="Bad Request: DESCRIPTION_INVALID",
    )
    bot = SimpleNamespace(set_my_description=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_set_my_description(bot, description="Claude agent for Telegram")


async def test_perform_set_my_description_reraises_forbidden():
    error = TelegramForbiddenError(
        method=SetMyDescription(description="Claude agent for Telegram"),
        message="Forbidden: bot was blocked by the user",
    )
    bot = SimpleNamespace(set_my_description=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_set_my_description(bot, description="Claude agent for Telegram")


async def test_perform_set_my_description_rejects_too_long_description():
    bot = SimpleNamespace(set_my_description=AsyncMock())

    with pytest.raises(SetMyDescriptionValidationError):
        await perform_set_my_description(
            bot,
            description="x" * (SET_MY_DESCRIPTION_LIMIT + 1),
        )

    bot.set_my_description.assert_not_awaited()


async def test_sync_configured_bot_description_skips_when_not_configured():
    bot = SimpleNamespace(set_my_description=AsyncMock())

    result = await sync_configured_bot_description(
        bot,
        description=None,
        language_code=None,
    )

    assert result is False
    bot.set_my_description.assert_not_awaited()


async def test_sync_configured_bot_description_applies_configured_description():
    bot = SimpleNamespace(set_my_description=AsyncMock(return_value=True))

    result = await sync_configured_bot_description(
        bot,
        description="Claude agent for Telegram",
        language_code="ru",
    )

    assert result is True
    bot.set_my_description.assert_awaited_once_with(
        description="Claude agent for Telegram",
        language_code="ru",
    )


def test_validate_bot_description_allows_empty_string_for_clear():
    assert validate_bot_description("   ") == ""


def test_format_set_my_description_result_escapes_fields():
    text = format_set_my_description_result(
        description="Claude <Agent>",
        language_code="pt-BR",
    )

    assert "setMyDescription" in text
    assert "Claude &lt;Agent&gt;" in text
    assert "<code>pt-BR</code>" in text


async def test_cmd_set_my_description_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_set_my_description", AsyncMock())
    message = _message(chat_id=42)

    await commands.cmd_set_my_description(message)

    commands.perform_set_my_description.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_set_my_description_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_set_my_description", AsyncMock())
    message = _message(text="/setmydescription", chat_id=42)

    await commands.cmd_set_my_description(message)

    commands.perform_set_my_description.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "setmydescription usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_set_my_description_calls_service(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_set_my_description",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(commands, "format_set_my_description_result", lambda **_: "ok")
    message = _message(
        text="/setmydescription Claude agent for Telegram language=en",
        chat_id=42,
    )

    await commands.cmd_set_my_description(message)

    commands.perform_set_my_description.assert_awaited_once_with(
        message.bot,
        description="Claude agent for Telegram",
        language_code="en",
    )
    message.answer.assert_awaited_once_with("ok", parse_mode="HTML")


async def test_cmd_set_my_description_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(
        method=SetMyDescription(description="Claude agent for Telegram"),
        message="Bad Request: DESCRIPTION_INVALID",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_set_my_description",
        AsyncMock(side_effect=error),
    )
    message = _message(chat_id=42)

    await commands.cmd_set_my_description(message)

    args, _ = message.answer.await_args
    assert "Could not set bot description" in args[0]
    assert "DESCRIPTION_INVALID" in args[0]


def test_parse_set_my_description_args_required_only():
    assert commands._parse_set_my_description_args(
        "/setmydescription Claude agent for Telegram"
    ) == (
        "Claude agent for Telegram",
        None,
    )


def test_parse_set_my_description_args_with_language_code():
    assert commands._parse_set_my_description_args(
        "/setmydescription Claude agent for Telegram language=pt-BR"
    ) == ("Claude agent for Telegram", "pt-BR")


def test_parse_set_my_description_args_clear_with_language_code():
    assert commands._parse_set_my_description_args(
        "/setmydescription --clear language=pt-BR"
    ) == ("", "pt-BR")


def test_parse_set_my_description_args_rejects_too_long_description():
    assert (
        commands._parse_set_my_description_args(
            "/setmydescription " + "x" * (SET_MY_DESCRIPTION_LIMIT + 1)
        )
        is None
    )
