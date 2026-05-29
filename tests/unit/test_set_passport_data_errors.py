import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import set_passport_data_errors
from bot.services.set_passport_data_errors import (
    SetPassportDataErrorsError,
    perform_set_passport_data_errors,
)

USER_ID = 123456789
ERRORS = [
    {
        "source": "data",
        "type": "personal_details",
        "field_name": "first_name",
        "data_hash": "ZmllbGQtaGFzaA==",
        "message": "First name is invalid",
    }
]


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
        set_passport_data_errors.httpx, "AsyncClient", lambda *a, **k: client
    )


async def test_perform_set_passport_data_errors_posts_raw_payload(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    result = await perform_set_passport_data_errors(
        _bot(),
        user_id=USER_ID,
        errors=ERRORS,
    )

    assert result is True
    assert client.posted["url"] == (
        "https://api.telegram.org/bot123:abc/setPassportDataErrors"
    )
    assert client.posted["json"] == {
        "user_id": USER_ID,
        "errors": json.dumps(ERRORS),
    }
    assert json.loads(client.posted["json"]["errors"]) == ERRORS


@pytest.mark.parametrize(
    ("user_id", "errors"),
    [(0, ERRORS), (USER_ID, []), (USER_ID, ["not-an-object"]), (USER_ID, [{}])],
)
async def test_perform_set_passport_data_errors_rejects_invalid_input(
    monkeypatch, user_id, errors
):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    with pytest.raises(SetPassportDataErrorsError):
        await perform_set_passport_data_errors(
            _bot(),
            user_id=user_id,
            errors=errors,
        )

    assert client.posted is None


async def test_perform_set_passport_data_errors_raises_on_telegram_error(
    monkeypatch,
):
    client = _FakeClient(
        response=_FakeResponse(
            {
                "ok": False,
                "error_code": 400,
                "description": "Bad Request: wrong user_id specified",
            }
        )
    )
    _install_client(monkeypatch, client)

    with pytest.raises(SetPassportDataErrorsError) as excinfo:
        await perform_set_passport_data_errors(
            _bot(),
            user_id=USER_ID,
            errors=ERRORS,
        )

    assert excinfo.value.error_code == 400
    assert "wrong user_id" in str(excinfo.value)


async def test_perform_set_passport_data_errors_raises_on_transport_error(
    monkeypatch,
):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(SetPassportDataErrorsError):
        await perform_set_passport_data_errors(
            _bot(),
            user_id=USER_ID,
            errors=ERRORS,
        )


def test_parse_set_passport_data_errors_args():
    assert commands._parse_set_passport_data_errors_args(
        f"/setpassporterrors {USER_ID} {json.dumps(ERRORS)}"
    ) == (USER_ID, ERRORS)
    assert commands._parse_set_passport_data_errors_args("/setpassporterrors") is None
    assert (
        commands._parse_set_passport_data_errors_args(
            f"/setpassporterrors not-int {json.dumps(ERRORS)}"
        )
        is None
    )
    assert (
        commands._parse_set_passport_data_errors_args(
            f"/setpassporterrors {USER_ID} {{}}"
        )
        is None
    )


def _message(text: str = "/setpassporterrors", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_set_passport_data_errors_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_set_passport_data_errors", AsyncMock())
    message = _message(
        text=f"/setpassporterrors {USER_ID} {json.dumps(ERRORS)}",
        chat_id=42,
    )

    await commands.cmd_set_passport_data_errors(message)

    commands.perform_set_passport_data_errors.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_set_passport_data_errors_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_set_passport_data_errors", AsyncMock())
    message = _message(text="/setpassporterrors", chat_id=42)

    await commands.cmd_set_passport_data_errors(message)

    commands.perform_set_passport_data_errors.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "setpassporterrors usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_set_passport_data_errors_sets_errors(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_set_passport_data_errors",
        AsyncMock(return_value=True),
    )
    message = _message(
        text=f"/setpassporterrors {USER_ID} {json.dumps(ERRORS)}",
        chat_id=42,
    )

    await commands.cmd_set_passport_data_errors(message)

    commands.perform_set_passport_data_errors.assert_awaited_once_with(
        message.bot,
        user_id=USER_ID,
        errors=ERRORS,
    )
    message.answer.assert_awaited_once_with(
        f"Set {len(ERRORS)} Passport data error(s) for user {USER_ID}."
    )


async def test_cmd_set_passport_data_errors_reports_service_error(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_set_passport_data_errors",
        AsyncMock(side_effect=SetPassportDataErrorsError("telegram rejected")),
    )
    message = _message(
        text=f"/setpassporterrors {USER_ID} {json.dumps(ERRORS)}",
        chat_id=42,
    )

    await commands.cmd_set_passport_data_errors(message)

    message.answer.assert_awaited_once_with(
        "Could not set Passport data errors: telegram rejected"
    )
