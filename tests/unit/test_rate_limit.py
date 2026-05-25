import time
from unittest.mock import AsyncMock, MagicMock
from bot.middlewares.rate_limit import RateLimitMiddleware
from aiogram import types


async def _make_message(user_id: int) -> types.Message:
    msg = MagicMock(spec=types.Message)
    user = MagicMock()
    user.id = user_id
    msg.from_user = user
    msg.answer = AsyncMock()
    return msg


async def test_allows_within_limit():
    middleware = RateLimitMiddleware(requests_per_minute=5)
    handler = AsyncMock(return_value="ok")
    msg = await _make_message(1)
    result = await middleware(handler, msg, {})
    assert result == "ok"
    handler.assert_called_once()


async def test_blocks_when_limit_exceeded():
    middleware = RateLimitMiddleware(requests_per_minute=2)
    handler = AsyncMock(return_value="ok")
    msg = await _make_message(2)

    await middleware(handler, msg, {})
    await middleware(handler, msg, {})
    # Third call should be rate limited
    result = await middleware(handler, msg, {})
    assert result is None
    assert handler.call_count == 2
    msg.answer.assert_called_once()


async def test_resets_after_window():
    middleware = RateLimitMiddleware(requests_per_minute=1)
    handler = AsyncMock(return_value="ok")
    msg = await _make_message(3)

    await middleware(handler, msg, {})
    # Simulate passage of time by clearing timestamps
    middleware.user_timestamps[3].clear()
    # Should pass again
    result = await middleware(handler, msg, {})
    assert result == "ok"
    assert handler.call_count == 2
