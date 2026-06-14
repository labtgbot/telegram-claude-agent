"""Regression tests for issue #410.

The bot is configured with a default ``parse_mode=ParseMode.HTML``. Every
fallback path that retries a failed send must therefore pass ``parse_mode=None``
explicitly, otherwise the retry re-applies HTML and fails the same way, losing
the message entirely. The fallbacks must also be wrapped in ``try/except`` so an
exception never escapes the safety net.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import GetWebhookInfo

import bot.handlers.chat as chat


def _bad_request() -> TelegramBadRequest:
    return TelegramBadRequest(
        method=GetWebhookInfo(),
        message="Bad Request: can't parse entities: overlap </b> over ['i']",
    )


@pytest.mark.asyncio
async def test_send_reply_safely_falls_back_to_plain_text():
    """The HTML send fails, the plain (parse_mode=None) retry succeeds."""
    answer = AsyncMock(side_effect=[_bad_request(), None])
    message = SimpleNamespace(answer=answer)

    await chat.send_reply_safely(message, "Here is <b><i>broken</b></i> text")

    assert answer.await_count == 2
    # First attempt uses HTML (the default parse_mode argument).
    assert answer.await_args_list[0].kwargs["parse_mode"] == "HTML"
    # Fallback must explicitly disable parsing.
    assert answer.await_args_list[1].kwargs["parse_mode"] is None


@pytest.mark.asyncio
async def test_send_reply_safely_swallows_fallback_exception():
    """If even the plain fallback fails, no exception escapes."""
    answer = AsyncMock(side_effect=[_bad_request(), _bad_request()])
    message = SimpleNamespace(answer=answer)

    # Must not raise.
    await chat.send_reply_safely(message, "text")

    assert answer.await_count == 2


@pytest.mark.asyncio
async def test_try_edit_stream_preview_uses_plain_parse_mode():
    """Raw streamed text must be previewed with parse_mode=None."""
    sent_msg = SimpleNamespace(edit_text=AsyncMock())

    edited, error_logged = await chat._try_edit_stream_preview(
        sent_msg, "partial <tag stream", error_logged=False
    )

    assert edited is True
    assert sent_msg.edit_text.await_args.kwargs["parse_mode"] is None


@pytest.mark.asyncio
async def test_handle_streaming_final_edit_falls_back_to_plain(monkeypatch):
    """The final streaming edit retries with parse_mode=None on HTML failure."""

    class _StreamingClient:
        async def send_message(self, *args, **kwargs):
            async def _gen():
                yield {
                    "type": "content_block_delta",
                    "delta": {"type": "text_delta", "text": "**hi**"},
                }

            return _gen()

        async def close(self):
            pass

    # edit_text: first the preview ("…" replacement), then final HTML edit fails,
    # then the plain fallback succeeds.
    edit_text = AsyncMock(side_effect=[None, _bad_request(), None])
    sent_msg = SimpleNamespace(edit_text=edit_text)
    message = SimpleNamespace(answer=AsyncMock(return_value=sent_msg))

    await chat.handle_streaming(message, _StreamingClient(), [], "claude-test")

    # The last edit_text call is the plain fallback with parse_mode=None.
    assert edit_text.await_args_list[-1].kwargs["parse_mode"] is None


@pytest.mark.asyncio
async def test_handle_streaming_extra_chunks_fall_back_to_plain(monkeypatch):
    """Extra chunks (chunks[1:]) retry with parse_mode=None on HTML failure."""
    monkeypatch.setattr(chat, "TELEGRAM_MESSAGE_LIMIT", 5)

    long_text = "abcde" * 4  # 20 chars -> multiple chunks at limit 5

    class _StreamingClient:
        async def send_message(self, *args, **kwargs):
            async def _gen():
                yield {
                    "type": "content_block_delta",
                    "delta": {"type": "text_delta", "text": long_text},
                }

            return _gen()

        async def close(self):
            pass

    sent_msg = SimpleNamespace(edit_text=AsyncMock())
    # answer: first the "…" placeholder, then extra-chunk HTML send fails,
    # then plain fallback succeeds (repeated for each extra chunk).
    answer = AsyncMock(
        side_effect=[sent_msg, _bad_request(), None, _bad_request(), None, _bad_request(), None]
    )
    message = SimpleNamespace(answer=answer)

    await chat.handle_streaming(message, _StreamingClient(), [], "claude-test")

    # Among the extra-chunk answer calls, every plain fallback uses parse_mode=None.
    plain_calls = [
        c for c in answer.await_args_list if c.kwargs.get("parse_mode") is None
    ]
    assert plain_calls, "expected at least one plain fallback answer"
