from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import save_prepared_keyboard_button
from bot.services.save_prepared_keyboard_button import (
    SavePreparedKeyboardButtonError,
    perform_save_prepared_keyboard_button,
)

USER_ID = 123456789
PREPARED_MESSAGE_ID = "prepared-1"


class _FakeResponse:
    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data


class _FakeClient:
    def __init__(self, *, response=None, exc=None):
        self._response = response
        self._exc = exc
        self.posted = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, url, json):
        self.posted = {"url": url, "json": json}
        if self._exc is not None:
            raise self._exc
        return self._response


def _bot(token="123:abc"):
    return SimpleNamespace(
        token=token,
        session=SimpleNamespace(
            api=SimpleNamespace(
                api_url=lambda token, method: (
                    f"https://api.telegram.org/bot{token}/{method}"
                )
            )
        ),
    )


def _install_client(monkeypatch, client):
    monkeypatch.setattr(
        save_prepared_keyboard_button.httpx, "AsyncClient", lambda *a, **k: client
    )


async def test_perform_save_prepared_keyboard_button_posts_raw_payload(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    result = await perform_save_prepared_keyboard_button(
        _bot(),
        user_id=USER_ID,
        prepared_message_id=PREPARED_MESSAGE_ID,
    )

    assert result is True
    assert client.posted["url"] == (
        "https://api.telegram.org/bot123:abc/savePreparedKeyboardButton"
    )
    assert client.posted["json"] == {
        "user_id": USER_ID,
        "prepared_message_id": PREPARED_MESSAGE_ID,
    }


@pytest.mark.parametrize(
    ("user_id", "prepared_message_id"),
    [(0, PREPARED_MESSAGE_ID), (USER_ID, "   ")],
)
async def test_perform_save_prepared_keyboard_button_rejects_invalid_input(
    monkeypatch, user_id, prepared_message_id
):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    with pytest.raises(SavePreparedKeyboardButtonError):
        await perform_save_prepared_keyboard_button(
            _bot(),
            user_id=user_id,
            prepared_message_id=prepared_message_id,
        )

    assert client.posted is None


async def test_perform_save_prepared_keyboard_button_raises_on_telegram_error(
    monkeypatch,
):
    client = _FakeClient(
        response=_FakeResponse(
            {
                "ok": False,
                "error_code": 400,
                "description": "Bad Request: invalid prepared message",
            }
        )
    )
    _install_client(monkeypatch, client)

    with pytest.raises(SavePreparedKeyboardButtonError) as excinfo:
        await perform_save_prepared_keyboard_button(
            _bot(),
            user_id=USER_ID,
            prepared_message_id=PREPARED_MESSAGE_ID,
        )

    assert excinfo.value.error_code == 400
    assert "invalid prepared message" in str(excinfo.value)


async def test_perform_save_prepared_keyboard_button_raises_on_transport_error(
    monkeypatch,
):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(SavePreparedKeyboardButtonError):
        await perform_save_prepared_keyboard_button(
            _bot(),
            user_id=USER_ID,
            prepared_message_id=PREPARED_MESSAGE_ID,
        )


def test_parse_save_prepared_keyboard_button_args():
    assert commands._parse_save_prepared_keyboard_button_args(
        f"/savepreparedkeyboard {USER_ID} {PREPARED_MESSAGE_ID}"
    ) == (USER_ID, PREPARED_MESSAGE_ID)
    assert commands._parse_save_prepared_keyboard_button_args(
        "/savepreparedkeyboard"
    ) is None
    assert (
        commands._parse_save_prepared_keyboard_button_args(
            f"/savepreparedkeyboard not-int {PREPARED_MESSAGE_ID}"
        )
        is None
    )
    assert (
        commands._parse_save_prepared_keyboard_button_args(
            f"/savepreparedkeyboard {USER_ID}   "
        )
        is None
    )


def _message(text: str = "/savepreparedkeyboard", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_save_prepared_keyboard_button_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_save_prepared_keyboard_button", AsyncMock())
    message = _message(
        text=f"/savepreparedkeyboard {USER_ID} {PREPARED_MESSAGE_ID}",
        chat_id=42,
    )

    await commands.cmd_save_prepared_keyboard_button(message)

    commands.perform_save_prepared_keyboard_button.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_save_prepared_keyboard_button_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_save_prepared_keyboard_button", AsyncMock())
    message = _message(text="/savepreparedkeyboard", chat_id=42)

    await commands.cmd_save_prepared_keyboard_button(message)

    commands.perform_save_prepared_keyboard_button.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "savepreparedkeyboard usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_save_prepared_keyboard_button_saves_button(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_save_prepared_keyboard_button",
        AsyncMock(return_value=True),
    )
    message = _message(
        text=f"/savepreparedkeyboard {USER_ID} {PREPARED_MESSAGE_ID}",
        chat_id=42,
    )

    await commands.cmd_save_prepared_keyboard_button(message)

    commands.perform_save_prepared_keyboard_button.assert_awaited_once_with(
        message.bot,
        user_id=USER_ID,
        prepared_message_id=PREPARED_MESSAGE_ID,
    )
    message.answer.assert_awaited_once_with("Saved prepared keyboard button.")


async def test_cmd_save_prepared_keyboard_button_reports_errors(monkeypatch):
    error = SavePreparedKeyboardButtonError("Bad Request: invalid prepared message")
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_save_prepared_keyboard_button",
        AsyncMock(side_effect=error),
    )
    message = _message(
        text=f"/savepreparedkeyboard {USER_ID} {PREPARED_MESSAGE_ID}",
        chat_id=42,
    )

    await commands.cmd_save_prepared_keyboard_button(message)

    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Could not save the prepared keyboard button" in args[0]
