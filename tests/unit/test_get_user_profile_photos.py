from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import GetUserProfilePhotos

from bot.handlers import commands
from bot.services.get_user_profile_photos import (
    fetch_user_profile_photos,
    format_user_profile_photos,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_photo_size(file_id: str, width: int = 160, height: int = 160):
    return SimpleNamespace(file_id=file_id, width=width, height=height)


def _make_result(total_count: int = 3, photos=None):
    """Build a minimal UserProfilePhotos-like namespace."""
    if photos is None:
        photos = [
            [_make_photo_size(f"small_{i}"), _make_photo_size(f"big_{i}", 800, 800)]
            for i in range(total_count)
        ]
    return SimpleNamespace(total_count=total_count, photos=photos)


def _message(text: str = "/userprofilephotos", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


# ---------------------------------------------------------------------------
# Service: fetch_user_profile_photos
# ---------------------------------------------------------------------------


async def test_fetch_user_profile_photos_uses_typed_aiogram_api():
    result = _make_result()
    bot = SimpleNamespace(get_user_profile_photos=AsyncMock(return_value=result))

    returned = await fetch_user_profile_photos(bot, user_id=123)

    assert returned is result
    bot.get_user_profile_photos.assert_awaited_once_with(
        user_id=123,
        offset=None,
        limit=None,
    )


async def test_fetch_user_profile_photos_passes_offset_and_limit():
    result = _make_result(total_count=1, photos=[[_make_photo_size("f1")]])
    bot = SimpleNamespace(get_user_profile_photos=AsyncMock(return_value=result))

    returned = await fetch_user_profile_photos(bot, user_id=5, offset=2, limit=10)

    assert returned is result
    bot.get_user_profile_photos.assert_awaited_once_with(
        user_id=5,
        offset=2,
        limit=10,
    )


async def test_fetch_user_profile_photos_reraises_bad_request():
    error = TelegramBadRequest(
        method=GetUserProfilePhotos(user_id=1),
        message="Bad Request: user not found",
    )
    bot = SimpleNamespace(get_user_profile_photos=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await fetch_user_profile_photos(bot, user_id=1)


async def test_fetch_user_profile_photos_reraises_forbidden():
    error = TelegramForbiddenError(
        method=GetUserProfilePhotos(user_id=2),
        message="Forbidden: bot was blocked by the user",
    )
    bot = SimpleNamespace(get_user_profile_photos=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await fetch_user_profile_photos(bot, user_id=2)


# ---------------------------------------------------------------------------
# Service: format_user_profile_photos
# ---------------------------------------------------------------------------


def test_format_user_profile_photos_no_photos():
    result = _make_result(total_count=0, photos=[])
    text = format_user_profile_photos(result, user_id=99)
    assert "No profile photos found" in text
    assert "99" in text


def test_format_user_profile_photos_with_photos():
    result = _make_result(total_count=2)
    text = format_user_profile_photos(result, user_id=7)
    assert "Total photos: 2" in text
    assert "big_0" in text
    assert "big_1" in text
    assert "800×800px" in text


def test_format_user_profile_photos_escapes_user_id():
    result = _make_result(total_count=0, photos=[])
    text = format_user_profile_photos(result, user_id=42)
    # Should not raise and should contain the user id
    assert "42" in text


def test_format_user_profile_photos_escapes_file_id():
    """file_id values containing HTML special chars must be escaped."""
    tricky_file_id = "a<b>c&d"
    result = _make_result(
        total_count=1,
        photos=[[_make_photo_size(tricky_file_id)]],
    )
    text = format_user_profile_photos(result, user_id=1)
    assert "<b>c" not in text  # raw angle bracket must not appear as tag
    assert "a&lt;b&gt;c&amp;d" in text


# ---------------------------------------------------------------------------
# Handler: cmd_user_profile_photos — access control
# ---------------------------------------------------------------------------


async def test_cmd_user_profile_photos_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "fetch_user_profile_photos", AsyncMock())
    message = _message(text="/userprofilephotos 123", chat_id=42)

    await commands.cmd_user_profile_photos(message)

    commands.fetch_user_profile_photos.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


# ---------------------------------------------------------------------------
# Handler: cmd_user_profile_photos — validation
# ---------------------------------------------------------------------------


async def test_cmd_user_profile_photos_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "fetch_user_profile_photos", AsyncMock())
    message = _message(text="/userprofilephotos", chat_id=42)

    await commands.cmd_user_profile_photos(message)

    commands.fetch_user_profile_photos.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "userprofilephotos usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_user_profile_photos_shows_usage_on_invalid_user_id(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "fetch_user_profile_photos", AsyncMock())
    message = _message(text="/userprofilephotos notanumber", chat_id=42)

    await commands.cmd_user_profile_photos(message)

    commands.fetch_user_profile_photos.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "userprofilephotos usage" in args[0]


async def test_cmd_user_profile_photos_rejects_limit_too_small(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "fetch_user_profile_photos", AsyncMock())
    message = _message(text="/userprofilephotos 123 0 0", chat_id=42)

    await commands.cmd_user_profile_photos(message)

    commands.fetch_user_profile_photos.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Limit must be between" in args[0]


async def test_cmd_user_profile_photos_rejects_limit_too_large(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "fetch_user_profile_photos", AsyncMock())
    message = _message(text="/userprofilephotos 123 0 101", chat_id=42)

    await commands.cmd_user_profile_photos(message)

    commands.fetch_user_profile_photos.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Limit must be between" in args[0]


# ---------------------------------------------------------------------------
# Handler: cmd_user_profile_photos — successful calls
# ---------------------------------------------------------------------------


async def test_cmd_user_profile_photos_calls_service_with_user_id_only(monkeypatch):
    result = _make_result()
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "fetch_user_profile_photos", AsyncMock(return_value=result)
    )
    monkeypatch.setattr(
        commands, "format_user_profile_photos", lambda r, uid: f"ok {uid}"
    )
    message = _message(text="/userprofilephotos 999", chat_id=42)

    await commands.cmd_user_profile_photos(message)

    commands.fetch_user_profile_photos.assert_awaited_once_with(
        message.bot,
        user_id=999,
        offset=None,
        limit=None,
    )
    args, kwargs = message.answer.await_args
    assert "ok 999" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_user_profile_photos_passes_offset_and_limit(monkeypatch):
    result = _make_result()
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "fetch_user_profile_photos", AsyncMock(return_value=result)
    )
    monkeypatch.setattr(
        commands, "format_user_profile_photos", lambda r, uid: "formatted"
    )
    message = _message(text="/userprofilephotos 7 5 10", chat_id=42)

    await commands.cmd_user_profile_photos(message)

    commands.fetch_user_profile_photos.assert_awaited_once_with(
        message.bot,
        user_id=7,
        offset=5,
        limit=10,
    )


# ---------------------------------------------------------------------------
# Handler: cmd_user_profile_photos — error handling
# ---------------------------------------------------------------------------


async def test_cmd_user_profile_photos_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(
        method=GetUserProfilePhotos(user_id=1),
        message="Bad Request: user not found",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "fetch_user_profile_photos", AsyncMock(side_effect=error)
    )
    message = _message(text="/userprofilephotos 1", chat_id=42)

    await commands.cmd_user_profile_photos(message)

    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Could not fetch user profile photos" in args[0]


# ---------------------------------------------------------------------------
# Parser: _parse_user_profile_photos_args
# ---------------------------------------------------------------------------


def test_parse_user_profile_photos_args_no_args():
    assert commands._parse_user_profile_photos_args("/userprofilephotos") is None


def test_parse_user_profile_photos_args_invalid_user_id():
    assert commands._parse_user_profile_photos_args("/userprofilephotos abc") is None


def test_parse_user_profile_photos_args_user_id_only():
    result = commands._parse_user_profile_photos_args("/userprofilephotos 123")
    assert result == (123, None, None)


def test_parse_user_profile_photos_args_with_offset():
    result = commands._parse_user_profile_photos_args("/userprofilephotos 123 5")
    assert result == (123, 5, None)


def test_parse_user_profile_photos_args_with_offset_and_limit():
    result = commands._parse_user_profile_photos_args("/userprofilephotos 123 5 20")
    assert result == (123, 5, 20)


def test_parse_user_profile_photos_args_invalid_offset():
    assert (
        commands._parse_user_profile_photos_args("/userprofilephotos 123 abc") is None
    )


def test_parse_user_profile_photos_args_invalid_limit():
    assert (
        commands._parse_user_profile_photos_args("/userprofilephotos 123 0 abc") is None
    )


def test_parse_user_profile_photos_args_zero_user_id():
    # user_id=0 is unusual but should be passed through (Telegram will reject it)
    result = commands._parse_user_profile_photos_args("/userprofilephotos 0")
    assert result == (0, None, None)


def test_parse_user_profile_photos_args_negative_user_id():
    # Negative values are unusual but the parser should not reject them
    result = commands._parse_user_profile_photos_args("/userprofilephotos -5")
    assert result == (-5, None, None)
