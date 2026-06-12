from typing import Any, Optional

import httpx
import structlog

from bot.services.send_message_draft import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()


class SendChatJoinRequestWebAppError(Exception):
    """Raised when ``sendChatJoinRequestWebApp`` validation or raw call fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


async def perform_send_chat_join_request_web_app(
    bot: Any,
    *,
    chat_join_request_query_id: str,
    web_app_url: str,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> bool:
    """Show a Mini App while processing a Bot API 10.1 join request query."""
    if not chat_join_request_query_id:
        raise SendChatJoinRequestWebAppError("chat_join_request_query_id is required.")
    if not web_app_url.startswith(("http://", "https://")):
        raise SendChatJoinRequestWebAppError("web_app_url must be an HTTP(S) URL.")

    payload = {
        "chat_join_request_query_id": chat_join_request_query_id,
        "web_app_url": web_app_url,
    }
    url = _build_api_url(bot, "sendChatJoinRequestWebApp")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "send_chat_join_request_web_app_failed",
            query_id_length=len(chat_join_request_query_id),
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise SendChatJoinRequestWebAppError(
            f"sendChatJoinRequestWebApp request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "send_chat_join_request_web_app_failed",
            query_id_length=len(chat_join_request_query_id),
            error_code=error_code,
            error=description,
        )
        raise SendChatJoinRequestWebAppError(description, error_code=error_code)

    logger.info(
        "chat_join_request_web_app_sent",
        query_id_length=len(chat_join_request_query_id),
    )
    return data.get("result", True)
