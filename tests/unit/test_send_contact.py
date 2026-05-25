from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.methods import SendContact

from bot.handlers import commands
from bot.services.send_contact import perform_send_contact

PHONE_NUMBER = "+1-202-555-0173"
FIRST_NAME = "Ada"
LAST_NAME = "Lovelace"


async def test_perform_send_contact_uses_typed_aiogram_api():
    sent = SimpleNamespace(message_id=777)
    bot = SimpleNamespace(send_contact=AsyncMock(return_value=sent))

    result = await perform_send_contact(
        bot,
        chat_id=42,
        phone_number=PHONE_NUMBER,
        first_name=FIRST_NAME,
    )

    assert result is sent
    bot.send_contact.assert_awaited_once_with(
        chat_id=42,
        phone_number=PHONE_NUMBER,
        first_name=FIRST_NAME,
        last_name=None,
        vcard=None,
        message_thread_id=None,
        disable_notification=None,
        protect_content=None,
    )


async def test_perform_send_contact_forwards_optional_fields():
    bot = SimpleNamespace(
        send_contact=AsyncMock(return_value=SimpleNamespace(message_id=1))
    )

    await perform_send_contact(
        bot,
        chat_id=42,
        phone_number=PHONE_NUMBER,
        first_name=FIRST_NAME,
        last_name=LAST_NAME,
        vcard="BEGIN:VCARD\nVERSION:3.0\nEND:VCARD",
    )

    _, kwargs = bot.send_contact.await_args
    assert kwargs["last_name"] == LAST_NAME
    assert kwargs["vcard"] == "BEGIN:VCARD\nVERSION:3.0\nEND:VCARD"


async def test_perform_send_contact_reraises_telegram_errors():
    error = TelegramBadRequest(
        method=SendContact(
            chat_id=1,
            phone_number=PHONE_NUMBER,
            first_name=FIRST_NAME,
        ),
        message="Bad Request: PHONE_NUMBER_INVALID",
    )
    bot = SimpleNamespace(send_contact=AsyncMock(side_effect=error))

    with pytest.raises(TelegramBadRequest):
        await perform_send_contact(
            bot,
            chat_id=1,
            phone_number=PHONE_NUMBER,
            first_name=FIRST_NAME,
        )


async def test_perform_send_contact_reraises_forbidden():
    error = TelegramForbiddenError(
        method=SendContact(
            chat_id=1,
            phone_number=PHONE_NUMBER,
            first_name=FIRST_NAME,
        ),
        message="Forbidden: bot was blocked by the user",
    )
    bot = SimpleNamespace(send_contact=AsyncMock(side_effect=error))

    with pytest.raises(TelegramForbiddenError):
        await perform_send_contact(
            bot,
            chat_id=1,
            phone_number=PHONE_NUMBER,
            first_name=FIRST_NAME,
        )


def _message(text: str = "/contact", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_contact_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_contact", AsyncMock())
    message = _message(
        text=f"/contact {PHONE_NUMBER} {FIRST_NAME}", chat_id=42
    )

    await commands.cmd_contact(message)

    commands.perform_send_contact.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_contact_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_contact", AsyncMock())
    message = _message(text="/contact", chat_id=42)

    await commands.cmd_contact(message)

    commands.perform_send_contact.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "contact usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_contact_shows_usage_without_first_name(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_contact", AsyncMock())
    message = _message(text=f"/contact {PHONE_NUMBER}", chat_id=42)

    await commands.cmd_contact(message)

    commands.perform_send_contact.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "contact usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_contact_shows_usage_for_empty_first_name(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_contact", AsyncMock())
    message = _message(text=f"/contact {PHONE_NUMBER} | {LAST_NAME}", chat_id=42)

    await commands.cmd_contact(message)

    commands.perform_send_contact.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "contact usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_contact_sends_with_first_name_only(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_send_contact", AsyncMock(return_value=object())
    )
    message = _message(text=f"/contact {PHONE_NUMBER} {FIRST_NAME}", chat_id=42)

    await commands.cmd_contact(message)

    commands.perform_send_contact.assert_awaited_once_with(
        message.bot,
        chat_id=42,
        phone_number=PHONE_NUMBER,
        first_name=FIRST_NAME,
        last_name=None,
    )
    args, _ = message.answer.await_args
    assert args[0] == "Sent contact."


async def test_cmd_contact_sends_with_last_name(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_send_contact", AsyncMock(return_value=object())
    )
    message = _message(
        text=f"/contact {PHONE_NUMBER} {FIRST_NAME} | {LAST_NAME}", chat_id=42
    )

    await commands.cmd_contact(message)

    _, kwargs = commands.perform_send_contact.await_args
    assert kwargs["first_name"] == FIRST_NAME
    assert kwargs["last_name"] == LAST_NAME


async def test_cmd_contact_keeps_spaces_in_names(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_send_contact", AsyncMock(return_value=object())
    )
    message = _message(
        text=f"/contact {PHONE_NUMBER}   Mary   Jane   |   Watson   Smith  ",
        chat_id=42,
    )

    await commands.cmd_contact(message)

    _, kwargs = commands.perform_send_contact.await_args
    assert kwargs["first_name"] == "Mary   Jane"
    assert kwargs["last_name"] == "Watson   Smith"


async def test_cmd_contact_treats_empty_last_name_segment_as_none(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_send_contact", AsyncMock(return_value=object())
    )
    message = _message(
        text=f"/contact {PHONE_NUMBER} {FIRST_NAME} |   ", chat_id=42
    )

    await commands.cmd_contact(message)

    _, kwargs = commands.perform_send_contact.await_args
    assert kwargs["first_name"] == FIRST_NAME
    assert kwargs["last_name"] is None


async def test_cmd_contact_reports_telegram_errors(monkeypatch):
    error = TelegramBadRequest(
        method=SendContact(
            chat_id=42,
            phone_number=PHONE_NUMBER,
            first_name=FIRST_NAME,
        ),
        message="Bad Request: chat not found",
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_send_contact", AsyncMock(side_effect=error)
    )
    message = _message(text=f"/contact {PHONE_NUMBER} {FIRST_NAME}", chat_id=42)

    await commands.cmd_contact(message)

    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Could not send the contact" in args[0]
