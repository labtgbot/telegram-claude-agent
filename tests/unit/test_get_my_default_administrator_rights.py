from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import GetMe
from aiogram.types import ChatAdministratorRights

from bot.handlers import commands
from bot.services.get_my_default_administrator_rights import (
    format_get_my_default_administrator_rights_result,
    perform_get_my_default_administrator_rights,
)


BASE_RIGHTS = {
    "is_anonymous": False,
    "can_manage_chat": False,
    "can_delete_messages": False,
    "can_manage_video_chats": False,
    "can_restrict_members": False,
    "can_promote_members": False,
    "can_change_info": False,
    "can_invite_users": False,
    "can_post_stories": False,
    "can_edit_stories": False,
    "can_delete_stories": False,
}


def _message(text: str = "/getmydefaultrights", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


def _rights(**overrides):
    return ChatAdministratorRights(**{**BASE_RIGHTS, **overrides})


async def test_perform_get_my_default_administrator_rights_uses_typed_aiogram_api():
    rights = _rights(can_manage_chat=True, can_delete_messages=True)
    bot = SimpleNamespace(get_my_default_administrator_rights=AsyncMock(return_value=rights))

    result = await perform_get_my_default_administrator_rights(
        bot,
        for_channels=False,
    )

    assert result == rights
    bot.get_my_default_administrator_rights.assert_awaited_once_with(
        for_channels=False,
    )


async def test_perform_get_my_default_administrator_rights_uses_raw_fallback():
    response = _rights(can_post_messages=True).model_dump(exclude_none=True)
    session = SimpleNamespace(make_request=AsyncMock(return_value=response))
    bot = SimpleNamespace(session=session)

    result = await perform_get_my_default_administrator_rights(
        bot,
        for_channels=True,
    )

    assert result.can_post_messages is True
    session.make_request.assert_awaited_once_with(
        bot,
        "getMyDefaultAdministratorRights",
        {"for_channels": True},
    )


async def test_perform_get_my_default_administrator_rights_reraises_bad_request():
    error = TelegramBadRequest(
        method=GetMe(),
        message="Bad Request: FOR_CHANNELS_INVALID",
    )
    bot = SimpleNamespace(get_my_default_administrator_rights=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_get_my_default_administrator_rights(bot, for_channels=True)


async def test_perform_get_my_default_administrator_rights_reraises_forbidden():
    error = TelegramForbiddenError(
        method=GetMe(),
        message="Forbidden: bot was blocked by the user",
    )
    bot = SimpleNamespace(get_my_default_administrator_rights=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_get_my_default_administrator_rights(bot)


def test_format_get_my_default_administrator_rights_result_lists_rights():
    text = format_get_my_default_administrator_rights_result(
        _rights(can_manage_chat=True, can_delete_messages=True),
        for_channels=False,
    )

    assert "getMyDefaultAdministratorRights" in text
    assert "groups and supergroups" in text
    assert "can_manage_chat" in text
    assert "can_delete_messages" in text
    assert "default administrator rights fetched" in text


async def test_cmd_get_my_default_administrator_rights_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_get_my_default_administrator_rights", AsyncMock())
    message = _message(chat_id=42)

    await commands.cmd_get_my_default_administrator_rights(message)

    commands.perform_get_my_default_administrator_rights.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_get_my_default_administrator_rights_shows_usage(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_get_my_default_administrator_rights", AsyncMock())
    message = _message(text="/getmydefaultrights for_channels=maybe", chat_id=42)

    await commands.cmd_get_my_default_administrator_rights(message)

    commands.perform_get_my_default_administrator_rights.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "getmydefaultrights usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_get_my_default_administrator_rights_calls_service(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_get_my_default_administrator_rights",
        AsyncMock(return_value=_rights(can_manage_chat=True)),
    )
    monkeypatch.setattr(
        commands,
        "format_get_my_default_administrator_rights_result",
        lambda *_, **__: "ok",
    )
    message = _message(text="/getmydefaultrights for_channels=true", chat_id=42)

    await commands.cmd_get_my_default_administrator_rights(message)

    commands.perform_get_my_default_administrator_rights.assert_awaited_once_with(
        message.bot,
        for_channels=True,
    )
    message.answer.assert_awaited_once_with("ok", parse_mode="HTML")


async def test_cmd_get_my_default_administrator_rights_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(
        method=GetMe(),
        message="Bad Request: FOR_CHANNELS_INVALID",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_get_my_default_administrator_rights",
        AsyncMock(side_effect=error),
    )
    message = _message(text="/getmydefaultrights for_channels=true", chat_id=42)

    await commands.cmd_get_my_default_administrator_rights(message)

    args, _ = message.answer.await_args
    assert "Could not get default administrator rights" in args[0]
    assert "FOR_CHANNELS_INVALID" in args[0]


def test_parse_get_my_default_administrator_rights_args():
    assert commands._parse_get_my_default_administrator_rights_args(
        "/getmydefaultrights"
    ) is None
    assert commands._parse_get_my_default_administrator_rights_args(
        "/getmydefaultrights for_channels=true"
    ) is True
    assert commands._parse_get_my_default_administrator_rights_args(
        "/getmydefaultrights for_channels=false"
    ) is False
    assert (
        commands._parse_get_my_default_administrator_rights_args(
            "/getmydefaultrights for_channels=maybe"
        )
        is commands.INVALID_COMMAND_ARGS
    )
