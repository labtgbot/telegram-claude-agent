from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import send_poll
from bot.services.send_poll import SendPollError, perform_send_poll

QUESTION = "What is the best editor?"
OPTIONS = ["Vim", "Emacs", "VS Code"]


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
    monkeypatch.setattr(send_poll.httpx, "AsyncClient", lambda *a, **k: client)


async def test_perform_send_poll_posts_current_raw_payload(monkeypatch):
    client = _FakeClient(
        response=_FakeResponse({"ok": True, "result": {"message_id": 777}})
    )
    _install_client(monkeypatch, client)

    result = await perform_send_poll(
        _bot(),
        chat_id=42,
        question=QUESTION,
        options=OPTIONS,
    )

    assert result == {"message_id": 777}
    assert client.posted["url"] == "https://api.telegram.org/bot123:abc/sendPoll"
    assert client.posted["json"] == {
        "chat_id": 42,
        "question": QUESTION,
        "options": [{"text": "Vim"}, {"text": "Emacs"}, {"text": "VS Code"}],
    }


async def test_perform_send_poll_forwards_current_metadata(monkeypatch):
    client = _FakeClient(
        response=_FakeResponse({"ok": True, "result": {"message_id": 1}})
    )
    _install_client(monkeypatch, client)

    await perform_send_poll(
        _bot(),
        chat_id=42,
        question=QUESTION,
        options=OPTIONS,
        type="quiz",
        correct_option_ids=[2],
        explanation="VS Code is the answer.",
        explanation_media={"type": "photo", "media": "https://example.com/a.jpg"},
        is_anonymous=False,
        open_period=60,
        allows_revoting=True,
    )

    assert client.posted["json"]["type"] == "quiz"
    assert client.posted["json"]["correct_option_ids"] == [2]
    assert client.posted["json"]["explanation"] == "VS Code is the answer."
    assert client.posted["json"]["explanation_media"] == {
        "type": "photo",
        "media": "https://example.com/a.jpg",
    }
    assert client.posted["json"]["is_anonymous"] is False
    assert client.posted["json"]["open_period"] == 60
    assert client.posted["json"]["allows_revoting"] is True


async def test_perform_send_poll_forwards_option_media_link(monkeypatch):
    client = _FakeClient(
        response=_FakeResponse({"ok": True, "result": {"message_id": 1}})
    )
    _install_client(monkeypatch, client)

    await perform_send_poll(
        _bot(),
        chat_id=42,
        question=QUESTION,
        options=[
            "Plain",
            {
                "text": "Read more",
                "media": {"type": "link", "url": "https://example.com"},
            },
        ],
    )

    assert client.posted["json"]["options"] == [
        {"text": "Plain"},
        {
            "text": "Read more",
            "media": {"type": "link", "url": "https://example.com"},
        },
    ]


async def test_perform_send_poll_raises_on_telegram_error(monkeypatch):
    client = _FakeClient(
        response=_FakeResponse(
            {
                "ok": False,
                "error_code": 400,
                "description": "Bad Request: chat not found",
            }
        )
    )
    _install_client(monkeypatch, client)

    with pytest.raises(SendPollError) as excinfo:
        await perform_send_poll(
            _bot(),
            chat_id=1,
            question=QUESTION,
            options=OPTIONS,
        )

    assert excinfo.value.error_code == 400
    assert "chat not found" in str(excinfo.value)


async def test_perform_send_poll_raises_on_transport_error(monkeypatch):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(SendPollError):
        await perform_send_poll(
            _bot(),
            chat_id=1,
            question=QUESTION,
            options=OPTIONS,
        )


def _message(text: str = "/poll", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_poll_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_poll", AsyncMock())
    message = _message(text=f"/poll {QUESTION} | Vim | Emacs", chat_id=42)

    await commands.cmd_poll(message)

    commands.perform_send_poll.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_poll_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_poll", AsyncMock())
    message = _message(text="/poll", chat_id=42)

    await commands.cmd_poll(message)

    commands.perform_send_poll.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "poll usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_poll_shows_usage_without_options(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_poll", AsyncMock())
    message = _message(text="/poll Just a question with no separator", chat_id=42)

    await commands.cmd_poll(message)

    commands.perform_send_poll.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "poll usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_poll_shows_usage_for_empty_option(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_poll", AsyncMock())
    message = _message(text=f"/poll {QUESTION} | Vim | ", chat_id=42)

    await commands.cmd_poll(message)

    commands.perform_send_poll.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "poll usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_poll_shows_usage_for_empty_question(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_poll", AsyncMock())
    message = _message(text="/poll  | Vim | Emacs", chat_id=42)

    await commands.cmd_poll(message)

    commands.perform_send_poll.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "poll usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_poll_sends_poll(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_send_poll", AsyncMock(return_value=object())
    )
    message = _message(text=f"/poll {QUESTION} | Vim | Emacs | VS Code", chat_id=42)

    await commands.cmd_poll(message)

    commands.perform_send_poll.assert_awaited_once_with(
        message.bot,
        chat_id=42,
        question=QUESTION,
        options=["Vim", "Emacs", "VS Code"],
    )
    args, _ = message.answer.await_args
    assert args[0] == "Sent poll with 3 options."


async def test_cmd_poll_sends_option_media_links(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_send_poll", AsyncMock(return_value=object())
    )
    message = _message(
        text=f"/poll {QUESTION} | Docs => https://example.com/docs | Plain",
        chat_id=42,
    )

    await commands.cmd_poll(message)

    commands.perform_send_poll.assert_awaited_once_with(
        message.bot,
        chat_id=42,
        question=QUESTION,
        options=[
            {
                "text": "Docs",
                "media": {"type": "link", "url": "https://example.com/docs"},
            },
            "Plain",
        ],
    )
    args, _ = message.answer.await_args
    assert args[0] == "Sent poll with 2 options."


async def test_cmd_poll_keeps_spaces_in_question_and_options(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_send_poll", AsyncMock(return_value=object())
    )
    message = _message(
        text="/poll  The   Question   |   Option  One  |  Option  Two  ",
        chat_id=42,
    )

    await commands.cmd_poll(message)

    _, kwargs = commands.perform_send_poll.await_args
    assert kwargs["question"] == "The   Question"
    assert kwargs["options"] == ["Option  One", "Option  Two"]


async def test_cmd_poll_sends_single_option(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_send_poll", AsyncMock(return_value=object())
    )
    message = _message(text=f"/poll {QUESTION} | Only one", chat_id=42)

    await commands.cmd_poll(message)

    commands.perform_send_poll.assert_awaited_once_with(
        message.bot,
        chat_id=42,
        question=QUESTION,
        options=["Only one"],
    )
    args, _ = message.answer.await_args
    assert args[0] == "Sent poll with 1 options."


async def test_cmd_poll_rejects_too_many_options(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_poll", AsyncMock())
    options = " | ".join(f"Option {i}" for i in range(13))
    message = _message(text=f"/poll {QUESTION} | {options}", chat_id=42)

    await commands.cmd_poll(message)

    commands.perform_send_poll.assert_not_awaited()
    args, _ = message.answer.await_args
    assert "A poll needs between" in args[0]


async def test_cmd_poll_rejects_too_long_question(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_poll", AsyncMock())
    long_question = "Q" * 301
    message = _message(text=f"/poll {long_question} | Vim | Emacs", chat_id=42)

    await commands.cmd_poll(message)

    commands.perform_send_poll.assert_not_awaited()
    args, _ = message.answer.await_args
    assert "Question is too long" in args[0]


async def test_cmd_poll_rejects_too_long_option(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_poll", AsyncMock())
    long_option = "A" * 101
    message = _message(text=f"/poll {QUESTION} | Vim | {long_option}", chat_id=42)

    await commands.cmd_poll(message)

    commands.perform_send_poll.assert_not_awaited()
    args, _ = message.answer.await_args
    assert "Option is too long" in args[0]


async def test_cmd_poll_rejects_empty_link_option_text(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_poll", AsyncMock())
    message = _message(text=f"/poll {QUESTION} | => https://example.com")

    await commands.cmd_poll(message)

    commands.perform_send_poll.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "poll usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_poll_rejects_invalid_link_option_url(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_send_poll", AsyncMock())
    message = _message(text=f"/poll {QUESTION} | Docs => ftp://example.com")

    await commands.cmd_poll(message)

    commands.perform_send_poll.assert_not_awaited()
    args, kwargs = message.answer.await_args
    assert "poll usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_poll_reports_telegram_errors(monkeypatch):
    error = SendPollError("Bad Request: chat not found", error_code=400)
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_send_poll", AsyncMock(side_effect=error)
    )
    message = _message(text=f"/poll {QUESTION} | Vim | Emacs", chat_id=42)

    await commands.cmd_poll(message)

    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Could not send the poll" in args[0]
