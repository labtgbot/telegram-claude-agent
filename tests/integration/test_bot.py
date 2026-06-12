"""
Integration tests for the Telegram Claude Agent bot.

These tests require a running free-claude-code proxy and a valid bot token.
Set the following environment variables to run:
  FREE_CLAUDE_BASE_URL, FREE_CLAUDE_AUTH_TOKEN, FREE_CLAUDE_DEFAULT_MODEL,
  TELEGRAM_BOT_TOKEN

Run with:
  INTEGRATION_TEST=1 pytest tests/integration/ -v
"""

import os

import pytest
import httpx

# Integration tests are skipped by default unless explicitly opted in via
# a INTEGRATION_TEST=1 environment variable.

pytestmark = pytest.mark.skipif(
    os.getenv("INTEGRATION_TEST") != "1",
    reason="integration tests require a live proxy; run manually with INTEGRATION_TEST=1",
)


@pytest.mark.asyncio
async def test_proxy_health(test_settings):
    """Verify that the free-claude-code proxy is reachable."""
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(
                f"{test_settings.free_claude_base_url}/v1/models",
                headers={"Authorization": f"Bearer {test_settings.free_claude_auth_token}"},
            )
            assert resp.status_code == 200
        except httpx.ConnectError:
            pytest.skip("free-claude-code proxy not reachable")


@pytest.mark.asyncio
async def test_send_message_end_to_end(test_settings):
    """Send a real message through the proxy and verify a response."""
    from bot.services.claude_proxy import ClaudeProxyClient

    client = ClaudeProxyClient(
        test_settings.free_claude_base_url,
        test_settings.free_claude_auth_token,
        timeout=30,
    )
    try:
        messages = [{"role": "user", "content": [{"type": "text", "text": "Say hello"}]}]
        resp = await client.send_message(
            messages=messages,
            model=test_settings.free_claude_default_model,
            stream=False,
        )
        assert "content" in resp
        text_blocks = [b for b in resp["content"] if b.get("type") == "text"]
        assert text_blocks, "Expected at least one text content block in response"
    finally:
        await client.close()
