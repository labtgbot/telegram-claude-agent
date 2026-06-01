"""Tests for webhook secret token authentication on the /webhook endpoint."""

import pytest
from fastapi.testclient import TestClient

import bot.main as main


@pytest.fixture
def client():
    return TestClient(main.app, raise_server_exceptions=False)


def test_webhook_rejects_missing_header(client, monkeypatch):
    monkeypatch.setattr(main.settings, "api_secret_token", "a-Strong_Secret_123456")
    resp = client.post("/webhook", json={"update_id": 1})
    assert resp.status_code == 403


def test_webhook_rejects_invalid_token(client, monkeypatch):
    monkeypatch.setattr(main.settings, "api_secret_token", "a-Strong_Secret_123456")
    resp = client.post(
        "/webhook",
        json={"update_id": 1},
        headers={"X-Telegram-Bot-Api-Secret-Token": "wrong-token"},
    )
    assert resp.status_code == 403


def test_webhook_rejects_when_token_not_configured(client, monkeypatch):
    # Even without a configured token the endpoint must not feed updates.
    monkeypatch.setattr(main.settings, "api_secret_token", None)
    resp = client.post(
        "/webhook",
        json={"update_id": 1},
        headers={"X-Telegram-Bot-Api-Secret-Token": "anything"},
    )
    assert resp.status_code == 403


def test_webhook_accepts_valid_token(client, monkeypatch):
    token = "a-Strong_Secret_123456"
    monkeypatch.setattr(main.settings, "api_secret_token", token)

    fed = {}

    async def fake_feed_update(bot, update):
        fed["update"] = update

    monkeypatch.setattr(main.dp, "feed_update", fake_feed_update)

    resp = client.post(
        "/webhook",
        json={"update_id": 1},
        headers={"X-Telegram-Bot-Api-Secret-Token": token},
    )
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    assert fed["update"].update_id == 1
