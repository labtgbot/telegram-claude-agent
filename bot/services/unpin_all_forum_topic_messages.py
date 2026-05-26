from html import escape
from typing import Any, Optional

import httpx
import structlog

logger = structlog.get_logger()

DEFAULT_REQUEST_TIMEOUT = 60.0


class UnpinAllForumTopicMessagesError(Exception):
    """Raised when raw ``unpinAllForumTopicMessages`` fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


def _build_api_url(bot: Any, method: str) -> str:
    session = getattr(bot, "session", None)
    api = getattr(session, "api", None)
    api_url = getattr(api, "api_url", None)
    if callable(api_url):
        return api_url(token=bot.token, method=method)
    return f"https://api.telegram.org/bot{bot.token}/{method}"


async def perform_unpin_all_forum_topic_messages(
    bot: Any,
    *,
    chat_id: int,
    message_thread_id: int,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> bool:
    """Unpin all messages in a forum topic through the raw Telegram Bot API."""
    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "message_thread_id": message_thread_id,
    }
    url = _build_api_url(bot, "unpinAllForumTopicMessages")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "unpin_all_forum_topic_messages_failed",
            chat_id=chat_id,
            message_thread_id=message_thread_id,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise UnpinAllForumTopicMessagesError(
            f"unpinAllForumTopicMessages request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "unpin_all_forum_topic_messages_failed",
            chat_id=chat_id,
            message_thread_id=message_thread_id,
            error_code=error_code,
            error=description,
        )
        raise UnpinAllForumTopicMessagesError(description, error_code=error_code)

    logger.info(
        "forum_topic_messages_unpinned",
        chat_id=chat_id,
        message_thread_id=message_thread_id,
    )
    return bool(data.get("result"))


def format_unpin_all_forum_topic_messages_result(
    *,
    chat_id: int,
    message_thread_id: int,
) -> str:
    return "\n".join(
        [
            "<b>unpinAllForumTopicMessages</b>",
            f"Chat ID: {escape(str(chat_id))}",
            f"Message thread ID: {escape(str(message_thread_id))}",
            "Status: all pinned forum topic messages unpinned.",
        ]
    )
