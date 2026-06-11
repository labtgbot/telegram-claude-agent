from bot.utils.storage import MemoryStorage


def test_add_and_get_history():
    storage = MemoryStorage()
    chat_id = 100
    user_id = 1
    storage.add_message(chat_id, user_id, "user", "Hello")
    storage.add_message(chat_id, user_id, "assistant", "Hi there")
    history = storage.get_history(chat_id, user_id)
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "Hello"
    assert history[1]["role"] == "assistant"


def test_clear_history():
    storage = MemoryStorage()
    chat_id = 100
    user_id = 2
    storage.add_message(chat_id, user_id, "user", "Test")
    storage.clear_history(chat_id, user_id)
    assert len(storage.get_history(chat_id, user_id)) == 0
    assert (chat_id, user_id) not in storage.histories


def test_max_history_trims_oldest():
    storage = MemoryStorage(max_history=3)
    chat_id = 100
    user_id = 3
    storage.add_message(chat_id, user_id, "user", "1")
    storage.add_message(chat_id, user_id, "assistant", "2")
    storage.add_message(chat_id, user_id, "user", "3")
    storage.add_message(chat_id, user_id, "assistant", "4")
    history = storage.get_history(chat_id, user_id)
    assert len(history) == 3
    assert history[0]["content"] == "2"
    assert history[-1]["content"] == "4"


def test_history_is_isolated_per_chat():
    storage = MemoryStorage()
    user_id = 5
    storage.add_message(10, user_id, "user", "in chat A")
    storage.add_message(20, user_id, "user", "in chat B")

    assert len(storage.get_history(10, user_id)) == 1
    assert len(storage.get_history(20, user_id)) == 1
    assert storage.get_history(10, user_id)[0]["content"] == "in chat A"
    assert storage.get_history(20, user_id)[0]["content"] == "in chat B"


def test_user_settings():
    storage = MemoryStorage()
    user_id = 4
    storage.set_setting(user_id, "model", "claude-3-opus")
    assert storage.get_setting(user_id, "model") == "claude-3-opus"
    assert storage.get_setting(user_id, "missing", default="default") == "default"


def test_get_history_does_not_create_empty_entries():
    storage = MemoryStorage()

    assert storage.get_history(999, 42) == []
    assert storage.histories == {}


def test_cleanup_expired_removes_idle_history_and_settings():
    now = 1_000.0

    def clock():
        return now

    storage = MemoryStorage(ttl_seconds=10, cleanup_interval_seconds=999, clock=clock)
    storage.add_message(100, 1, "user", "old")
    storage.set_setting(1, "model", "claude-3-opus")
    storage.add_message(200, 2, "user", "old too")

    assert len(storage.histories) == 2
    assert len(storage.user_settings) == 1

    now += 11
    removed = storage.cleanup_expired()

    assert removed == 3
    assert storage.histories == {}
    assert storage.user_settings == {}
