from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import SetMyShortDescription

from bot.handlers import commands
from bot.services.set_my_short_description import (
    SET_MY_SHORT_DESCRIPTION_LIMIT,
    SetMyShortDescriptionValidationError,
    format_set_my_short_description_result,
    perform_set_my_short_description,
    sync_configured_bot_short_description,
    validate_bot_short_description,
)


def _message(
    text: str = "/setmyshortdescription Claude agent",
    chat_id: int = 42,
):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_perform_set_my_short_description_uses_typed_aiogram_api():
    bot = SimpleNamespace(set_my_short_description=AsyncMock(return_value=True))

    result = await perform_set_my_short_description(
        bot,
        short_description=" Claude agent ",
        language_code=" en ",
    )

    assert result is True
    bot.set_my_short_description.assert_awaited_once_with(
        short_description="Claude agent",
        language_code="en",
    )


async def test_perform_set_my_short_description_reraises_bad_request():
    error = TelegramBadRequest(
        method=SetMyShortDescription(short_description="Claude agent"),
        message="Bad Request: SHORT_DESCRIPTION_INVALID",
    )
    bot = SimpleNamespace(set_my_short_description=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_set_my_short_description(bot, short_description="Claude agent")


async def test_perform_set_my_short_description_reraises_forbidden():
    error = TelegramForbiddenError(
        method=SetMyShortDescription(short_description="Claude agent"),
        message="Forbidden: bot was blocked by the user",
    )
    bot = SimpleNamespace(set_my_short_description=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_set_my_short_description(bot, short_description="Claude agent")


async def test_perform_set_my_short_description_rejects_too_long_description():
    bot = SimpleNamespace(set_my_short_description=AsyncMock())

    with pytest.raises(SetMyShortDescriptionValidationError):
        await perform_set_my_short_description(
            bot,
            short_description="x" * (SET_MY_SHORT_DESCRIPTION_LIMIT + 1),
        )

    bot.set_my_short_description.assert_not_awaited()


async def test_sync_configured_bot_short_description_skips_when_not_configured():
    bot = SimpleNamespace(set_my_short_description=AsyncMock())

    result = await sync_configured_bot_short_description(
        bot,
        short_description=None,
        language_code=None,
    )

    assert result is False
    bot.set_my_short_description.assert_not_awaited()


async def test_sync_configured_bot_short_description_applies_configured_description():
    bot = SimpleNamespace(set_my_short_description=AsyncMock(return_value=True))

    result = await sync_configured_bot_short_description(
        bot,
        short_description="Claude agent",
        language_code="ru",
    )

    assert result is True
    bot.set_my_short_description.assert_awaited_once_with(
        short_description="Claude agent",
        language_code="ru",
    )


def test_validate_bot_short_description_allows_empty_string_for_clear():
    assert validate_bot_short_description("   ") == ""


def test_format_set_my_short_description_result_escapes_fields():
    text = format_set_my_short_description_result(
        short_description="Claude <Agent>",
        language_code="pt-BR",
    )

    assert "setMyShortDescription" in text
    assert "Claude &lt;Agent&gt;" in text
    assert "<code>pt-BR</code>" in text


async def test_cmd_set_my_short_description_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_set_my_short_description", AsyncMock())
    message = _message(chat_id=42)

    await commands.cmd_set_my_short_description(message)

    commands.perform_set_my_short_description.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_set_my_short_description_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_set_my_short_description", AsyncMock())
    message = _message(text="/setmyshortdescription", chat_id=42)

    await commands.cmd_set_my_short_description(message)

    commands.perform_set_my_short_description.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "setmyshortdescription usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_set_my_short_description_calls_service(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_set_my_short_description",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(
        commands, "format_set_my_short_description_result", lambda **_: "ok"
    )
    message = _message(
        text="/setmyshortdescription Claude agent language=en",
        chat_id=42,
    )

    await commands.cmd_set_my_short_description(message)

    commands.perform_set_my_short_description.assert_awaited_once_with(
        message.bot,
        short_description="Claude agent",
        language_code="en",
    )
    message.answer.assert_awaited_once_with("ok", parse_mode="HTML")


async def test_cmd_set_my_short_description_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(
        method=SetMyShortDescription(short_description="Claude agent"),
        message="Bad Request: SHORT_DESCRIPTION_INVALID",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_set_my_short_description",
        AsyncMock(side_effect=error),
    )
    message = _message(chat_id=42)

    await commands.cmd_set_my_short_description(message)

    args, _ = message.answer.await_args
    assert "Could not set bot short description" in args[0]
    assert "SHORT_DESCRIPTION_INVALID" not in args[0]
    assert "Please try again later" in args[0]


def test_parse_set_my_short_description_args_required_only():
    assert commands._parse_set_my_short_description_args(
        "/setmyshortdescription Claude agent"
    ) == (
        "Claude agent",
        None,
    )


def test_parse_set_my_short_description_args_with_language_code():
    assert commands._parse_set_my_short_description_args(
        "/setmyshortdescription Claude agent language=pt-BR"
    ) == ("Claude agent", "pt-BR")


def test_parse_set_my_short_description_args_clear_with_language_code():
    assert commands._parse_set_my_short_description_args(
        "/setmyshortdescription --clear language=pt-BR"
    ) == ("", "pt-BR")


def test_parse_set_my_short_description_args_rejects_too_long_description():
    assert (
        commands._parse_set_my_short_description_args(
            "/setmyshortdescription " + "x" * (SET_MY_SHORT_DESCRIPTION_LIMIT + 1)
        )
        is None
    )
