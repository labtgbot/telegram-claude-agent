"""
EXPERIMENT: Does the SSE parser surface Anthropic mid-stream `error` events?

Anthropic Messages streaming API can emit an `error` event mid-stream, e.g.
when an overloaded_error or rate-limit happens after `message_start`:

    event: error
    data: {"type":"error","error":{"type":"overloaded_error","message":"Overloaded"}}

The HTTP status is 200 (the error happens during the stream), so
`raise_for_status()` does NOT catch it. We test what `_stream_response`
does with such an event and how `handle_streaming` / `handle_streaming_with_draft`
behave: does the user get an error, or a silent empty/partial reply?
"""
import asyncio
import json

import httpx

from bot.services.claude_proxy import ClaudeProxyClient


# Simulated Anthropic SSE stream: a couple of text deltas, then a mid-stream
# `error` event (HTTP 200, error inside the body), then nothing.
SSE_BODY = (
    'event: message_start\n'
    'data: {"type":"message_start","message":{"id":"msg_1","role":"assistant","content":[]}}\n'
    '\n'
    'event: content_block_start\n'
    'data: {"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}\n'
    '\n'
    'event: content_block_delta\n'
    'data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Hello"}}\n'
    '\n'
    'event: error\n'
    'data: {"type":"error","error":{"type":"overloaded_error","message":"Overloaded"}}\n'
    '\n'
)


def handler(request: httpx.Request) -> httpx.Response:
    # Return HTTP 200 with an SSE stream that ends in an error event.
    return httpx.Response(
        200,
        headers={"content-type": "text/event-stream"},
        content=SSE_BODY.encode("utf-8"),
    )


async def main():
    transport = httpx.MockTransport(handler)
    client = ClaudeProxyClient("http://test", "tok")
    # Inject the mock transport into the underlying client.
    client._client = httpx.AsyncClient(transport=transport, timeout=10)

    events = []
    stream = await client.send_message(
        messages=[{"role": "user", "content": "hi"}],
        model="claude-x",
        stream=True,
    )
    async for ev in stream:
        events.append(ev)

    await client.close()

    print("=== Events yielded by _stream_response ===")
    for e in events:
        print(json.dumps(e))

    error_events = [e for e in events if e.get("type") == "error"]
    text_deltas = [
        e for e in events
        if e.get("type") == "content_block_delta"
        and e.get("delta", {}).get("type") == "text_delta"
    ]

    print()
    print(f"text deltas yielded: {len(text_deltas)}")
    print(f"error events yielded to consumer: {len(error_events)}")

    # Now simulate what handle_streaming does: it only looks at
    # content_block_delta/text_delta and IGNORES everything else, including
    # error events. So the reply would just be the partial "Hello" with NO
    # indication that the model failed mid-stream.
    full_text = ""
    saw_error = False
    for ev in events:
        if ev.get("type") == "error":
            saw_error = True
        if ev.get("type") != "content_block_delta":
            continue
        delta = ev.get("delta", {})
        if delta.get("type") != "text_delta":
            continue
        full_text += delta.get("text", "")

    print()
    print(f"handle_streaming would produce reply_text = {full_text!r}")
    print(f"handle_streaming detects the error event? {saw_error and 'logic exists' or 'NO - error silently dropped'}")
    print()
    if error_events:
        print(">>> RESULT: error event IS yielded to consumer, but handle_streaming/")
        print(">>>         handle_streaming_with_draft only inspect text_delta and")
        print(">>>         therefore SILENTLY DROP the mid-stream error, returning a")
        print(">>>         truncated partial answer as if it were complete.")
    else:
        print(">>> RESULT: error event NOT yielded at all.")


if __name__ == "__main__":
    asyncio.run(main())
