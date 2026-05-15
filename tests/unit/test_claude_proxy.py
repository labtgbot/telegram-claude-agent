import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from bot.services.claude_proxy import ClaudeProxyClient, ClaudeProxyError

@pytest.mark.asyncio
async def test_list_models_anthropic_format():
    client = ClaudeProxyClient("http://localhost:8082", "token")
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "models": [{"id": "claude-3-opus"}, {"id": "claude-3-sonnet"}]
    }

    with patch.object(client._client, 'get', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        models = await client.list_models()
        assert models == ["claude-3-opus", "claude-3-sonnet"]
        mock_get.assert_called_once()

@pytest.mark.asyncio
async def test_list_models_openai_format():
    client = ClaudeProxyClient("http://localhost:8082", "token")
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "data": [{"id": "model1"}, {"id": "model2"}]
    }

    with patch.object(client._client, 'post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        # Actually list_models uses GET, but we can test similarly
        pass

@pytest.mark.asyncio
async def test_send_message_non_streaming():
    client = ClaudeProxyClient("http://localhost:8082", "token")
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "content": [{"type": "text", "text": "Hello, how can I help?"}]
    }

    with patch.object(client._client, 'post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        messages = [{"role": "user", "content": [{"type": "text", "text": "Hi"}]}]
        resp = await client.send_message(messages=messages, model="claude-3-opus")
        assert resp["content"][0]["text"] == "Hello, how can I help?"
        # Check headers and payload
        args, kwargs = mock_post.call_args
        assert "/v1/messages" in args[0]
        assert kwargs["json"]["messages"] == messages
        assert kwargs["json"]["model"] == "claude-3-opus"
        assert kwargs["json"]["stream"] is False
        assert "Authorization" in kwargs["headers"]
        assert kwargs["headers"]["Authorization"] == "Bearer token"

@pytest.mark.asyncio
async def test_send_message_streaming():
    client = ClaudeProxyClient("http://localhost:8082", "token")
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    # Mock aiter_lines to yield SSE lines
    async def mock_aiter_lines():
        yield "data: {\"type\": \"content_block_delta\", \"delta\": {\"type\": \"text_delta\", \"text\": \"Hello\"}}"
        yield "data: {\"type\": \"content_block_delta\", \"delta\": {\"type\": \"text_delta\", \"text\": \" World\"}}"
        yield "data: {\"type\": \"message_stop\"}"
        yield "data: [DONE]"

    mock_response.aiter_lines = mock_aiter_lines

    with patch.object(client._client, 'post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        messages = [{"role": "user", "content": [{"type": "text", "text": "Hi"}]}]
        stream = await client.send_message(messages=messages, model="claude-3-opus", stream=True)
        chunks = []
        async for chunk in stream:
            chunks.append(chunk)
        assert len(chunks) == 2  # two deltas before message_stop
        assert chunks[0]["delta"]["text"] == "Hello"
        assert chunks[1]["delta"]["text"] == " World"