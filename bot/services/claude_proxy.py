import json
import httpx
from typing import List, Dict, Any, AsyncIterator, Optional, Union

class ClaudeProxyError(Exception):
    pass


_STREAM_DONE = object()


def _format_stream_error(error: Any) -> str:
    if isinstance(error, dict):
        error_type = error.get("type") or "unknown_error"
        message = error.get("message") or "Claude stream returned an error."
        return f"{error_type}: {message}"
    if error:
        return str(error)
    return "Claude stream returned an error."


def _parse_sse_data_event(data_lines: List[str]) -> Optional[Union[Dict[str, Any], object]]:
    if not data_lines:
        return None

    data = "\n".join(data_lines)
    if data == "[DONE]":
        return _STREAM_DONE

    try:
        event = json.loads(data)
    except json.JSONDecodeError:
        return None

    event_type = event.get("type")
    if event_type == "message_stop":
        return _STREAM_DONE
    if event_type == "error":
        raise ClaudeProxyError(_format_stream_error(event.get("error")))
    return event


class ClaudeProxyClient:
    def __init__(self, base_url: str, auth_token: str, timeout: int = 120):
        self.base_url = base_url.rstrip('/')
        self.auth_token = auth_token
        self.timeout = timeout
        self._client = httpx.AsyncClient(timeout=timeout, follow_redirects=True)

    async def close(self):
        await self._client.aclose()

    def _auth_headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.auth_token}",
            "anthropic-version": "2023-06-01",
        }

    async def list_models(self) -> List[str]:
        resp = await self._client.get(f"{self.base_url}/v1/models", headers=self._auth_headers())
        resp.raise_for_status()
        data = resp.json()
        # Handle both Anthropic and OpenAI response formats
        if "models" in data:
            return [m["id"] for m in data["models"]]
        elif "data" in data:
            return [m["id"] for m in data["data"]]
        return []

    async def count_tokens(self, text: str, model: str) -> int:
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": text}],
        }
        resp = await self._client.post(
            f"{self.base_url}/v1/messages/count_tokens",
            json=payload,
            headers=self._auth_headers()
        )
        resp.raise_for_status()
        data = resp.json()
        return data["input_tokens"]

    async def send_message(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        stream: bool = False,
        max_tokens: int = 4096,
        system: Optional[str] = None,
    ) -> Union[ Dict[str, Any], AsyncIterator[Dict[str, Any]] ]:
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "max_tokens": max_tokens,
        }
        if system:
            payload["system"] = system

        if stream:
            request = self._client.build_request(
                "POST",
                f"{self.base_url}/v1/messages",
                json=payload,
                headers=self._auth_headers()
            )
            resp = await self._client.send(request, stream=True)
            try:
                resp.raise_for_status()
            except Exception:
                await resp.aclose()
                raise
            return self._stream_response(resp)
        else:
            resp = await self._client.post(
                f"{self.base_url}/v1/messages",
                json=payload,
                headers=self._auth_headers()
            )
            resp.raise_for_status()
            return resp.json()

    async def _stream_response(self, response: httpx.Response) -> AsyncIterator[Dict[str, Any]]:
        data_lines: List[str] = []
        try:
            async for raw_line in response.aiter_lines():
                line = raw_line.rstrip("\r")
                if line == "":
                    event = _parse_sse_data_event(data_lines)
                    data_lines.clear()
                    if event is _STREAM_DONE:
                        break
                    if event is not None:
                        yield event
                    continue

                if line.startswith(":"):
                    continue

                field_name, separator, value = line.partition(":")
                if separator and value.startswith(" "):
                    value = value[1:]
                if field_name == "data":
                    data_lines.append(value)

            event = _parse_sse_data_event(data_lines)
            if event is not None and event is not _STREAM_DONE:
                yield event
        finally:
            # Always release the underlying HTTP connection, even when the
            # consumer breaks early or raises mid-stream. Otherwise the response
            # stream (and its connection) would leak on a reused/long-lived
            # client. See issue #351.
            await response.aclose()
