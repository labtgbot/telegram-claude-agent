"""
EXPERIMENT: SSE parser robustness for two spec-legal framings:

1. Multi-line `data:` fields. Per the SSE spec (WHATWG/W3C), an event may have
   multiple `data:` lines which the client MUST concatenate with "\n" before
   dispatch. JSON pretty-printed by some proxies arrives this way:
       data: {
       data:   "type": "content_block_delta",
       data:   ...
       data: }
   The current parser calls json.loads() on EACH `data:` line independently,
   so each partial line fails json.loads and is silently `continue`d.

2. `data:` without the trailing space ("data:{...}" instead of "data: {...}").
   The spec says exactly ONE leading space after the colon is stripped, but a
   compliant server may also send `data:` with no space at all. The parser only
   matches the literal prefix "data: " (with a space) via `line.startswith`.

We feed both framings through the real _stream_response and observe how many
events survive.
"""
import asyncio

import httpx

from bot.services.claude_proxy import ClaudeProxyClient


# Case 1: a single logical event split across multiple `data:` lines (valid SSE).
MULTILINE_BODY = (
    'data: {\n'
    'data: "type": "content_block_delta",\n'
    'data: "index": 0,\n'
    'data: "delta": {"type": "text_delta", "text": "Hi"}\n'
    'data: }\n'
    '\n'
)

# Case 2: data lines with NO space after the colon (also valid SSE).
NOSPACE_BODY = (
    'data:{"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Hi"}}\n'
    '\n'
)


def make_handler(body: str):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            content=body.encode("utf-8"),
        )
    return handler


async def collect(body: str):
    transport = httpx.MockTransport(make_handler(body))
    client = ClaudeProxyClient("http://test", "tok")
    client._client = httpx.AsyncClient(transport=transport, timeout=10)
    out = []
    stream = await client.send_message(
        messages=[{"role": "user", "content": "hi"}], model="m", stream=True
    )
    async for ev in stream:
        out.append(ev)
    await client.close()
    return out


async def main():
    print("=== Case 1: multi-line data: (valid SSE, must concat with \\n) ===")
    ml = await collect(MULTILINE_BODY)
    print(f"events parsed: {len(ml)} -> {ml}")
    if not ml:
        print(">>> RESULT: valid multi-line SSE event is COMPLETELY LOST")
        print(">>>         (each `data:` line json.loads-fails and is dropped).")
    print()

    print("=== Case 2: data: with no space after colon (valid SSE) ===")
    ns = await collect(NOSPACE_BODY)
    print(f"events parsed: {len(ns)} -> {ns}")
    if not ns:
        print(">>> RESULT: a 'data:{...}' line (no space) is NOT recognized at all")
        print(">>>         because the parser only matches the literal 'data: ' prefix.")


if __name__ == "__main__":
    asyncio.run(main())
