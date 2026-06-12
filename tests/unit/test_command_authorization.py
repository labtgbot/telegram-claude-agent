from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from bot.handlers import commands


@pytest.mark.parametrize(
    ("admin_chat_ids", "allowed_chat_ids", "chat_id", "expected"),
    [
        ("", "", 42, False),
        ("", "42", 42, True),
        ("", "7", 42, False),
        ("42", "", 42, True),
        ("7", "42", 42, False),
        ("42", "7", 42, True),
    ],
)
def test_admin_or_allowed_chat_authorization(
    monkeypatch,
    admin_chat_ids,
    allowed_chat_ids,
    chat_id,
    expected,
):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", admin_chat_ids)
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", allowed_chat_ids)
    monkeypatch.setattr(commands.settings, "telegram_admin_user_ids", "")

    assert commands._is_admin_or_allowed_chat(chat_id) is expected


@pytest.mark.parametrize(
    ("admin_chat_ids", "admin_user_ids", "chat_id", "user_id", "expected"),
    [
        ("42", "", 42, 42, True),
        ("42", "", 42, 7, False),
        ("-10042", "", -10042, 7, False),
        ("-10042", "7", -10042, 7, True),
        ("-10042", "8", -10042, 7, False),
        ("-10042", "", -10042, None, False),
        ("42", "", 42, None, True),
    ],
)
def test_admin_action_authorization(
    monkeypatch,
    admin_chat_ids,
    admin_user_ids,
    chat_id,
    user_id,
    expected,
):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", admin_chat_ids)
    monkeypatch.setattr(commands.settings, "telegram_admin_user_ids", admin_user_ids)

    assert commands._is_admin_action_allowed(chat_id, user_id) is expected


@pytest.mark.parametrize(
    ("allowed_chat_ids", "admin_user_ids", "chat_id", "user_id", "expected"),
    [
        ("42", "", 42, 42, True),
        ("-10042", "", -10042, 7, False),
        ("-10042", "7", -10042, 7, True),
    ],
)
def test_admin_or_allowed_chat_authorization_applies_user_guard_to_allowed_fallback(
    monkeypatch,
    allowed_chat_ids,
    admin_user_ids,
    chat_id,
    user_id,
    expected,
):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", allowed_chat_ids)
    monkeypatch.setattr(commands.settings, "telegram_admin_user_ids", admin_user_ids)

    assert commands._is_admin_or_allowed_chat(chat_id, user_id) is expected


def _message(chat_id: int, text: str, user_id: int | None = None):
    return SimpleNamespace(
        chat=SimpleNamespace(id=chat_id),
        from_user=SimpleNamespace(id=chat_id if user_id is None else user_id),
        bot=object(),
        text=text,
        answer=AsyncMock(),
    )


async def test_webhook_commands_share_admin_or_allowed_authorization(monkeypatch):
    checked_chat_ids = []

    def deny(chat_id: int, user_id: int | None = None) -> bool:
        checked_chat_ids.append((chat_id, user_id))
        return False

    monkeypatch.setattr(commands, "_is_admin_or_allowed_chat", deny)
    monkeypatch.setattr(commands, "fetch_webhook_info", AsyncMock())
    monkeypatch.setattr(commands, "delete_webhook", AsyncMock())
    webhook_message = _message(chat_id=41, text="/webhook")
    delete_message = _message(chat_id=42, text="/deletewebhook")

    await commands.cmd_webhook_info(webhook_message)
    await commands.cmd_delete_webhook(delete_message)

    assert checked_chat_ids == [(41, 41), (42, 42)]
    commands.fetch_webhook_info.assert_not_awaited()
    commands.delete_webhook.assert_not_awaited()
    webhook_message.answer.assert_awaited_once_with("Webhook diagnostics are restricted.")
    delete_message.answer.assert_awaited_once_with(
        "Webhook lifecycle operations are restricted."
    )
