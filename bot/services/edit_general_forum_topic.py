from html import escape
from typing import Any, Optional

import httpx
import structlog

logger = structlog.get_logger()

DEFAULT_REQUEST_TIMEOUT = 60.0
GENERAL_FORUM_TOPIC_NAME_LIMIT = 128


class EditGeneralForumTopicError(Exception):
    """Raised when raw ``editGeneralForumTopic`` fails."""

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


async def perform_edit_general_forum_topic(
    bot: Any,
    *,
    chat_id: int,
    name: str,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> bool:
    """Edit the General forum topic through the raw Telegram Bot API."""
    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "name": name,
    }
    url = _build_api_url(bot, "editGeneralForumTopic")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "edit_general_forum_topic_failed",
            chat_id=chat_id,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise EditGeneralForumTopicError(
            f"editGeneralForumTopic request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "edit_general_forum_topic_failed",
            chat_id=chat_id,
            error_code=error_code,
            error=description,
        )
        raise EditGeneralForumTopicError(description, error_code=error_code)

    logger.info(
        "general_forum_topic_edited",
        chat_id=chat_id,
        has_name=bool(name),
    )
    return bool(data.get("result"))


def format_edit_general_forum_topic_result(
    *,
    chat_id: int,
    name: str,
) -> str:
    return "\n".join(
        [
            "<b>editGeneralForumTopic</b>",
            f"Chat ID: {escape(str(chat_id))}",
            f"Name: {escape(name)}",
            "Status: General forum topic updated.",
        ]
    )
