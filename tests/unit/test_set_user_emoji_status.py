from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import SetUserEmojiStatus

from bot.handlers import commands
from bot.services.set_user_emoji_status import perform_set_user_emoji_status

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CUSTOM_EMOJI_ID = "5361800661997563548"


def _message(text: str = "/setemojistatus", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


# ---------------------------------------------------------------------------
# Service: perform_set_user_emoji_status
# ---------------------------------------------------------------------------


async def test_perform_set_user_emoji_status_set_emoji():
    """Setting a custom emoji id calls the typed aiogram wrapper correctly."""
    bot = SimpleNamespace(set_user_emoji_status=AsyncMock(return_value=True))

    result = await perform_set_user_emoji_status(
        bot, user_id=123, emoji_status_custom_emoji_id=CUSTOM_EMOJI_ID
    )

    assert result is True
    bot.set_user_emoji_status.assert_awaited_once_with(
        user_id=123,
        emoji_status_custom_emoji_id=CUSTOM_EMOJI_ID,
        emoji_status_expiration_date=None,
    )


async def test_perform_set_user_emoji_status_remove_status():
    """Passing ``None`` for custom_emoji_id removes the emoji status."""
    bot = SimpleNamespace(set_user_emoji_status=AsyncMock(return_value=True))

    result = await perform_set_user_emoji_status(bot, user_id=456)

    assert result is True
    bot.set_user_emoji_status.assert_awaited_once_with(
        user_id=456,
        emoji_status_custom_emoji_id=None,
        emoji_status_expiration_date=None,
    )


async def test_perform_set_user_emoji_status_empty_string_removes_status():
    """Passing an empty string for custom_emoji_id also removes the status."""
    bot = SimpleNamespace(set_user_emoji_status=AsyncMock(return_value=True))

    result = await perform_set_user_emoji_status(
        bot, user_id=789, emoji_status_custom_emoji_id=""
    )

    assert result is True
    bot.set_user_emoji_status.assert_awaited_once_with(
        user_id=789,
        emoji_status_custom_emoji_id="",
        emoji_status_expiration_date=None,
    )


async def test_perform_set_user_emoji_status_reraises_bad_request():
    """TelegramBadRequest (e.g., no Mini App grant) is re-raised after logging."""
    error = TelegramBadRequest(
        method=SetUserEmojiStatus(user_id=1),
        message="Bad Request: USER_NOT_FOUND",
    )
    bot = SimpleNamespace(set_user_emoji_status=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_set_user_emoji_status(bot, user_id=1)


async def test_perform_set_user_emoji_status_reraises_forbidden():
    """TelegramForbiddenError is re-raised after logging."""
    error = TelegramForbiddenError(
        method=SetUserEmojiStatus(user_id=2),
        message="Forbidden: bot was blocked by the user",
    )
    bot = SimpleNamespace(set_user_emoji_status=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_set_user_emoji_status(bot, user_id=2)


# ---------------------------------------------------------------------------
# Handler: cmd_set_emoji_status — access control
# ---------------------------------------------------------------------------


async def test_cmd_set_emoji_status_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_set_user_emoji_status", AsyncMock())
    message = _message(text=f"/setemojistatus 123 {CUSTOM_EMOJI_ID}", chat_id=42)

    await commands.cmd_set_emoji_status(message)

    commands.perform_set_user_emoji_status.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


# ---------------------------------------------------------------------------
# Handler: cmd_set_emoji_status — validation
# ---------------------------------------------------------------------------


async def test_cmd_set_emoji_status_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_set_user_emoji_status", AsyncMock())
    message = _message(text="/setemojistatus", chat_id=42)

    await commands.cmd_set_emoji_status(message)

    commands.perform_set_user_emoji_status.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "setemojistatus usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_set_emoji_status_shows_usage_on_invalid_user_id(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_set_user_emoji_status", AsyncMock())
    message = _message(text="/setemojistatus notanumber", chat_id=42)

    await commands.cmd_set_emoji_status(message)

    commands.perform_set_user_emoji_status.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "setemojistatus usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


# ---------------------------------------------------------------------------
# Handler: cmd_set_emoji_status — successful calls
# ---------------------------------------------------------------------------


async def test_cmd_set_emoji_status_sets_emoji_status(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_set_user_emoji_status", AsyncMock(return_value=True)
    )
    message = _message(text=f"/setemojistatus 123 {CUSTOM_EMOJI_ID}", chat_id=42)

    await commands.cmd_set_emoji_status(message)

    commands.perform_set_user_emoji_status.assert_awaited_once()
    _, kwargs = commands.perform_set_user_emoji_status.await_args
    assert kwargs["user_id"] == 123
    assert kwargs["emoji_status_custom_emoji_id"] == CUSTOM_EMOJI_ID
    args, _ = message.answer.await_args
    assert CUSTOM_EMOJI_ID in args[0]
    assert "123" in args[0]


async def test_cmd_set_emoji_status_removes_emoji_status_without_emoji_id(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_set_user_emoji_status", AsyncMock(return_value=True)
    )
    message = _message(text="/setemojistatus 456", chat_id=42)

    await commands.cmd_set_emoji_status(message)

    commands.perform_set_user_emoji_status.assert_awaited_once()
    _, kwargs = commands.perform_set_user_emoji_status.await_args
    assert kwargs["user_id"] == 456
    assert kwargs["emoji_status_custom_emoji_id"] is None
    args, _ = message.answer.await_args
    assert "Removed emoji status" in args[0]
    assert "456" in args[0]


# ---------------------------------------------------------------------------
# Handler: cmd_set_emoji_status — error handling
# ---------------------------------------------------------------------------


async def test_cmd_set_emoji_status_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(
        method=SetUserEmojiStatus(user_id=42),
        message="Bad Request: USER_EMOJI_STATUS_FORBIDDEN",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_set_user_emoji_status",
        AsyncMock(side_effect=error),
    )
    message = _message(text=f"/setemojistatus 42 {CUSTOM_EMOJI_ID}", chat_id=42)

    await commands.cmd_set_emoji_status(message)

    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Could not set the emoji status" in args[0]


# ---------------------------------------------------------------------------
# Parser: _parse_set_emoji_status_args
# ---------------------------------------------------------------------------


def test_parse_set_emoji_status_args_no_args():
    assert commands._parse_set_emoji_status_args("/setemojistatus") is None


def test_parse_set_emoji_status_args_invalid_user_id():
    assert commands._parse_set_emoji_status_args("/setemojistatus notanumber") is None


def test_parse_set_emoji_status_args_user_id_only():
    result = commands._parse_set_emoji_status_args("/setemojistatus 123")
    assert result == (123, None)


def test_parse_set_emoji_status_args_with_custom_emoji_id():
    result = commands._parse_set_emoji_status_args(
        f"/setemojistatus 123 {CUSTOM_EMOJI_ID}"
    )
    assert result == (123, CUSTOM_EMOJI_ID)


def test_parse_set_emoji_status_args_zero_user_id():
    # user_id=0 is unusual but should pass through; Telegram will reject it
    result = commands._parse_set_emoji_status_args("/setemojistatus 0")
    assert result == (0, None)


def test_parse_set_emoji_status_args_negative_user_id():
    # Negative user_ids are unusual but the parser should not reject them
    result = commands._parse_set_emoji_status_args("/setemojistatus -5")
    assert result == (-5, None)
