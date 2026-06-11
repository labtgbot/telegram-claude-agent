from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import remove_business_account_profile_photo
from bot.services.remove_business_account_profile_photo import (
    RemoveBusinessAccountProfilePhotoError,
    format_remove_business_account_profile_photo_result,
    perform_remove_business_account_profile_photo,
)


BUSINESS_CONNECTION_ID = "bizconn-123"


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
        remove_business_account_profile_photo.httpx,
        "AsyncClient",
        lambda *a, **k: client,
    )


def _message(text: str = "/removebusinessaccountprofilephoto", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_perform_remove_business_account_profile_photo_posts_payload(
    monkeypatch,
):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    result = await perform_remove_business_account_profile_photo(
        _bot(),
        business_connection_id=f" {BUSINESS_CONNECTION_ID} ",
        is_public=True,
    )

    assert result is True
    assert client.posted == {
        "url": "https://api.telegram.org/bot123:abc/removeBusinessAccountProfilePhoto",
        "json": {
            "business_connection_id": BUSINESS_CONNECTION_ID,
            "is_public": True,
        },
    }


async def test_perform_remove_business_account_profile_photo_omits_false_public_flag(
    monkeypatch,
):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    await perform_remove_business_account_profile_photo(
        _bot(),
        business_connection_id=BUSINESS_CONNECTION_ID,
    )

    assert client.posted["json"] == {
        "business_connection_id": BUSINESS_CONNECTION_ID,
    }


async def test_perform_remove_business_account_profile_photo_rejects_missing_id(
    monkeypatch,
):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    with pytest.raises(RemoveBusinessAccountProfilePhotoError):
        await perform_remove_business_account_profile_photo(
            _bot(),
            business_connection_id="",
        )

    assert client.posted is None


async def test_perform_remove_business_account_profile_photo_raises_on_telegram_error(
    monkeypatch,
):
    client = _FakeClient(
        response=_FakeResponse(
            {
                "ok": False,
                "error_code": 403,
                "description": "Forbidden: bot lacks can_edit_profile_photo right",
            }
        )
    )
    _install_client(monkeypatch, client)

    with pytest.raises(RemoveBusinessAccountProfilePhotoError) as excinfo:
        await perform_remove_business_account_profile_photo(
            _bot(),
            business_connection_id=BUSINESS_CONNECTION_ID,
        )

    assert excinfo.value.error_code == 403
    assert "can_edit_profile_photo" in str(excinfo.value)


async def test_perform_remove_business_account_profile_photo_raises_on_transport_error(
    monkeypatch,
):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(RemoveBusinessAccountProfilePhotoError) as excinfo:
        await perform_remove_business_account_profile_photo(
            _bot(),
            business_connection_id=BUSINESS_CONNECTION_ID,
        )

    assert "boom" in str(excinfo.value)


def test_format_remove_business_account_profile_photo_result_escapes_fields():
    text = format_remove_business_account_profile_photo_result(
        business_connection_id="biz<&>",
        is_public=True,
    )

    assert "removeBusinessAccountProfilePhoto" in text
    assert "biz&lt;&amp;&gt;" in text
    assert "public fallback photo" in text
    assert "Rollback" in text


def test_parse_remove_business_account_profile_photo_args():
    assert commands._parse_remove_business_account_profile_photo_args(
        f"/removebusinessaccountprofilephoto {BUSINESS_CONNECTION_ID} confirm"
    ) == (BUSINESS_CONNECTION_ID, False)
    assert commands._parse_remove_business_account_profile_photo_args(
        f"/removebusinessaccountprofilephoto {BUSINESS_CONNECTION_ID} public=true confirm"
    ) == (BUSINESS_CONNECTION_ID, True)
    assert commands._parse_remove_business_account_profile_photo_args(
        f"/removebusinessaccountprofilephoto {BUSINESS_CONNECTION_ID} public=false confirm"
    ) == (BUSINESS_CONNECTION_ID, False)
    assert (
        commands._parse_remove_business_account_profile_photo_args(
            f"/removebusinessaccountprofilephoto {BUSINESS_CONNECTION_ID}"
        )
        is None
    )
    assert (
        commands._parse_remove_business_account_profile_photo_args(
            f"/removebusinessaccountprofilephoto {BUSINESS_CONNECTION_ID} public=maybe confirm"
        )
        is None
    )


async def test_cmd_remove_business_account_profile_photo_rejects_unlisted_chat(
    monkeypatch,
):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_remove_business_account_profile_photo",
        AsyncMock(),
    )
    message = _message(
        text=f"/removebusinessaccountprofilephoto {BUSINESS_CONNECTION_ID} confirm",
        chat_id=42,
    )

    await commands.cmd_remove_business_account_profile_photo(message)

    commands.perform_remove_business_account_profile_photo.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_remove_business_account_profile_photo_shows_usage_without_args(
    monkeypatch,
):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_remove_business_account_profile_photo",
        AsyncMock(),
    )
    message = _message(text="/removebusinessaccountprofilephoto", chat_id=42)

    await commands.cmd_remove_business_account_profile_photo(message)

    commands.perform_remove_business_account_profile_photo.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "removebusinessaccountprofilephoto usage" in args[0]
    assert "confirm" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_remove_business_account_profile_photo_calls_service(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_remove_business_account_profile_photo",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(
        commands,
        "format_remove_business_account_profile_photo_result",
        lambda **_: "ok",
    )
    message = _message(
        text=(
            f"/removebusinessaccountprofilephoto {BUSINESS_CONNECTION_ID} "
            "public=true confirm"
        ),
        chat_id=42,
    )

    await commands.cmd_remove_business_account_profile_photo(message)

    commands.perform_remove_business_account_profile_photo.assert_awaited_once_with(
        message.bot,
        business_connection_id=BUSINESS_CONNECTION_ID,
        is_public=True,
    )
    message.answer.assert_awaited_once_with("ok", parse_mode="HTML")


async def test_cmd_remove_business_account_profile_photo_reports_errors(monkeypatch):
    error = RemoveBusinessAccountProfilePhotoError(
        "Forbidden: bot lacks can_edit_profile_photo right",
        error_code=403,
    )
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_remove_business_account_profile_photo",
        AsyncMock(side_effect=error),
    )
    message = _message(
        text=f"/removebusinessaccountprofilephoto {BUSINESS_CONNECTION_ID} confirm",
        chat_id=42,
    )

    await commands.cmd_remove_business_account_profile_photo(message)

    args, _ = message.answer.await_args
    assert "Could not remove the business account profile photo" in args[0]
    assert "can_edit_profile_photo" not in args[0]
    assert "Please try again later" in args[0]
