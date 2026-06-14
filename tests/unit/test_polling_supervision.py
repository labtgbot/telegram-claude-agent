import asyncio

import pytest
from fastapi.testclient import TestClient

import bot.main as main


@pytest.fixture(autouse=True)
def reset_polling_state():
    main.polling_state.reset()
    main.polling_shutdown_requested = False
    yield
    main.polling_state.reset()
    main.polling_shutdown_requested = False


class FailingDispatcher:
    def __init__(self):
        self.calls = 0
        self.handle_signals = []
        self.start_polling_kwargs = []

    async def start_polling(self, bot, **kwargs):
        self.calls += 1
        self.start_polling_kwargs.append(kwargs)
        self.handle_signals.append(kwargs["handle_signals"])
        assert bot is not None
        assert "skip_updates" not in kwargs
        assert kwargs == {"handle_signals": False}
        raise RuntimeError(f"polling boom {self.calls}")


class RecordingBot:
    def __init__(self):
        self.drop_pending_updates = []

    async def delete_webhook(self, *, drop_pending_updates):
        self.drop_pending_updates.append(drop_pending_updates)
        return True


async def test_supervised_polling_retries_failed_start_polling_with_backoff():
    dispatcher = FailingDispatcher()
    bot = RecordingBot()
    delays = []
    snapshots = []

    async def fake_sleep(delay):
        delays.append(delay)
        snapshots.append(main.polling_state.snapshot())
        if len(delays) == 2:
            raise asyncio.CancelledError

    with pytest.raises(asyncio.CancelledError):
        await main._run_supervised_polling(
            dispatcher,
            bot,
            sleep=fake_sleep,
            base_delay_seconds=1,
            max_delay_seconds=10,
        )

    assert dispatcher.calls == 2
    assert dispatcher.handle_signals == [False, False]
    assert dispatcher.start_polling_kwargs == [
        {"handle_signals": False},
        {"handle_signals": False},
    ]
    assert bot.drop_pending_updates == [True, True]
    assert delays == [1, 2]
    assert [snapshot["status"] for snapshot in snapshots] == ["degraded", "degraded"]
    assert snapshots[0]["last_error"] == "polling boom 1"
    assert snapshots[1]["last_error"] == "polling boom 2"


async def test_supervised_polling_stops_when_start_polling_returns_during_shutdown():
    class ReturningDispatcher:
        def __init__(self):
            self.calls = 0
            self.start_polling_kwargs = []

        async def start_polling(self, bot, **kwargs):
            self.calls += 1
            self.start_polling_kwargs.append(kwargs)
            assert bot is not None
            assert "skip_updates" not in kwargs
            assert kwargs == {"handle_signals": False}

    async def unexpected_sleep(delay):
        raise AssertionError(f"supervisor retried after shutdown with delay {delay}")

    dispatcher = ReturningDispatcher()
    bot = RecordingBot()

    await main._run_supervised_polling(
        dispatcher,
        bot,
        sleep=unexpected_sleep,
        shutdown_requested=lambda: True,
    )

    assert dispatcher.calls == 1
    assert dispatcher.start_polling_kwargs == [{"handle_signals": False}]
    assert bot.drop_pending_updates == [True]
    assert main.polling_state.snapshot()["status"] == "stopped"


async def test_supervised_polling_retries_unexpected_clean_start_polling_return():
    class ReturningDispatcher:
        def __init__(self):
            self.calls = 0
            self.start_polling_kwargs = []

        async def start_polling(self, bot, **kwargs):
            self.calls += 1
            self.start_polling_kwargs.append(kwargs)
            assert bot is not None
            assert "skip_updates" not in kwargs
            assert kwargs == {"handle_signals": False}

    delays = []
    snapshots = []
    dispatcher = ReturningDispatcher()
    bot = RecordingBot()

    async def fake_sleep(delay):
        delays.append(delay)
        snapshots.append(main.polling_state.snapshot())
        if len(delays) == 2:
            raise asyncio.CancelledError

    with pytest.raises(asyncio.CancelledError):
        await main._run_supervised_polling(
            dispatcher,
            bot,
            sleep=fake_sleep,
            base_delay_seconds=1,
            max_delay_seconds=10,
            shutdown_requested=lambda: False,
        )

    assert dispatcher.calls == 2
    assert dispatcher.start_polling_kwargs == [
        {"handle_signals": False},
        {"handle_signals": False},
    ]
    assert bot.drop_pending_updates == [True, True]
    assert delays == [1, 2]
    assert [snapshot["status"] for snapshot in snapshots] == ["degraded", "degraded"]
    assert snapshots[0]["last_error"] == "start_polling returned unexpectedly"
    assert snapshots[1]["last_error"] == "start_polling returned unexpectedly"


def test_health_returns_503_when_polling_is_degraded():
    main.polling_state.mark_degraded("polling boom", retry_delay_seconds=1)
    client = TestClient(main.app, raise_server_exceptions=False)

    response = client.get("/health")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["polling"]["status"] == "degraded"
    assert body["polling"]["last_error"] == "polling boom"
    assert body["polling"]["retry_delay_seconds"] == 1


def test_health_returns_200_when_polling_is_running():
    main.polling_state.mark_running()
    client = TestClient(main.app, raise_server_exceptions=False)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["polling"]["status"] == "running"


async def test_get_me_failure_is_reported_as_clear_startup_error():
    class BrokenBot:
        async def get_me(self):
            raise RuntimeError("invalid token")

    with pytest.raises(RuntimeError, match="Failed to validate Telegram bot token"):
        await main._ensure_bot_identity_cached(BrokenBot())
