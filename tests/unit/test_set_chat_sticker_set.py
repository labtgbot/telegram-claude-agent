from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import SetChatStickerSet

from bot.handlers import commands
from bot.services.set_chat_sticker_set import (
    format_set_chat_sticker_set_result,
    perform_set_chat_sticker_set,
)


def _message(text: str = "/setchatstickerset", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_perform_set_chat_sticker_set_uses_typed_aiogram_api():
    bot = SimpleNamespace(set_chat_sticker_set=AsyncMock(return_value=True))

    result = await perform_set_chat_sticker_set(
        bot,
        chat_id=-100123,
        sticker_set_name="project_support_by_example_bot",
    )

    assert result is True
    bot.set_chat_sticker_set.assert_awaited_once_with(
        chat_id=-100123,
        sticker_set_name="project_support_by_example_bot",
    )


async def test_perform_set_chat_sticker_set_reraises_bad_request():
    error = TelegramBadRequest(
        method=SetChatStickerSet(
            chat_id=-100123,
            sticker_set_name="project_support_by_example_bot",
        ),
        message="Bad Request: CHAT_ADMIN_REQUIRED",
    )
    bot = SimpleNamespace(set_chat_sticker_set=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_set_chat_sticker_set(
            bot,
            chat_id=-100123,
            sticker_set_name="project_support_by_example_bot",
        )


async def test_perform_set_chat_sticker_set_reraises_forbidden():
    error = TelegramForbiddenError(
        method=SetChatStickerSet(
            chat_id=-100123,
            sticker_set_name="project_support_by_example_bot",
        ),
        message="Forbidden: bot is not an administrator",
    )
    bot = SimpleNamespace(set_chat_sticker_set=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_set_chat_sticker_set(
            bot,
            chat_id=-100123,
            sticker_set_name="project_support_by_example_bot",
        )


def test_format_set_chat_sticker_set_result_escapes_fields():
    text = format_set_chat_sticker_set_result(
        chat_id=-100123,
        sticker_set_name="support_<&>_by_example_bot",
    )

    assert "setChatStickerSet" in text
    assert "-100123" in text
    assert "support_&lt;&amp;&gt;_by_example_bot" in text
    assert "chat sticker set updated" in text


async def test_cmd_set_chat_sticker_set_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_set_chat_sticker_set", AsyncMock())
    message = _message(
        text="/setchatstickerset -100123 project_support_by_example_bot",
        chat_id=42,
    )

    await commands.cmd_set_chat_sticker_set(message)

    commands.perform_set_chat_sticker_set.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_set_chat_sticker_set_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_set_chat_sticker_set", AsyncMock())
    message = _message(text="/setchatstickerset", chat_id=42)

    await commands.cmd_set_chat_sticker_set(message)

    commands.perform_set_chat_sticker_set.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "setchatstickerset usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_set_chat_sticker_set_calls_service(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_set_chat_sticker_set", AsyncMock(return_value=True)
    )
    monkeypatch.setattr(commands, "format_set_chat_sticker_set_result", lambda **_: "ok")
    message = _message(
        text="/setchatstickerset -100123 project_support_by_example_bot",
        chat_id=42,
    )

    await commands.cmd_set_chat_sticker_set(message)

    commands.perform_set_chat_sticker_set.assert_awaited_once_with(
        message.bot,
        chat_id=-100123,
        sticker_set_name="project_support_by_example_bot",
    )
    message.answer.assert_awaited_once_with("ok", parse_mode="HTML")


async def test_cmd_set_chat_sticker_set_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(
        method=SetChatStickerSet(
            chat_id=-100123,
            sticker_set_name="project_support_by_example_bot",
        ),
        message="Bad Request: CHAT_ADMIN_REQUIRED",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_set_chat_sticker_set", AsyncMock(side_effect=error)
    )
    message = _message(
        text="/setchatstickerset -100123 project_support_by_example_bot",
        chat_id=42,
    )

    await commands.cmd_set_chat_sticker_set(message)

    args, _ = message.answer.await_args
    assert "Could not set the chat sticker set" in args[0]
    assert "CHAT_ADMIN_REQUIRED" in args[0]


def test_parse_set_chat_sticker_set_args_required_only():
    result = commands._parse_set_chat_sticker_set_args(
        "/setchatstickerset -100123 project_support_by_example_bot"
    )

    assert result == (-100123, "project_support_by_example_bot")


def test_parse_set_chat_sticker_set_args_requires_sticker_set_name():
    assert commands._parse_set_chat_sticker_set_args("/setchatstickerset -100123") is None


def test_parse_set_chat_sticker_set_args_invalid_chat_id():
    assert (
        commands._parse_set_chat_sticker_set_args(
            "/setchatstickerset not-a-chat project_support_by_example_bot"
        )
        is None
    )


def test_parse_set_chat_sticker_set_args_rejects_names_with_spaces():
    assert (
        commands._parse_set_chat_sticker_set_args(
            "/setchatstickerset -100123 project support"
        )
        is None
    )
