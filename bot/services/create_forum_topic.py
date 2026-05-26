from html import escape
from typing import Any, Optional

import httpx
import structlog
from aiogram.types import ForumTopic

logger = structlog.get_logger()

DEFAULT_REQUEST_TIMEOUT = 60.0
FORUM_TOPIC_NAME_LIMIT = 128


class CreateForumTopicError(Exception):
    """Raised when raw ``createForumTopic`` fails."""

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


async def perform_create_forum_topic(
    bot: Any,
    *,
    chat_id: int,
    name: str,
    icon_color: Optional[int] = None,
    icon_custom_emoji_id: Optional[str] = None,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> ForumTopic:
    """Create a forum topic through the raw Telegram Bot API."""
    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "name": name,
    }
    if icon_color is not None:
        payload["icon_color"] = icon_color
    if icon_custom_emoji_id is not None:
        payload["icon_custom_emoji_id"] = icon_custom_emoji_id

    url = _build_api_url(bot, "createForumTopic")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "create_forum_topic_failed",
            chat_id=chat_id,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise CreateForumTopicError(f"createForumTopic request failed: {exc}") from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "create_forum_topic_failed",
            chat_id=chat_id,
            error_code=error_code,
            error=description,
        )
        raise CreateForumTopicError(description, error_code=error_code)

    topic = ForumTopic.model_validate(data.get("result") or {})
    logger.info(
        "forum_topic_created",
        chat_id=chat_id,
        message_thread_id=topic.message_thread_id,
        has_icon_color=icon_color is not None,
        has_icon_custom_emoji_id=icon_custom_emoji_id is not None,
    )
    return topic


def format_create_forum_topic_result(
    *,
    chat_id: int,
    name: str,
    topic: ForumTopic,
    icon_color: Optional[int] = None,
    icon_custom_emoji_id: Optional[str] = None,
) -> str:
    lines = [
        "<b>createForumTopic</b>",
        f"Chat ID: {escape(str(chat_id))}",
        f"Message thread ID: {escape(str(topic.message_thread_id))}",
        f"Name: {escape(name)}",
        "Status: forum topic created.",
    ]
    if icon_color is not None:
        lines.append(f"Icon color: <code>{escape(str(icon_color))}</code>")
    if icon_custom_emoji_id is not None:
        lines.append(
            "Icon custom emoji ID: "
            f"<code>{escape(str(icon_custom_emoji_id))}</code>"
        )
    return "\n".join(lines)
