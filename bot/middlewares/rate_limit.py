import time
from collections import deque
from typing import Any, Awaitable, Callable, Deque, Dict

from aiogram import BaseMiddleware, types


class RateLimitMiddleware(BaseMiddleware):
    def __init__(
        self,
        requests_per_minute: int = 60,
        window_seconds: float = 60,
        cleanup_interval_seconds: float = 60,
        clock: Callable[[], float] | None = None,
    ):
        self.requests_per_minute = requests_per_minute
        self.window_seconds = window_seconds
        self.cleanup_interval_seconds = cleanup_interval_seconds
        self._clock = clock or time.monotonic
        self._last_cleanup = self._clock()
        self.user_timestamps: Dict[int, Deque[float]] = {}

    async def __call__(
        self,
        handler: Callable,
        event: types.TelegramObject,
        data: Dict[str, Any],
    ) -> Awaitable:
        user_id = None
        if isinstance(event, types.Message):
            user_id = event.from_user.id
        elif isinstance(event, types.CallbackQuery):
            user_id = event.from_user.id
        elif isinstance(event, types.InlineQuery):
            user_id = event.from_user.id

        if user_id is None:
            return await handler(event, data)

        now = self._clock()
        self._cleanup_if_due(now)

        timestamps = self.user_timestamps.get(user_id)
        if timestamps is None:
            timestamps = deque()
            self.user_timestamps[user_id] = timestamps
        else:
            self._prune_expired_timestamps(timestamps, now)

        if len(timestamps) >= self.requests_per_minute:
            # Rate limit exceeded
            if isinstance(event, types.Message):
                try:
                    await event.answer("⏳ Rate limit exceeded. Please wait a moment.")
                except Exception:
                    pass
            return  # skip handler
        timestamps.append(now)
        return await handler(event, data)

    def cleanup_expired(self, now: float | None = None) -> int:
        now = self._clock() if now is None else now
        self._last_cleanup = now
        removed = 0

        for user_id, timestamps in list(self.user_timestamps.items()):
            self._prune_expired_timestamps(timestamps, now)
            if not timestamps:
                self.user_timestamps.pop(user_id, None)
                removed += 1

        return removed

    def _cleanup_if_due(self, now: float):
        if self.cleanup_interval_seconds <= 0:
            self.cleanup_expired(now)
            return

        if now - self._last_cleanup >= self.cleanup_interval_seconds:
            self.cleanup_expired(now)

    def _prune_expired_timestamps(self, timestamps: Deque[float], now: float):
        expires_at = now - self.window_seconds
        while timestamps and timestamps[0] <= expires_at:
            timestamps.popleft()
