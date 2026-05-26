from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import SetChatMemberTag

from bot.handlers import commands
from bot.services.set_chat_member_tag import (
    format_set_chat_member_tag_result,
    perform_set_chat_member_tag,
)


def _message(text: str = "/setchatmembertag", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_perform_set_chat_member_tag_uses_typed_aiogram_api():
    bot = SimpleNamespace(set_chat_member_tag=AsyncMock(return_value=True))

    result = await perform_set_chat_member_tag(
        bot,
        chat_id=-100123,
        user_id=456,
        tag="vip",
    )

    assert result is True
    bot.set_chat_member_tag.assert_awaited_once_with(
        chat_id=-100123,
        user_id=456,
        tag="vip",
    )


async def test_perform_set_chat_member_tag_allows_clearing_tag():
    bot = SimpleNamespace(set_chat_member_tag=AsyncMock(return_value=True))

    result = await perform_set_chat_member_tag(
        bot,
        chat_id=-100123,
        user_id=456,
        tag=None,
    )

    assert result is True
    bot.set_chat_member_tag.assert_awaited_once_with(
        chat_id=-100123,
        user_id=456,
        tag=None,
    )


async def test_perform_set_chat_member_tag_reraises_bad_request():
    error = TelegramBadRequest(
        method=SetChatMemberTag(chat_id=-100123, user_id=1, tag="vip"),
        message="Bad Request: tag is invalid",
    )
    bot = SimpleNamespace(set_chat_member_tag=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_set_chat_member_tag(
            bot,
            chat_id=-100123,
            user_id=1,
            tag="vip",
        )


async def test_perform_set_chat_member_tag_reraises_forbidden():
    error = TelegramForbiddenError(
        method=SetChatMemberTag(chat_id=-100123, user_id=2, tag="vip"),
        message="Forbidden: bot is not an administrator",
    )
    bot = SimpleNamespace(set_chat_member_tag=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_set_chat_member_tag(
            bot,
            chat_id=-100123,
            user_id=2,
            tag="vip",
        )


def test_format_set_chat_member_tag_result_escapes_tag():
    text = format_set_chat_member_tag_result(
        chat_id=-100123,
        user_id=456,
        tag="team <alpha>",
    )

    assert "setChatMemberTag" in text
    assert "-100123" in text
    assert "456" in text
    assert "team &lt;alpha&gt;" in text
    assert "member tag updated successfully" in text


def test_format_set_chat_member_tag_result_for_cleared_tag():
    text = format_set_chat_member_tag_result(
        chat_id=-100123,
        user_id=456,
        tag=None,
    )

    assert "Tag: cleared" in text
    assert "member tag cleared successfully" in text


async def test_cmd_set_chat_member_tag_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_set_chat_member_tag", AsyncMock())
    message = _message(text="/setchatmembertag -100123 456 vip", chat_id=42)

    await commands.cmd_set_chat_member_tag(message)

    commands.perform_set_chat_member_tag.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_set_chat_member_tag_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_set_chat_member_tag", AsyncMock())
    message = _message(text="/setchatmembertag", chat_id=42)

    await commands.cmd_set_chat_member_tag(message)

    commands.perform_set_chat_member_tag.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "setchatmembertag usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_set_chat_member_tag_calls_service(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_set_chat_member_tag",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(commands, "format_set_chat_member_tag_result", lambda **kwargs: "ok")
    message = _message(text="/setchatmembertag -100123 456 vip", chat_id=42)

    await commands.cmd_set_chat_member_tag(message)

    commands.perform_set_chat_member_tag.assert_awaited_once_with(
        message.bot,
        chat_id=-100123,
        user_id=456,
        tag="vip",
    )
    args, kwargs = message.answer.await_args
    assert args[0] == "ok"
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_set_chat_member_tag_calls_service_to_clear_tag(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_set_chat_member_tag",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(commands, "format_set_chat_member_tag_result", lambda **kwargs: "ok")
    message = _message(text="/setchatmembertag -100123 456 clear", chat_id=42)

    await commands.cmd_set_chat_member_tag(message)

    commands.perform_set_chat_member_tag.assert_awaited_once_with(
        message.bot,
        chat_id=-100123,
        user_id=456,
        tag=None,
    )


async def test_cmd_set_chat_member_tag_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(
        method=SetChatMemberTag(chat_id=-100123, user_id=1, tag="vip"),
        message="Bad Request: not enough rights",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_set_chat_member_tag",
        AsyncMock(side_effect=error),
    )
    message = _message(text="/setchatmembertag -100123 1 vip", chat_id=42)

    await commands.cmd_set_chat_member_tag(message)

    args, _kwargs = message.answer.await_args
    assert "Could not set the member tag" in args[0]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("/setchatmembertag -100123 456 vip", (-100123, 456, "vip")),
        ("/setchatmembertag -100123 456 team alpha", (-100123, 456, "team alpha")),
        ("/setchatmembertag -100123 456 clear", (-100123, 456, None)),
        ("/setchatmembertag -100123 456 none", (-100123, 456, None)),
        ("/setchatmembertag -100123 456 -", (-100123, 456, None)),
    ],
)
def test_parse_set_chat_member_tag_args(text, expected):
    assert commands._parse_set_chat_member_tag_args(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "/setchatmembertag",
        "/setchatmembertag bad 456 vip",
        "/setchatmembertag -100123 bad vip",
        "/setchatmembertag -100123 456",
        "/setchatmembertag -100123 456    ",
    ],
)
def test_parse_set_chat_member_tag_args_invalid(text):
    assert commands._parse_set_chat_member_tag_args(text) is None
