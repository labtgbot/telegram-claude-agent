from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import GetUserProfileAudios

from bot.handlers import commands
from bot.services.get_user_profile_audios import (
    fetch_user_profile_audios,
    format_user_profile_audios,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_audio(
    file_id: str = "audio_file_id",
    file_unique_id: str = "unique_id",
    duration: int = 180,
    performer: str | None = "Artist",
    title: str | None = "Song",
    file_name: str | None = "song.mp3",
    mime_type: str | None = "audio/mpeg",
    file_size: int | None = 1024000,
):
    return SimpleNamespace(
        file_id=file_id,
        file_unique_id=file_unique_id,
        duration=duration,
        performer=performer,
        title=title,
        file_name=file_name,
        mime_type=mime_type,
        file_size=file_size,
        thumbnail=None,
    )


def _make_result(total_count: int = 2, audios=None):
    """Build a minimal UserProfileAudios-like namespace."""
    if audios is None:
        audios = [
            _make_audio(file_id=f"audio_{i}", title=f"Track {i}")
            for i in range(total_count)
        ]
    return SimpleNamespace(total_count=total_count, audios=audios)


def _message(text: str = "/userprofileaudios", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


# ---------------------------------------------------------------------------
# Service: fetch_user_profile_audios
# ---------------------------------------------------------------------------


async def test_fetch_user_profile_audios_uses_typed_aiogram_api():
    result = _make_result()
    bot = SimpleNamespace(get_user_profile_audios=AsyncMock(return_value=result))

    returned = await fetch_user_profile_audios(bot, user_id=123)

    assert returned is result
    bot.get_user_profile_audios.assert_awaited_once_with(
        user_id=123,
        offset=None,
        limit=None,
    )


async def test_fetch_user_profile_audios_passes_offset_and_limit():
    result = _make_result(total_count=1, audios=[_make_audio(file_id="f1")])
    bot = SimpleNamespace(get_user_profile_audios=AsyncMock(return_value=result))

    returned = await fetch_user_profile_audios(bot, user_id=5, offset=2, limit=10)

    assert returned is result
    bot.get_user_profile_audios.assert_awaited_once_with(
        user_id=5,
        offset=2,
        limit=10,
    )


async def test_fetch_user_profile_audios_reraises_bad_request():
    error = TelegramBadRequest(
        method=GetUserProfileAudios(user_id=1),
        message="Bad Request: user not found",
    )
    bot = SimpleNamespace(get_user_profile_audios=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await fetch_user_profile_audios(bot, user_id=1)


async def test_fetch_user_profile_audios_reraises_forbidden():
    error = TelegramForbiddenError(
        method=GetUserProfileAudios(user_id=2),
        message="Forbidden: bot was blocked by the user",
    )
    bot = SimpleNamespace(get_user_profile_audios=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await fetch_user_profile_audios(bot, user_id=2)


# ---------------------------------------------------------------------------
# Service: format_user_profile_audios
# ---------------------------------------------------------------------------


def test_format_user_profile_audios_no_audios():
    result = _make_result(total_count=0, audios=[])
    text = format_user_profile_audios(result, user_id=99)
    assert "No profile audios found" in text
    assert "99" in text


def test_format_user_profile_audios_with_audios():
    result = _make_result(total_count=2)
    text = format_user_profile_audios(result, user_id=7)
    assert "Total audios: 2" in text
    assert "audio_0" in text
    assert "audio_1" in text
    assert "Track 0" in text
    assert "Track 1" in text


def test_format_user_profile_audios_includes_duration():
    result = _make_result(
        total_count=1,
        audios=[_make_audio(file_id="f1", duration=240)],
    )
    text = format_user_profile_audios(result, user_id=1)
    assert "240s" in text


def test_format_user_profile_audios_includes_performer():
    result = _make_result(
        total_count=1,
        audios=[_make_audio(file_id="f1", performer="The Beatles")],
    )
    text = format_user_profile_audios(result, user_id=1)
    assert "The Beatles" in text


def test_format_user_profile_audios_omits_none_performer():
    result = _make_result(
        total_count=1,
        audios=[_make_audio(file_id="f1", performer=None, title=None)],
    )
    text = format_user_profile_audios(result, user_id=1)
    assert "performer" not in text
    assert "title" not in text


def test_format_user_profile_audios_escapes_user_id():
    result = _make_result(total_count=0, audios=[])
    text = format_user_profile_audios(result, user_id=42)
    assert "42" in text


def test_format_user_profile_audios_escapes_file_id():
    """file_id values containing HTML special chars must be escaped."""
    tricky_file_id = "a<b>c&d"
    result = _make_result(
        total_count=1,
        audios=[_make_audio(file_id=tricky_file_id)],
    )
    text = format_user_profile_audios(result, user_id=1)
    assert "<b>c" not in text  # raw angle bracket must not appear as tag
    assert "a&lt;b&gt;c&amp;d" in text


def test_format_user_profile_audios_escapes_performer():
    """Performer values containing HTML special chars must be escaped."""
    result = _make_result(
        total_count=1,
        audios=[_make_audio(file_id="f1", performer="A&B <Band>")],
    )
    text = format_user_profile_audios(result, user_id=1)
    assert "A&amp;B &lt;Band&gt;" in text


def test_format_user_profile_audios_escapes_title():
    """Title values containing HTML special chars must be escaped."""
    result = _make_result(
        total_count=1,
        audios=[_make_audio(file_id="f1", title="<Song> & \"More\"")],
    )
    text = format_user_profile_audios(result, user_id=1)
    assert "&lt;Song&gt;" in text


# ---------------------------------------------------------------------------
# Handler: cmd_user_profile_audios — access control
# ---------------------------------------------------------------------------


async def test_cmd_user_profile_audios_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "fetch_user_profile_audios", AsyncMock())
    message = _message(text="/userprofileaudios 123", chat_id=42)

    await commands.cmd_user_profile_audios(message)

    commands.fetch_user_profile_audios.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


# ---------------------------------------------------------------------------
# Handler: cmd_user_profile_audios — validation
# ---------------------------------------------------------------------------


async def test_cmd_user_profile_audios_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "fetch_user_profile_audios", AsyncMock())
    message = _message(text="/userprofileaudios", chat_id=42)

    await commands.cmd_user_profile_audios(message)

    commands.fetch_user_profile_audios.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "userprofileaudios usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_user_profile_audios_shows_usage_on_invalid_user_id(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "fetch_user_profile_audios", AsyncMock())
    message = _message(text="/userprofileaudios notanumber", chat_id=42)

    await commands.cmd_user_profile_audios(message)

    commands.fetch_user_profile_audios.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "userprofileaudios usage" in args[0]


async def test_cmd_user_profile_audios_rejects_limit_too_small(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "fetch_user_profile_audios", AsyncMock())
    message = _message(text="/userprofileaudios 123 0 0", chat_id=42)

    await commands.cmd_user_profile_audios(message)

    commands.fetch_user_profile_audios.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Limit must be between" in args[0]


async def test_cmd_user_profile_audios_rejects_limit_too_large(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "fetch_user_profile_audios", AsyncMock())
    message = _message(text="/userprofileaudios 123 0 101", chat_id=42)

    await commands.cmd_user_profile_audios(message)

    commands.fetch_user_profile_audios.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Limit must be between" in args[0]


# ---------------------------------------------------------------------------
# Handler: cmd_user_profile_audios — successful calls
# ---------------------------------------------------------------------------


async def test_cmd_user_profile_audios_calls_service_with_user_id_only(monkeypatch):
    result = _make_result()
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "fetch_user_profile_audios", AsyncMock(return_value=result)
    )
    monkeypatch.setattr(
        commands, "format_user_profile_audios", lambda r, uid: f"ok {uid}"
    )
    message = _message(text="/userprofileaudios 999", chat_id=42)

    await commands.cmd_user_profile_audios(message)

    commands.fetch_user_profile_audios.assert_awaited_once_with(
        message.bot,
        user_id=999,
        offset=None,
        limit=None,
    )
    args, kwargs = message.answer.await_args
    assert "ok 999" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_user_profile_audios_passes_offset_and_limit(monkeypatch):
    result = _make_result()
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "fetch_user_profile_audios", AsyncMock(return_value=result)
    )
    monkeypatch.setattr(
        commands, "format_user_profile_audios", lambda r, uid: "formatted"
    )
    message = _message(text="/userprofileaudios 7 5 10", chat_id=42)

    await commands.cmd_user_profile_audios(message)

    commands.fetch_user_profile_audios.assert_awaited_once_with(
        message.bot,
        user_id=7,
        offset=5,
        limit=10,
    )


# ---------------------------------------------------------------------------
# Handler: cmd_user_profile_audios — error handling
# ---------------------------------------------------------------------------


async def test_cmd_user_profile_audios_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(
        method=GetUserProfileAudios(user_id=1),
        message="Bad Request: user not found",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "fetch_user_profile_audios", AsyncMock(side_effect=error)
    )
    message = _message(text="/userprofileaudios 1", chat_id=42)

    await commands.cmd_user_profile_audios(message)

    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Could not fetch user profile audios" in args[0]


# ---------------------------------------------------------------------------
# Parser: _parse_user_profile_audios_args
# ---------------------------------------------------------------------------


def test_parse_user_profile_audios_args_no_args():
    assert commands._parse_user_profile_audios_args("/userprofileaudios") is None


def test_parse_user_profile_audios_args_invalid_user_id():
    assert commands._parse_user_profile_audios_args("/userprofileaudios abc") is None


def test_parse_user_profile_audios_args_user_id_only():
    result = commands._parse_user_profile_audios_args("/userprofileaudios 123")
    assert result == (123, None, None)


def test_parse_user_profile_audios_args_with_offset():
    result = commands._parse_user_profile_audios_args("/userprofileaudios 123 5")
    assert result == (123, 5, None)


def test_parse_user_profile_audios_args_with_offset_and_limit():
    result = commands._parse_user_profile_audios_args("/userprofileaudios 123 5 20")
    assert result == (123, 5, 20)


def test_parse_user_profile_audios_args_invalid_offset():
    assert (
        commands._parse_user_profile_audios_args("/userprofileaudios 123 abc") is None
    )


def test_parse_user_profile_audios_args_invalid_limit():
    assert (
        commands._parse_user_profile_audios_args("/userprofileaudios 123 0 abc") is None
    )


def test_parse_user_profile_audios_args_zero_user_id():
    # user_id=0 is unusual but should be passed through (Telegram will reject it)
    result = commands._parse_user_profile_audios_args("/userprofileaudios 0")
    assert result == (0, None, None)


def test_parse_user_profile_audios_args_negative_user_id():
    # Negative values are unusual but the parser should not reject them
    result = commands._parse_user_profile_audios_args("/userprofileaudios -5")
    assert result == (-5, None, None)
