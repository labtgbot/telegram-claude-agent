import asyncio
import json
from contextlib import aclosing
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
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

    with patch.object(client._client, 'get', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        models = await client.list_models()

        assert models == ["model1", "model2"]
        mock_get.assert_awaited_once_with(
            "http://localhost:8082/v1/models",
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer token",
                "anthropic-version": "2023-06-01",
            },
        )

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
async def test_count_tokens_uses_messages_api_payload():
    client = ClaudeProxyClient("http://localhost:8082", "token")
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"input_tokens": 7}

    with patch.object(client._client, 'post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        token_count = await client.count_tokens("Hi", model="claude-3-opus")

        assert token_count == 7
        args, kwargs = mock_post.call_args
        assert args[0] == "http://localhost:8082/v1/messages/count_tokens"
        assert kwargs["json"] == {
            "model": "claude-3-opus",
            "messages": [{"role": "user", "content": "Hi"}],
        }
        assert kwargs["headers"]["Authorization"] == "Bearer token"


@pytest.mark.asyncio
async def test_send_message_streaming():
    client = ClaudeProxyClient("http://localhost:8082", "token")
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.aclose = AsyncMock()
    # Mock aiter_lines to yield SSE lines
    async def mock_aiter_lines():
        yield "data: {\"type\": \"content_block_delta\", \"delta\": {\"type\": \"text_delta\", \"text\": \"Hello\"}}"
        yield ""
        yield "data: {\"type\": \"content_block_delta\", \"delta\": {\"type\": \"text_delta\", \"text\": \" World\"}}"
        yield ""
        yield "data: {\"type\": \"message_stop\"}"
        yield ""
        yield "data: [DONE]"
        yield ""

    mock_response.aiter_lines = mock_aiter_lines

    with patch.object(client._client, "send", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = mock_response
        messages = [{"role": "user", "content": [{"type": "text", "text": "Hi"}]}]
        stream = await client.send_message(messages=messages, model="claude-3-opus", stream=True)
        args, kwargs = mock_send.call_args
        request = args[0]
        payload = json.loads(request.content.decode())
        assert request.method == "POST"
        assert str(request.url) == "http://localhost:8082/v1/messages"
        assert payload["messages"] == messages
        assert payload["model"] == "claude-3-opus"
        assert payload["stream"] is True
        assert request.headers["Authorization"] == "Bearer token"
        assert kwargs["stream"] is True
        chunks = []
        async for chunk in stream:
            chunks.append(chunk)
        assert len(chunks) == 2  # two deltas before message_stop
        assert chunks[0]["delta"]["text"] == "Hello"
        assert chunks[1]["delta"]["text"] == " World"


async def _collect_streaming_body(body: str):
    async def handler(_request):
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            content=body.encode("utf-8"),
        )

    transport = httpx.MockTransport(handler)
    client = ClaudeProxyClient("http://localhost:8082", "token")
    await client.close()
    client._client = httpx.AsyncClient(transport=transport, timeout=1, follow_redirects=True)

    try:
        stream = await client.send_message(
            messages=[{"role": "user", "content": [{"type": "text", "text": "Hi"}]}],
            model="m",
            stream=True,
        )
        return [chunk async for chunk in stream]
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_send_message_streaming_accepts_data_without_space_after_colon():
    chunks = await _collect_streaming_body(
        'data:{"type":"content_block_delta","index":0,'
        '"delta":{"type":"text_delta","text":"Hi"}}\n'
        "\n"
        "data:[DONE]\n"
        "\n"
    )

    assert chunks == [
        {
            "type": "content_block_delta",
            "index": 0,
            "delta": {"type": "text_delta", "text": "Hi"},
        }
    ]


@pytest.mark.asyncio
async def test_send_message_streaming_concatenates_multiline_data_event():
    chunks = await _collect_streaming_body(
        "data: {\n"
        'data:   "type": "content_block_delta",\n'
        'data:   "index": 0,\n'
        'data:   "delta": {"type": "text_delta", "text": "Hi"}\n'
        "data: }\n"
        "\n"
        "data: [DONE]\n"
        "\n"
    )

    assert chunks == [
        {
            "type": "content_block_delta",
            "index": 0,
            "delta": {"type": "text_delta", "text": "Hi"},
        }
    ]


@pytest.mark.asyncio
async def test_send_message_streaming_raises_on_anthropic_error_event():
    client = ClaudeProxyClient("http://localhost:8082", "token")
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.aclose = AsyncMock()

    async def mock_aiter_lines():
        yield (
            'data: {"type": "content_block_delta", '
            '"delta": {"type": "text_delta", "text": "Hello"}}'
        )
        yield ""
        yield (
            'data: {"type": "error", '
            '"error": {"type": "overloaded_error", "message": "Overloaded"}}'
        )
        yield ""
        yield "data: {\"type\": \"message_stop\"}"
        yield ""

    mock_response.aiter_lines = mock_aiter_lines

    with patch.object(client._client, "send", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = mock_response
        messages = [{"role": "user", "content": [{"type": "text", "text": "Hi"}]}]
        stream = await client.send_message(messages=messages, model="m", stream=True)
        chunks = []

        with pytest.raises(ClaudeProxyError, match="overloaded_error: Overloaded"):
            async for chunk in stream:
                chunks.append(chunk)

        assert chunks == [
            {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "Hello"}}
        ]
        mock_response.aclose.assert_awaited_once()


class _BlockingSSEStream(httpx.AsyncByteStream):
    def __init__(self):
        self.iteration_started = asyncio.Event()
        self.release_remaining = asyncio.Event()
        self.closed = False

    async def __aiter__(self):
        self.iteration_started.set()
        yield (
            b'data: {"type": "content_block_delta", '
            b'"delta": {"type": "text_delta", "text": "Hello"}}\n\n'
        )
        await self.release_remaining.wait()
        yield b'data: {"type": "message_stop"}\n\n'

    async def aclose(self):
        self.closed = True


@pytest.mark.asyncio
async def test_send_message_streaming_returns_before_sse_body_completes():
    slow_stream = _BlockingSSEStream()

    async def handler(_request):
        return httpx.Response(200, stream=slow_stream)

    transport = httpx.MockTransport(handler)
    client = ClaudeProxyClient("http://localhost:8082", "token")
    await client.close()
    client._client = httpx.AsyncClient(transport=transport, timeout=1, follow_redirects=True)

    send_task = asyncio.create_task(
        client.send_message(
            messages=[{"role": "user", "content": [{"type": "text", "text": "Hi"}]}],
            model="m",
            stream=True,
        )
    )
    body_iteration_task = asyncio.create_task(slow_stream.iteration_started.wait())

    try:
        done, _pending = await asyncio.wait(
            {send_task, body_iteration_task},
            timeout=1,
            return_when=asyncio.FIRST_COMPLETED,
        )

        assert send_task in done
        assert body_iteration_task not in done

        stream = send_task.result()
        chunks = []
        async for chunk in stream:
            chunks.append(chunk)
            slow_stream.release_remaining.set()

        assert chunks[0]["delta"]["text"] == "Hello"
        assert slow_stream.closed is True
    finally:
        slow_stream.release_remaining.set()
        for task in (send_task, body_iteration_task):
            if not task.done():
                task.cancel()
        await asyncio.gather(send_task, body_iteration_task, return_exceptions=True)
        await client.close()


def _streaming_response_mock():
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.aclose = AsyncMock()

    async def mock_aiter_lines():
        yield "data: {\"type\": \"content_block_delta\", \"delta\": {\"type\": \"text_delta\", \"text\": \"Hello\"}}"
        yield ""
        yield "data: {\"type\": \"content_block_delta\", \"delta\": {\"type\": \"text_delta\", \"text\": \" World\"}}"
        yield ""
        yield "data: {\"type\": \"message_stop\"}"
        yield ""
        yield "data: [DONE]"
        yield ""

    mock_response.aiter_lines = mock_aiter_lines
    return mock_response


@pytest.mark.asyncio
async def test_streaming_closes_response_on_completion():
    client = ClaudeProxyClient("http://localhost:8082", "token")
    mock_response = _streaming_response_mock()

    with patch.object(client._client, "send", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = mock_response
        messages = [{"role": "user", "content": [{"type": "text", "text": "Hi"}]}]
        stream = await client.send_message(messages=messages, model="m", stream=True)
        async for _ in stream:
            pass
        mock_response.aclose.assert_awaited_once()


@pytest.mark.asyncio
async def test_streaming_closes_response_on_status_error():
    client = ClaudeProxyClient("http://localhost:8082", "token")
    request = httpx.Request("POST", "http://localhost:8082/v1/messages")
    error = httpx.HTTPStatusError(
        "proxy failed",
        request=request,
        response=httpx.Response(502, request=request),
    )
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = error
    mock_response.aclose = AsyncMock()

    with patch.object(client._client, "send", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = mock_response
        messages = [{"role": "user", "content": [{"type": "text", "text": "Hi"}]}]
        with pytest.raises(httpx.HTTPStatusError):
            await client.send_message(messages=messages, model="m", stream=True)

        mock_response.aclose.assert_awaited_once()


@pytest.mark.asyncio
async def test_streaming_closes_response_on_explicit_aclose():
    client = ClaudeProxyClient("http://localhost:8082", "token")
    mock_response = _streaming_response_mock()

    with patch.object(client._client, "send", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = mock_response
        messages = [{"role": "user", "content": [{"type": "text", "text": "Hi"}]}]
        stream = await client.send_message(messages=messages, model="m", stream=True)
        async for _ in stream:
            break  # abandon the stream after the first event
        # Closing the generator triggers its finally block.
        await stream.aclose()
        mock_response.aclose.assert_awaited_once()


@pytest.mark.asyncio
async def test_streaming_closes_response_on_early_break_with_aclosing():
    client = ClaudeProxyClient("http://localhost:8082", "token")
    mock_response = _streaming_response_mock()

    with patch.object(client._client, "send", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = mock_response
        messages = [{"role": "user", "content": [{"type": "text", "text": "Hi"}]}]
        stream = await client.send_message(messages=messages, model="m", stream=True)
        # Mirrors the handler which wraps the stream in ``contextlib.aclosing``.
        async with aclosing(stream) as events:
            async for _ in events:
                break  # abandon the stream after the first event
        mock_response.aclose.assert_awaited_once()


@pytest.mark.asyncio
async def test_streaming_closes_response_on_consumer_exception():
    client = ClaudeProxyClient("http://localhost:8082", "token")
    mock_response = _streaming_response_mock()

    with patch.object(client._client, "send", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = mock_response
        messages = [{"role": "user", "content": [{"type": "text", "text": "Hi"}]}]
        stream = await client.send_message(messages=messages, model="m", stream=True)
        # Mirrors the handler which wraps the stream in ``contextlib.aclosing``;
        # the consumer raising mid-stream must still release the response.
        with pytest.raises(RuntimeError):
            async with aclosing(stream) as events:
                async for _ in events:
                    raise RuntimeError("consumer blew up")
        mock_response.aclose.assert_awaited_once()
