from html import escape
from typing import Any, Optional

import httpx
import structlog

logger = structlog.get_logger()

DEFAULT_REQUEST_TIMEOUT = 60.0
FORUM_TOPIC_NAME_LIMIT = 128


class EditForumTopicError(Exception):
    """Raised when raw ``editForumTopic`` fails."""

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


async def perform_edit_forum_topic(
    bot: Any,
    *,
    chat_id: int,
    message_thread_id: int,
    name: Optional[str] = None,
    icon_custom_emoji_id: Optional[str] = None,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> bool:
    """Edit a forum topic through the raw Telegram Bot API."""
    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "message_thread_id": message_thread_id,
    }
    if name is not None:
        payload["name"] = name
    if icon_custom_emoji_id is not None:
        payload["icon_custom_emoji_id"] = icon_custom_emoji_id

    url = _build_api_url(bot, "editForumTopic")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "edit_forum_topic_failed",
            chat_id=chat_id,
            message_thread_id=message_thread_id,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise EditForumTopicError(f"editForumTopic request failed: {exc}") from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "edit_forum_topic_failed",
            chat_id=chat_id,
            message_thread_id=message_thread_id,
            error_code=error_code,
            error=description,
        )
        raise EditForumTopicError(description, error_code=error_code)

    logger.info(
        "forum_topic_edited",
        chat_id=chat_id,
        message_thread_id=message_thread_id,
        has_name=name is not None,
        has_icon_custom_emoji_id=icon_custom_emoji_id is not None,
    )
    return bool(data.get("result"))


def format_edit_forum_topic_result(
    *,
    chat_id: int,
    message_thread_id: int,
    name: Optional[str],
    icon_custom_emoji_id: Optional[str],
) -> str:
    lines = [
        "<b>editForumTopic</b>",
        f"Chat ID: {escape(str(chat_id))}",
        f"Message thread ID: {escape(str(message_thread_id))}",
        "Status: forum topic updated.",
    ]
    if name is not None:
        lines.append(f"Name: {escape(name)}")
    if icon_custom_emoji_id is not None:
        lines.append(
            "Icon custom emoji ID: "
            f"<code>{escape(str(icon_custom_emoji_id))}</code>"
        )
    return "\n".join(lines)
