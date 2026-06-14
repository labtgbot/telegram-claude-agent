import time
from typing import Any, Callable, Dict, List, Tuple


HistoryKey = Tuple[int, int]
Clock = Callable[[], float]


class MemoryStorage:
    def __init__(
        self,
        max_history: int = 20,
        ttl_seconds: float | None = 24 * 60 * 60,
        cleanup_interval_seconds: float = 60,
        clock: Clock | None = None,
    ):
        self.histories: Dict[HistoryKey, List[Dict[str, Any]]] = {}
        self.user_settings: Dict[int, Dict[str, Any]] = {}
        self.max_history = max_history
        self.ttl_seconds = ttl_seconds
        self.cleanup_interval_seconds = cleanup_interval_seconds
        self._clock = clock or time.monotonic
        self._history_last_access: Dict[HistoryKey, float] = {}
        self._settings_last_access: Dict[int, float] = {}
        self._last_cleanup = self._clock()

    def get_history(self, chat_id: int, user_id: int) -> List[Dict[str, Any]]:
        now = self._clock()
        self._cleanup_if_due(now)

        key = (chat_id, user_id)
        self._touch_settings(user_id, now)
        history = self.histories.get(key)
        if history is None:
            return []

        self._history_last_access[key] = now
        return history

    def add_message(self, chat_id: int, user_id: int, role: str, content: Any):
        now = self._clock()
        self._cleanup_if_due(now)

        key = (chat_id, user_id)
        history = self.histories.setdefault(key, [])
        history.append({"role": role, "content": content})
        if len(history) > self.max_history:
            history.pop(0)
        self._history_last_access[key] = now
        self._touch_settings(user_id, now)

    def clear_history(self, chat_id: int, user_id: int):
        now = self._clock()
        self._cleanup_if_due(now)

        key = (chat_id, user_id)
        self.histories.pop(key, None)
        self._history_last_access.pop(key, None)
        self._touch_settings(user_id, now)

    def get_setting(self, user_id: int, key: str, default=None):
        now = self._clock()
        self._cleanup_if_due(now)
        self._touch_histories(user_id, now)

        settings = self.user_settings.get(user_id)
        if settings is None:
            return default

        self._settings_last_access[user_id] = now
        return settings.get(key, default)

    def set_setting(self, user_id: int, key: str, value):
        now = self._clock()
        self._cleanup_if_due(now)

        settings = self.user_settings.setdefault(user_id, {})
        settings[key] = value
        self._settings_last_access[user_id] = now
        self._touch_histories(user_id, now)

    def cleanup_expired(self, now: float | None = None) -> int:
        now = self._clock() if now is None else now
        self._last_cleanup = now

        if self.ttl_seconds is None:
            return 0

        expires_at = now - self.ttl_seconds
        removed = 0

        for key, last_access in list(self._history_last_access.items()):
            if last_access <= expires_at:
                self.histories.pop(key, None)
                self._history_last_access.pop(key, None)
                removed += 1

        for user_id, last_access in list(self._settings_last_access.items()):
            if last_access <= expires_at:
                self.user_settings.pop(user_id, None)
                self._settings_last_access.pop(user_id, None)
                removed += 1

        return removed

    def _cleanup_if_due(self, now: float):
        if self.cleanup_interval_seconds <= 0:
            self.cleanup_expired(now)
            return

        if now - self._last_cleanup >= self.cleanup_interval_seconds:
            self.cleanup_expired(now)

    def _touch_settings(self, user_id: int, now: float):
        if user_id in self.user_settings:
            self._settings_last_access[user_id] = now

    def _touch_histories(self, user_id: int, now: float):
        for history_key in self.histories:
            if history_key[1] == user_id:
                self._history_last_access[history_key] = now


storage = MemoryStorage()
