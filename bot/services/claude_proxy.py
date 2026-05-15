import json
import httpx
from typing import List, Dict, Any, AsyncIterator, Optional

class ClaudeProxyError(Exception):
    pass

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

    async def count_tokens(self, text: str, model: Optional[str] = None) -> int:
        payload = {"prompt": text}
        if model:
            payload["model"] = model
        resp = await self._client.post(
            f"{self.base_url}/v1/messages/count_tokens",
            json=payload,
            headers=self._auth_headers()
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("input_tokens", data.get("usage", {}).get("input_tokens", 0))

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
            resp = await self._client.post(
                f"{self.base_url}/v1/messages",
                json=payload,
                headers=self._auth_headers()
            )
            resp.raise_for_status()
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
        async for line in response.aiter_lines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("data: "):
                data = line[6:]
                if data == "[DONE]":
                    break
                try:
                    yield json.loads(data)
                except json.JSONDecodeError:
                    continue