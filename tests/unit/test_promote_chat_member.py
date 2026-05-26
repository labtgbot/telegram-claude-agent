from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import PromoteChatMember
from aiogram.types import ChatAdministratorRights

from bot.handlers import commands
from bot.services.promote_chat_member import (
    format_promote_result,
    perform_promote_chat_member,
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


def _message(text: str = "/promotechatmember", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


def _rights(**overrides):
    return ChatAdministratorRights(**{**BASE_RIGHTS, **overrides})


async def test_perform_promote_chat_member_uses_typed_aiogram_api():
    bot = SimpleNamespace(promote_chat_member=AsyncMock(return_value=True))
    rights = _rights(
        can_manage_chat=True,
        can_delete_messages=True,
        can_restrict_members=True,
    )

    result = await perform_promote_chat_member(
        bot,
        chat_id=-100123,
        user_id=456,
        rights=rights,
    )

    assert result is True
    bot.promote_chat_member.assert_awaited_once_with(
        chat_id=-100123,
        user_id=456,
        can_manage_chat=True,
        can_delete_messages=True,
        can_manage_video_chats=False,
        can_restrict_members=True,
        can_promote_members=False,
        can_change_info=False,
        can_invite_users=False,
        can_post_stories=False,
        can_edit_stories=False,
        can_delete_stories=False,
        is_anonymous=False,
    )


async def test_perform_promote_chat_member_reraises_bad_request():
    rights = _rights(can_manage_chat=True)
    error = TelegramBadRequest(
        method=PromoteChatMember(
            chat_id=-100123,
            user_id=1,
            can_manage_chat=True,
        ),
        message="Bad Request: not enough rights",
    )
    bot = SimpleNamespace(promote_chat_member=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_promote_chat_member(
            bot,
            chat_id=-100123,
            user_id=1,
            rights=rights,
        )


async def test_perform_promote_chat_member_reraises_forbidden():
    rights = _rights(can_manage_chat=True)
    error = TelegramForbiddenError(
        method=PromoteChatMember(
            chat_id=-100123,
            user_id=2,
            can_manage_chat=True,
        ),
        message="Forbidden: bot is not an administrator",
    )
    bot = SimpleNamespace(promote_chat_member=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_promote_chat_member(
            bot,
            chat_id=-100123,
            user_id=2,
            rights=rights,
        )


def test_format_promote_result_escapes_and_lists_rights():
    text = format_promote_result(
        chat_id=-100123,
        user_id=456,
        preset="manager",
        rights=_rights(
            can_manage_chat=True,
            can_delete_messages=True,
            can_promote_members=False,
        ),
    )

    assert "promoteChatMember" in text
    assert "-100123" in text
    assert "456" in text
    assert "manager" in text
    assert "can_manage_chat" in text
    assert "can_promote_members" in text
    assert "promoted successfully" in text


async def test_cmd_promote_chat_member_rejects_non_admin_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands, "perform_promote_chat_member", AsyncMock())
    message = _message(text="/promotechatmember -100123 456 moderator", chat_id=42)

    await commands.cmd_promote_chat_member(message)

    commands.perform_promote_chat_member.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_promote_chat_member_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_promote_chat_member", AsyncMock())
    message = _message(text="/promotechatmember", chat_id=42)

    await commands.cmd_promote_chat_member(message)

    commands.perform_promote_chat_member.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "promotechatmember usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_promote_chat_member_calls_service(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_promote_chat_member",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(commands, "format_promote_result", lambda **kwargs: "ok")
    message = _message(text="/promotechatmember -100123 456 moderator", chat_id=42)

    await commands.cmd_promote_chat_member(message)

    call_kwargs = commands.perform_promote_chat_member.await_args.kwargs
    assert call_kwargs["chat_id"] == -100123
    assert call_kwargs["user_id"] == 456
    assert call_kwargs["rights"].can_manage_chat is True
    assert call_kwargs["rights"].can_restrict_members is True
    args, kwargs = message.answer.await_args
    assert args[0] == "ok"
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_promote_chat_member_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(
        method=PromoteChatMember(
            chat_id=-100123,
            user_id=1,
            can_manage_chat=True,
        ),
        message="Bad Request: not enough rights",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_promote_chat_member",
        AsyncMock(side_effect=error),
    )
    message = _message(text="/promotechatmember -100123 1 moderator", chat_id=42)

    await commands.cmd_promote_chat_member(message)

    args, _kwargs = message.answer.await_args
    assert "Could not promote the user" in args[0]


def test_parse_promote_chat_member_args_moderator_preset():
    result = commands._parse_promote_chat_member_args(
        "/promotechatmember -100123 456 moderator"
    )

    chat_id, user_id, preset, rights = result
    assert chat_id == -100123
    assert user_id == 456
    assert preset == "moderator"
    assert rights.can_manage_chat is True
    assert rights.can_restrict_members is True
    assert rights.can_promote_members is False


def test_parse_promote_chat_member_args_manager_preset():
    result = commands._parse_promote_chat_member_args(
        "/promotechatmember -100123 456 manager"
    )

    assert result[3].can_invite_users is True
    assert result[3].can_pin_messages is True
    assert result[3].can_manage_topics is True


def test_parse_promote_chat_member_args_demote_preset():
    result = commands._parse_promote_chat_member_args(
        "/promotechatmember -100123 456 demote"
    )

    assert result[2] == "demote"
    assert result[3].can_manage_chat is False
    assert result[3].can_delete_messages is False


@pytest.mark.parametrize(
    "text",
    [
        "/promotechatmember",
        "/promotechatmember bad 456 moderator",
        "/promotechatmember -100123 bad moderator",
        "/promotechatmember -100123 456 unknown",
        "/promotechatmember -100123 456 moderator extra",
    ],
)
def test_parse_promote_chat_member_args_invalid(text):
    assert commands._parse_promote_chat_member_args(text) is None
