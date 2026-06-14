"""Regression tests for issue #409.

The logging and rate-limit middlewares used to be registered on ``dp.update``,
which feeds them the raw ``Update`` object instead of the concrete
``Message``/``CallbackQuery``/``InlineQuery`` event. Because both middlewares
branch on ``isinstance(event, types.Message)`` (etc.) — always False for an
``Update`` — logging never recorded per-event details and rate limiting was
never enforced.

These tests exercise the middlewares through the *real* ``Dispatcher.feed_update``
path so the production wiring is verified end to end, not just the middleware's
``__call__`` in isolation. They also cover updates whose ``from_user`` is None
(channel posts, anonymous admins) which must not crash the outermost layer.
"""

from datetime import datetime, timezone

import pytest
from aiogram import Bot, Dispatcher, Router, types
from aiogram.client.default import DefaultBotProperties

from bot.middlewares.logging import LoggingMiddleware
from bot.middlewares.rate_limit import RateLimitMiddleware


def _build_dispatcher(rate_limit: RateLimitMiddleware) -> tuple[Dispatcher, Router, list]:
    """Wire a dispatcher exactly like bot/main.py does (issue #409 fix)."""
    dp = Dispatcher()
    logging_middleware = LoggingMiddleware()
    for observer in (dp.message, dp.callback_query, dp.inline_query):
        observer.middleware(logging_middleware)
        observer.middleware(rate_limit)

    router = Router()
    handled = []

    @router.message()
    async def _on_message(message: types.Message):
        handled.append(("message", message))

    dp.include_router(router)
    return dp, router, handled


def _message_update(update_id: int, user_id: int, text: str = "hi") -> types.Update:
    return types.Update.model_construct(
        update_id=update_id,
        message=types.Message.model_construct(
            message_id=update_id,
            date=datetime.now(timezone.utc),
            chat=types.Chat.model_construct(id=user_id, type="private"),
            from_user=types.User.model_construct(
                id=user_id, is_bot=False, first_name="Tester"
            ),
            text=text,
        ),
    )


def _channel_post_update(update_id: int) -> types.Update:
    """A channel post: ``from_user`` is None."""
    return types.Update.model_construct(
        update_id=update_id,
        message=types.Message.model_construct(
            message_id=update_id,
            date=datetime.now(timezone.utc),
            chat=types.Chat.model_construct(id=-100123, type="channel"),
            from_user=None,
            text="from a channel",
        ),
    )


@pytest.fixture
def bot():
    return Bot(token="123:abc", default=DefaultBotProperties())


async def test_rate_limit_enforced_through_dispatcher(bot):
    """With the fix, the rate limiter actually blocks via feed_update."""
    rate_limit = RateLimitMiddleware(requests_per_minute=2)
    dp, _, handled = _build_dispatcher(rate_limit)

    for update_id in range(1, 6):
        await dp.feed_update(bot, _message_update(update_id, user_id=42))

    # Only the first two updates from the same user reach the handler; the
    # remaining three are rate limited.
    assert len(handled) == 2
    assert rate_limit.user_timestamps.get(42) is not None
    assert len(rate_limit.user_timestamps[42]) == 2

    await bot.session.close()


async def test_logging_middleware_does_not_crash_on_missing_from_user(bot):
    """Channel posts (from_user=None) must still reach the handler."""
    rate_limit = RateLimitMiddleware(requests_per_minute=10)
    dp, _, handled = _build_dispatcher(rate_limit)

    # Should not raise AttributeError; the handler still runs.
    await dp.feed_update(bot, _channel_post_update(1))

    assert len(handled) == 1
    # No user_id could be derived, so the rate limiter recorded nothing.
    assert rate_limit.user_timestamps == {}

    await bot.session.close()


async def test_rate_limit_ignores_events_without_from_user():
    """The rate limiter passes through events lacking a from_user."""
    rate_limit = RateLimitMiddleware(requests_per_minute=1)
    calls = []

    async def handler(event, data):
        calls.append(event)
        return "ok"

    message = types.Message.model_construct(
        message_id=1,
        date=datetime.now(timezone.utc),
        chat=types.Chat.model_construct(id=-100123, type="channel"),
        from_user=None,
        text="from a channel",
    )

    result = await rate_limit(handler, message, {})

    assert result == "ok"
    assert calls == [message]
    assert rate_limit.user_timestamps == {}


async def test_logging_middleware_handles_none_from_user_directly():
    """LoggingMiddleware must not raise when from_user is None."""
    mw = LoggingMiddleware()
    calls = []

    async def handler(event, data):
        calls.append(event)
        return "handler-ran"

    message = types.Message.model_construct(
        message_id=1,
        date=datetime.now(timezone.utc),
        chat=types.Chat.model_construct(id=-100123, type="channel"),
        from_user=None,
        text="from a channel",
    )

    result = await mw(handler, message, {})

    assert result == "handler-ran"
    assert calls == [message]
