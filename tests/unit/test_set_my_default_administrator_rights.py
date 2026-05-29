from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import SetMyDefaultAdministratorRights
from aiogram.types import ChatAdministratorRights

from bot.handlers import commands
from bot.services.set_my_default_administrator_rights import (
    format_set_my_default_administrator_rights_result,
    perform_set_my_default_administrator_rights,
    sync_configured_my_default_administrator_rights,
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


def _message(text: str = "/setmydefaultrights moderator", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


def _rights(**overrides):
    return ChatAdministratorRights(**{**BASE_RIGHTS, **overrides})


async def test_perform_set_my_default_administrator_rights_uses_typed_aiogram_api():
    bot = SimpleNamespace(set_my_default_administrator_rights=AsyncMock(return_value=True))
    rights = _rights(can_manage_chat=True, can_delete_messages=True)

    result = await perform_set_my_default_administrator_rights(
        bot,
        rights=rights,
        for_channels=False,
    )

    assert result is True
    bot.set_my_default_administrator_rights.assert_awaited_once_with(
        rights=rights,
        for_channels=False,
    )


async def test_perform_set_my_default_administrator_rights_allows_clear():
    bot = SimpleNamespace(set_my_default_administrator_rights=AsyncMock(return_value=True))

    result = await perform_set_my_default_administrator_rights(
        bot,
        rights=None,
        for_channels=True,
    )

    assert result is True
    bot.set_my_default_administrator_rights.assert_awaited_once_with(
        rights=None,
        for_channels=True,
    )


async def test_perform_set_my_default_administrator_rights_reraises_bad_request():
    error = TelegramBadRequest(
        method=SetMyDefaultAdministratorRights(
            rights=_rights(can_manage_chat=True),
            for_channels=False,
        ),
        message="Bad Request: RIGHTS_INVALID",
    )
    bot = SimpleNamespace(set_my_default_administrator_rights=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_set_my_default_administrator_rights(
            bot,
            rights=_rights(can_manage_chat=True),
            for_channels=False,
        )


async def test_perform_set_my_default_administrator_rights_reraises_forbidden():
    error = TelegramForbiddenError(
        method=SetMyDefaultAdministratorRights(rights=None, for_channels=True),
        message="Forbidden: bot was blocked by the user",
    )
    bot = SimpleNamespace(set_my_default_administrator_rights=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_set_my_default_administrator_rights(
            bot,
            rights=None,
            for_channels=True,
        )


async def test_sync_configured_my_default_administrator_rights_skips_when_unconfigured():
    bot = SimpleNamespace(set_my_default_administrator_rights=AsyncMock())

    result = await sync_configured_my_default_administrator_rights(
        bot,
        rights=None,
        for_channels=None,
        configured=False,
    )

    assert result is False
    bot.set_my_default_administrator_rights.assert_not_awaited()


async def test_sync_configured_my_default_administrator_rights_applies_config():
    bot = SimpleNamespace(set_my_default_administrator_rights=AsyncMock(return_value=True))
    rights = _rights(can_manage_chat=True)

    result = await sync_configured_my_default_administrator_rights(
        bot,
        rights=rights,
        for_channels=False,
        configured=True,
    )

    assert result is True
    bot.set_my_default_administrator_rights.assert_awaited_once_with(
        rights=rights,
        for_channels=False,
    )


def test_format_set_my_default_administrator_rights_result_lists_rights():
    text = format_set_my_default_administrator_rights_result(
        preset="moderator",
        rights=_rights(can_manage_chat=True, can_delete_messages=True),
        for_channels=False,
    )

    assert "setMyDefaultAdministratorRights" in text
    assert "moderator" in text
    assert "groups and supergroups" in text
    assert "can_manage_chat" in text
    assert "default administrator rights updated" in text


async def test_cmd_set_my_default_administrator_rights_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_set_my_default_administrator_rights", AsyncMock())
    message = _message(chat_id=42)

    await commands.cmd_set_my_default_administrator_rights(message)

    commands.perform_set_my_default_administrator_rights.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_set_my_default_administrator_rights_shows_usage(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_set_my_default_administrator_rights", AsyncMock())
    message = _message(text="/setmydefaultrights", chat_id=42)

    await commands.cmd_set_my_default_administrator_rights(message)

    commands.perform_set_my_default_administrator_rights.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "setmydefaultrights usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_set_my_default_administrator_rights_calls_service(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_set_my_default_administrator_rights",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(
        commands,
        "format_set_my_default_administrator_rights_result",
        lambda **kwargs: "ok",
    )
    message = _message(text="/setmydefaultrights moderator for_channels=false", chat_id=42)

    await commands.cmd_set_my_default_administrator_rights(message)

    call_kwargs = commands.perform_set_my_default_administrator_rights.await_args.kwargs
    assert call_kwargs["for_channels"] is False
    assert call_kwargs["rights"].can_manage_chat is True
    assert call_kwargs["rights"].can_restrict_members is True
    message.answer.assert_awaited_once_with("ok", parse_mode="HTML")


async def test_cmd_set_my_default_administrator_rights_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(
        method=SetMyDefaultAdministratorRights(rights=None, for_channels=True),
        message="Bad Request: RIGHTS_INVALID",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_set_my_default_administrator_rights",
        AsyncMock(side_effect=error),
    )
    message = _message(text="/setmydefaultrights clear for_channels=true", chat_id=42)

    await commands.cmd_set_my_default_administrator_rights(message)

    args, _ = message.answer.await_args
    assert "Could not set default administrator rights" in args[0]
    assert "RIGHTS_INVALID" in args[0]


def test_parse_set_my_default_administrator_rights_args_moderator():
    preset, rights, for_channels = commands._parse_set_my_default_administrator_rights_args(
        "/setmydefaultrights moderator for_channels=false"
    )

    assert preset == "moderator"
    assert rights.can_manage_chat is True
    assert rights.can_restrict_members is True
    assert for_channels is False


def test_parse_set_my_default_administrator_rights_args_clear():
    assert commands._parse_set_my_default_administrator_rights_args(
        "/setmydefaultrights clear for_channels=true"
    ) == ("clear", None, True)


@pytest.mark.parametrize(
    "text",
    [
        "/setmydefaultrights",
        "/setmydefaultrights unknown",
        "/setmydefaultrights moderator bad=true",
        "/setmydefaultrights moderator for_channels=maybe",
    ],
)
def test_parse_set_my_default_administrator_rights_args_invalid(text):
    assert commands._parse_set_my_default_administrator_rights_args(text) is None
