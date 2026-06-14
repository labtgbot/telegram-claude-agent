"""
EXPERIMENT: Streaming with no message_stop / [DONE] terminator.

_stream_response breaks only on:
    data == "[DONE]"  OR  event["type"] == "message_stop"

If the upstream proxy finishes the HTTP body WITHOUT sending either terminator
(e.g. free-claude-code closes the connection after the last delta, or a buggy
proxy forgets the terminal events), what happens?

aiter_lines() will simply end when the body ends, the async-for completes, the
finally closes the response, and the generator returns normally. So the consumer
sees a normal end. That's fine. We confirm this is graceful (no hang, no error),
i.e. the absence of a terminator is tolerated. We also confirm a body that ends
mid-line (no trailing newline) still yields the last event.
"""
import asyncio

import httpx

from bot.services.claude_proxy import ClaudeProxyClient


# Stream that NEVER sends message_stop or [DONE]; it just ends.
NO_TERMINATOR = (
    'data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"A"}}\n'
    '\n'
    'data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"B"}}\n'
    # no blank line, no terminator, body just ends here:
)


def handler(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, headers={"content-type": "text/event-stream"},
                          content=NO_TERMINATOR.encode("utf-8"))


async def main():
    transport = httpx.MockTransport(handler)
    client = ClaudeProxyClient("http://test", "tok")
    client._client = httpx.AsyncClient(transport=transport, timeout=5)

    out = []
    stream = await client.send_message(messages=[{"role": "user", "content": "x"}],
                                       model="m", stream=True)
    try:
        out = [ev async for ev in stream]
    except Exception as exc:
        print("raised:", type(exc).__name__, exc)
    await client.close()

    texts = [e["delta"]["text"] for e in out if e.get("type") == "content_block_delta"]
    print("events:", len(out), "texts:", texts)
    if texts == ["A", "B"]:
        print(">>> RESULT: no-terminator stream ends gracefully; last event NOT lost.")
    else:
        print(f">>> RESULT: unexpected -> {texts}")


if __name__ == "__main__":
    asyncio.run(main())
