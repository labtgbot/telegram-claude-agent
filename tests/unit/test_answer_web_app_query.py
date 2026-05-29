import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from bot.handlers import commands
from bot.services import answer_web_app_query
from bot.services.answer_web_app_query import (
    AnswerWebAppQueryError,
    perform_answer_web_app_query,
)

WEB_APP_QUERY_ID = "AAEAAAE-web-app-query"
RESULT = {
    "type": "article",
    "id": "article-1",
    "title": "Result title",
    "input_message_content": {
        "message_text": "Message from Web App",
    },
}


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
        answer_web_app_query.httpx, "AsyncClient", lambda *a, **k: client
    )


async def test_perform_answer_web_app_query_posts_raw_payload(monkeypatch):
    client = _FakeClient(
        response=_FakeResponse(
            {"ok": True, "result": {"inline_message_id": "inline-1"}}
        )
    )
    _install_client(monkeypatch, client)

    result = await perform_answer_web_app_query(
        _bot(),
        web_app_query_id=WEB_APP_QUERY_ID,
        result=RESULT,
    )

    assert result == {"inline_message_id": "inline-1"}
    assert client.posted["url"] == (
        "https://api.telegram.org/bot123:abc/answerWebAppQuery"
    )
    assert client.posted["json"] == {
        "web_app_query_id": WEB_APP_QUERY_ID,
        "result": json.dumps(RESULT),
    }
    assert json.loads(client.posted["json"]["result"]) == RESULT


@pytest.mark.parametrize(
    ("web_app_query_id", "result"),
    [("", RESULT), (WEB_APP_QUERY_ID, {})],
)
async def test_perform_answer_web_app_query_rejects_invalid_input(
    monkeypatch, web_app_query_id, result
):
    client = _FakeClient(response=_FakeResponse({"ok": True, "result": {}}))
    _install_client(monkeypatch, client)

    with pytest.raises(AnswerWebAppQueryError):
        await perform_answer_web_app_query(
            _bot(),
            web_app_query_id=web_app_query_id,
            result=result,
        )

    assert client.posted is None


async def test_perform_answer_web_app_query_raises_on_telegram_error(monkeypatch):
    client = _FakeClient(
        response=_FakeResponse(
            {
                "ok": False,
                "error_code": 400,
                "description": "Bad Request: query is too old",
            }
        )
    )
    _install_client(monkeypatch, client)

    with pytest.raises(AnswerWebAppQueryError) as excinfo:
        await perform_answer_web_app_query(
            _bot(),
            web_app_query_id=WEB_APP_QUERY_ID,
            result=RESULT,
        )

    assert excinfo.value.error_code == 400
    assert "query is too old" in str(excinfo.value)


async def test_perform_answer_web_app_query_raises_on_transport_error(monkeypatch):
    client = _FakeClient(exc=httpx.ConnectError("boom"))
    _install_client(monkeypatch, client)

    with pytest.raises(AnswerWebAppQueryError):
        await perform_answer_web_app_query(
            _bot(),
            web_app_query_id=WEB_APP_QUERY_ID,
            result=RESULT,
        )


def test_parse_answer_web_app_query_args():
    assert commands._parse_answer_web_app_query_args(
        f"/answerwebappquery {WEB_APP_QUERY_ID} {json.dumps(RESULT)}"
    ) == (WEB_APP_QUERY_ID, RESULT)
    assert commands._parse_answer_web_app_query_args("/answerwebappquery") is None
    assert (
        commands._parse_answer_web_app_query_args(
            f"/answerwebappquery {WEB_APP_QUERY_ID} not-json"
        )
        is None
    )
    assert (
        commands._parse_answer_web_app_query_args(
            f"/answerwebappquery {WEB_APP_QUERY_ID} []"
        )
        is None
    )


def _message(text: str = "/answerwebappquery", chat_id: int = 42):
    return SimpleNamespace(
        text=text,
        chat=SimpleNamespace(id=chat_id),
        bot=object(),
        answer=AsyncMock(),
    )


async def test_cmd_answer_web_app_query_rejects_unlisted_chat(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "")
    monkeypatch.setattr(commands.settings, "telegram_allowed_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_answer_web_app_query", AsyncMock())
    message = _message(
        text=f"/answerwebappquery {WEB_APP_QUERY_ID} {json.dumps(RESULT)}",
        chat_id=42,
    )

    await commands.cmd_answer_web_app_query(message)

    commands.perform_answer_web_app_query.assert_not_awaited()
    message.answer.assert_awaited_once_with(
        "This command is restricted to admin chats."
    )


async def test_cmd_answer_web_app_query_shows_usage_without_args(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(commands, "perform_answer_web_app_query", AsyncMock())
    message = _message(text="/answerwebappquery", chat_id=42)

    await commands.cmd_answer_web_app_query(message)

    commands.perform_answer_web_app_query.assert_not_awaited()
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "answerwebappquery usage" in args[0]
    assert kwargs["parse_mode"] == "HTML"


async def test_cmd_answer_web_app_query_answers_query(monkeypatch):
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands,
        "perform_answer_web_app_query",
        AsyncMock(return_value={"inline_message_id": "inline-1"}),
    )
    message = _message(
        text=f"/answerwebappquery {WEB_APP_QUERY_ID} {json.dumps(RESULT)}",
        chat_id=42,
    )

    await commands.cmd_answer_web_app_query(message)

    commands.perform_answer_web_app_query.assert_awaited_once_with(
        message.bot,
        web_app_query_id=WEB_APP_QUERY_ID,
        result=RESULT,
    )
    message.answer.assert_awaited_once_with(
        "Answered Web App query: inline message inline-1."
    )


async def test_cmd_answer_web_app_query_reports_errors(monkeypatch):
    error = AnswerWebAppQueryError("Bad Request: query is too old", error_code=400)
    monkeypatch.setattr(commands.settings, "telegram_admin_chat_ids", "42")
    monkeypatch.setattr(
        commands, "perform_answer_web_app_query", AsyncMock(side_effect=error)
    )
    message = _message(
        text=f"/answerwebappquery {WEB_APP_QUERY_ID} {json.dumps(RESULT)}",
        chat_id=42,
    )

    await commands.cmd_answer_web_app_query(message)

    message.answer.assert_awaited_once()
    args, _ = message.answer.await_args
    assert "Could not answer the Web App query" in args[0]
