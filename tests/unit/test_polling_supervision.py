import asyncio

import pytest
from fastapi.testclient import TestClient

import bot.main as main


@pytest.fixture(autouse=True)
def reset_polling_state():
    main.polling_state.reset()
    yield
    main.polling_state.reset()


class FailingDispatcher:
    def __init__(self):
        self.calls = 0

    async def start_polling(self, bot, *, skip_updates):
        self.calls += 1
        assert bot is not None
        assert skip_updates is True
        raise RuntimeError(f"polling boom {self.calls}")


async def test_supervised_polling_retries_failed_start_polling_with_backoff():
    dispatcher = FailingDispatcher()
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
            object(),
            sleep=fake_sleep,
            base_delay_seconds=1,
            max_delay_seconds=10,
        )

    assert dispatcher.calls == 2
    assert delays == [1, 2]
    assert [snapshot["status"] for snapshot in snapshots] == ["degraded", "degraded"]
    assert snapshots[0]["last_error"] == "polling boom 1"
    assert snapshots[1]["last_error"] == "polling boom 2"


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
