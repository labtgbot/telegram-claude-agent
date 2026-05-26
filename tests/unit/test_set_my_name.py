from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import SetMyName

from bot.handlers import commands
from bot.services.set_my_name import (
    SET_MY_NAME_LIMIT,
    SetMyNameValidationError,
    format_set_my_name_result,
    perform_set_my_name,
    sync_configured_bot_name,
    validate_bot_name,
)


def _message(text: str = "/setmyname Claude Agent", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_perform_set_my_name_uses_typed_aiogram_api():
    bot = SimpleNamespace(set_my_name=AsyncMock(return_value=True))

    result = await perform_set_my_name(
        bot,
        name=" Claude Agent ",
        language_code=" en ",
    )

    assert result is True
    bot.set_my_name.assert_awaited_once_with(
        name="Claude Agent",
        language_code="en",
    )


async def test_perform_set_my_name_reraises_bad_request():
    error = TelegramBadRequest(
        method=SetMyName(name="Claude Agent"),
        message="Bad Request: BOT_NAME_INVALID",
    )
    bot = SimpleNamespace(set_my_name=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_set_my_name(bot, name="Claude Agent")


async def test_perform_set_my_name_reraises_forbidden():
    error = TelegramForbiddenError(
        method=SetMyName(name="Claude Agent"),
        message="Forbidden: bot was blocked by the user",
    )
    bot = SimpleNamespace(set_my_name=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_set_my_name(bot, name="Claude Agent")


async def test_perform_set_my_name_rejects_too_long_name():
    bot = SimpleNamespace(set_my_name=AsyncMock())

    with pytest.raises(SetMyNameValidationError):
        await perform_set_my_name(bot, name="x" * (SET_MY_NAME_LIMIT + 1))

    bot.set_my_name.assert_not_awaited()


async def test_sync_configured_bot_name_skips_when_not_configured():
    bot = SimpleNamespace(set_my_name=AsyncMock())

    result = await sync_configured_bot_name(bot, name=None, language_code=None)

    assert result is False
    bot.set_my_name.assert_not_awaited()


async def test_sync_configured_bot_name_applies_configured_name():
    bot = SimpleNamespace(set_my_name=AsyncMock(return_value=True))

    result = await sync_configured_bot_name(
        bot,
        name="Claude Agent",
        language_code="ru",
    )

    assert result is True
    bot.set_my_name.assert_awaited_once_with(
        name="Claude Agent",
        language_code="ru",
    )


def test_validate_bot_name_allows_empty_string_for_clear():
    assert validate_bot_name("   ") == ""


def test_format_set_my_name_result_escapes_fields():
    text = format_set_my_name_result(
        name="Claude <Agent>",
        language_code="pt-BR",
    )

    assert "setMyName" in text
    assert "Claude &lt;Agent&gt;" in text
    assert "<code>pt-BR</code>" in text


async def test_cmd_set_my_name_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_set_my_name", AsyncMock())
    message = _message(chat_id=42)

    await commands.cmd_set_my_name(message)

    commands.perform_set_my_name.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_set_my_name_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_set_my_name", AsyncMock())
    message = _message(text="/setmyname", chat_id=42)

    await commands.cmd_set_my_name(message)

    commands.perform_set_my_name.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "setmyname usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_set_my_name_calls_service(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_set_my_name", AsyncMock(return_value=True))
    monkeypatch.setattr(commands, "format_set_my_name_result", lambda **_: "ok")
    message = _message(text="/setmyname Claude Agent language=en", chat_id=42)

    await commands.cmd_set_my_name(message)

    commands.perform_set_my_name.assert_awaited_once_with(
        message.bot,
        name="Claude Agent",
        language_code="en",
    )
    message.answer.assert_awaited_once_with("ok", parse_mode="HTML")


async def test_cmd_set_my_name_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(
        method=SetMyName(name="Claude Agent"),
        message="Bad Request: BOT_NAME_INVALID",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_set_my_name", AsyncMock(side_effect=error))
    message = _message(chat_id=42)

    await commands.cmd_set_my_name(message)

    args, _ = message.answer.await_args
    assert "Could not set bot name" in args[0]
    assert "BOT_NAME_INVALID" in args[0]


def test_parse_set_my_name_args_required_only():
    assert commands._parse_set_my_name_args("/setmyname Claude Agent") == (
        "Claude Agent",
        None,
    )


def test_parse_set_my_name_args_with_language_code():
    assert commands._parse_set_my_name_args(
        "/setmyname Claude Agent language=pt-BR"
    ) == ("Claude Agent", "pt-BR")


def test_parse_set_my_name_args_clear_with_language_code():
    assert commands._parse_set_my_name_args(
        "/setmyname --clear language=pt-BR"
    ) == ("", "pt-BR")


def test_parse_set_my_name_args_rejects_too_long_name():
    assert (
        commands._parse_set_my_name_args(
            "/setmyname " + "x" * (SET_MY_NAME_LIMIT + 1)
        )
        is None
    )
