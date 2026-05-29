from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import send_gift
from bot.services.send_gift import SendGiftError, perform_send_gift


class _FakeResponse:
    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data


class _FakeClient:
    """Minimal async-context-manager stand-in for ``httpx.AsyncClient``."""

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
    monkeypatch.setattr(send_gift.httpx, "AsyncClient", lambda *a, **k: client)


def _message(text: str = "/sendgift", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_perform_send_gift_posts_user_payload(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    result = await perform_send_gift(
        _bot(),
        user_id=777,
        gift_id="gift-1",
        text="thanks",
        text_parse_mode="HTML",
    )

    assert result is True
    assert client.posted["url"] == "https://api.telegram.org/bot123:abc/sendGift"
    assert client.posted["json"] == {
        "gift_id": "gift-1",
        "user_id": 777,
        "text": "thanks",
        "text_parse_mode": "HTML",
    }


async def test_perform_send_gift_posts_chat_payload(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    await perform_send_gift(_bot(), chat_id="@channel", gift_id="gift-1")

    assert client.posted["json"] == {"gift_id": "gift-1", "chat_id": "@channel"}


async def test_perform_send_gift_requires_exactly_one_receiver(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": True}))
    _install_client(monkeypatch, client)

    with pytest.raises(SendGiftError):
        await perform_send_gift(_bot(), gift_id="gift-1")

    with pytest.raises(SendGiftError):
        await perform_send_gift(
            _bot(), user_id=777, chat_id=42, gift_id="gift-1"
        )


async def test_perform_send_gift_raises_on_telegram_error(monkeypatch):
    client = _FakeClient(
        response=_FakeResponse(
            {
                "ok": False,
                "error_code": 400,
                "description": "Bad Request: not enough Stars",
            }
        )
    )
    _install_client(monkeypatch, client)

    with pytest.raises(SendGiftError) as excinfo:
        await perform_send_gift(_bot(), user_id=777, gift_id="gift-1")

    assert excinfo.value.error_code == 400
    assert "not enough Stars" in str(excinfo.value)


async def test_perform_send_gift_raises_on_transport_error(monkeypatch):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(SendGiftError):
        await perform_send_gift(_bot(), user_id=777, gift_id="gift-1")


async def test_perform_send_gift_rejects_unexpected_result(monkeypatch):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": {}}))
    _install_client(monkeypatch, client)

    with pytest.raises(SendGiftError):
        await perform_send_gift(_bot(), user_id=777, gift_id="gift-1")


def test_parse_send_gift_args_variants():
    assert commands._parse_send_gift_args("/sendgift user 777 gift-1") == (
        "user",
        777,
        "gift-1",
        False,
        None,
    )
    assert commands._parse_send_gift_args(
        "/sendgift chat @channel gift-1 confirm thanks"
    ) == ("chat", "@channel", "gift-1", True, "thanks")
    assert commands._parse_send_gift_args(
        "/sendgift chat -100123 gift-1 confirm"
    ) == ("chat", -100123, "gift-1", True, None)
    assert commands._parse_send_gift_args("/sendgift user bad gift-1") is None
    assert commands._parse_send_gift_args("/sendgift both 777 gift-1") is None
    assert commands._parse_send_gift_args(
        "/sendgift user 777 gift-1 maybe"
    ) is None


async def test_cmd_send_gift_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_gift", AsyncMock())
    message = _message(text="/sendgift user 777 gift-1 confirm", chat_id=42)

    await commands.cmd_send_gift(message)

    commands.perform_send_gift.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_send_gift_requires_confirmation(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_gift", AsyncMock())
    message = _message(text="/sendgift user 777 gift-1", chat_id=42)

    await commands.cmd_send_gift(message)

    commands.perform_send_gift.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "confirmation required" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_send_gift_sends_confirmed_user_gift(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_gift", AsyncMock(return_value=True))
    message = _message(text="/sendgift user 777 gift-1 confirm thanks", chat_id=42)

    await commands.cmd_send_gift(message)

    commands.perform_send_gift.assert_awaited_once_with(
        message.bot,
        gift_id="gift-1",
        text="thanks",
        text_parse_mode="HTML",
        user_id=777,
    )
    message.answer.assert_awaited_once_with("Sent gift.")


async def test_cmd_send_gift_rejects_too_long_text(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_gift", AsyncMock())
    text = "x" * (commands.SEND_GIFT_TEXT_LIMIT + 1)
    message = _message(text=f"/sendgift user 777 gift-1 confirm {text}", chat_id=42)

    await commands.cmd_send_gift(message)

    commands.perform_send_gift.assert_not_awaited()
    args, _ = message.answer.await_args
    assert "Gift text is too long" in args[0]


async def test_cmd_send_gift_reports_errors(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_send_gift",
        AsyncMock(side_effect=SendGiftError("Bad Request")),
    )
    message = _message(text="/sendgift user 777 gift-1 confirm", chat_id=42)

    await commands.cmd_send_gift(message)

    message.answer.assert_awaited_once_with("Could not send gift: Bad Request")
