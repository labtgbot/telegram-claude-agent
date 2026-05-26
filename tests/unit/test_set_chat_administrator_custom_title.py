from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import SetChatAdministratorCustomTitle

from bot.handlers import commands
from bot.services.set_chat_administrator_custom_title import (
    format_set_chat_administrator_custom_title_result,
    perform_set_chat_administrator_custom_title,
)


def _message(text: str = "/setchatadministratortitle", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_perform_set_chat_administrator_custom_title_uses_typed_aiogram_api():
    bot = SimpleNamespace(set_chat_administrator_custom_title=AsyncMock(return_value=True))

    result = await perform_set_chat_administrator_custom_title(
        bot,
        chat_id=-100123,
        user_id=456,
        custom_title="Moderator",
    )

    assert result is True
    bot.set_chat_administrator_custom_title.assert_awaited_once_with(
        chat_id=-100123,
        user_id=456,
        custom_title="Moderator",
    )


async def test_perform_set_chat_administrator_custom_title_reraises_bad_request():
    error = TelegramBadRequest(
        method=SetChatAdministratorCustomTitle(
            chat_id=-100123,
            user_id=1,
            custom_title="Moderator",
        ),
        message="Bad Request: user is not an administrator",
    )
    bot = SimpleNamespace(set_chat_administrator_custom_title=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_set_chat_administrator_custom_title(
            bot,
            chat_id=-100123,
            user_id=1,
            custom_title="Moderator",
        )


async def test_perform_set_chat_administrator_custom_title_reraises_forbidden():
    error = TelegramForbiddenError(
        method=SetChatAdministratorCustomTitle(
            chat_id=-100123,
            user_id=2,
            custom_title="Moderator",
        ),
        message="Forbidden: bot is not an administrator",
    )
    bot = SimpleNamespace(set_chat_administrator_custom_title=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_set_chat_administrator_custom_title(
            bot,
            chat_id=-100123,
            user_id=2,
            custom_title="Moderator",
        )


def test_format_set_chat_administrator_custom_title_result():
    text = format_set_chat_administrator_custom_title_result(
        chat_id=-100123,
        user_id=456,
        custom_title="Lead <Admin>",
    )

    assert "setChatAdministratorCustomTitle" in text
    assert "-100123" in text
    assert "456" in text
    assert "Lead &lt;Admin&gt;" in text
    assert "custom title updated successfully" in text


async def test_cmd_set_chat_administrator_custom_title_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_set_chat_administrator_custom_title", AsyncMock())
    message = _message(text="/setchatadministratortitle -100123 456 Moderator", chat_id=42)

    await commands.cmd_set_chat_administrator_custom_title(message)

    commands.perform_set_chat_administrator_custom_title.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_set_chat_administrator_custom_title_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_set_chat_administrator_custom_title", AsyncMock())
    message = _message(text="/setchatadministratortitle", chat_id=42)

    await commands.cmd_set_chat_administrator_custom_title(message)

    commands.perform_set_chat_administrator_custom_title.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "setchatadministratortitle usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_set_chat_administrator_custom_title_calls_service(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_set_chat_administrator_custom_title",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(
        commands,
        "format_set_chat_administrator_custom_title_result",
        lambda **kwargs: "ok",
    )
    message = _message(text="/setchatadministratortitle -100123 456 Lead Moderator", chat_id=42)

    await commands.cmd_set_chat_administrator_custom_title(message)

    commands.perform_set_chat_administrator_custom_title.assert_awaited_once_with(
        message.bot,
        chat_id=-100123,
        user_id=456,
        custom_title="Lead Moderator",
    )
    args, kwargs = message.answer.await_args
    assert args[0] == "ok"
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_set_chat_administrator_custom_title_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(
        method=SetChatAdministratorCustomTitle(
            chat_id=-100123,
            user_id=1,
            custom_title="Moderator",
        ),
        message="Bad Request: not enough rights",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_set_chat_administrator_custom_title",
        AsyncMock(side_effect=error),
    )
    message = _message(text="/setchatadministratortitle -100123 1 Moderator", chat_id=42)

    await commands.cmd_set_chat_administrator_custom_title(message)

    args, _kwargs = message.answer.await_args
    assert "Could not set the administrator custom title" in args[0]


def test_parse_set_chat_administrator_custom_title_args():
    result = commands._parse_set_chat_administrator_custom_title_args(
        "/setchatadministratortitle -100123 456 Lead Moderator"
    )

    assert result == (-100123, 456, "Lead Moderator")


@pytest.mark.parametrize(
    "text",
    [
        "/setchatadministratortitle",
        "/setchatadministratortitle bad 456 Moderator",
        "/setchatadministratortitle -100123 bad Moderator",
        "/setchatadministratortitle -100123 456",
        "/setchatadministratortitle -100123 456    ",
    ],
)
def test_parse_set_chat_administrator_custom_title_args_invalid(text):
    assert commands._parse_set_chat_administrator_custom_title_args(text) is None
