from collections import defaultdict, deque
from typing import List, Dict, Any
import time

class MemoryStorage:
    def __init__(self, max_history: int = 20):
        self.histories: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
        self.user_settings: Dict[int, Dict[str, Any]] = defaultdict(dict)
        self.max_history = max_history

    def get_history(self, user_id: int) -> List[Dict[str, Any]]:
        return self.histories[user_id]

    def add_message(self, user_id: int, role: str, content: Any):
        self.histories[user_id].append({"role": role, "content": content})
        if len(self.histories[user_id]) > self.max_history:
            self.histories[user_id].pop(0)

    def clear_history(self, user_id: int):
        self.histories[user_id].clear()

    def get_setting(self, user_id: int, key: str, default=None):
        return self.user_settings.get(user_id, {}).get(key, default)

    def set_setting(self, user_id: int, key: str, value):
        if user_id not in self.user_settings:
            self.user_settings[user_id] = {}
        self.user_settings[user_id][key] = value

storage = MemoryStorage()