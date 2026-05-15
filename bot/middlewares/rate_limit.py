import time
from collections import defaultdict, deque
from aiogram import BaseMiddleware, types
from typing import Callable, Dict, Any, Awaitable

class RateLimitMiddleware(BaseMiddleware):
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.user_timestamps: Dict[int, deque] = defaultdict(lambda: deque())

    async def __call__(self, handler: Callable, event: types.TelegramObject, data: Dict[str, Any]) -> Awaitable:
        user_id = None
        if isinstance(event, types.Message):
            user_id = event.from_user.id
        elif isinstance(event, types.CallbackQuery):
            user_id = event.from_user.id
        elif isinstance(event, types.InlineQuery):
            user_id = event.from_user.id

        if user_id is None:
            return await handler(event, data)

        now = time.time()
        timestamps = self.user_timestamps[user_id]
        # Remove timestamps older than 60 seconds
        while timestamps and timestamps[0] < now - 60:
            timestamps.popleft()
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