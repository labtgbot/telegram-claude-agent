from html import escape
from typing import Any, Optional

import httpx
import structlog

logger = structlog.get_logger()

DEFAULT_REQUEST_TIMEOUT = 60.0


class CloseGeneralForumTopicError(Exception):
    """Raised when raw ``closeGeneralForumTopic`` fails."""

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


async def perform_close_general_forum_topic(
    bot: Any,
    *,
    chat_id: int,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> bool:
    """Close the General forum topic through the raw Telegram Bot API."""
    payload: dict[str, Any] = {"chat_id": chat_id}
    url = _build_api_url(bot, "closeGeneralForumTopic")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "close_general_forum_topic_failed",
            chat_id=chat_id,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise CloseGeneralForumTopicError(
            f"closeGeneralForumTopic request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "close_general_forum_topic_failed",
            chat_id=chat_id,
            error_code=error_code,
            error=description,
        )
        raise CloseGeneralForumTopicError(description, error_code=error_code)

    logger.info("general_forum_topic_closed", chat_id=chat_id)
    return bool(data.get("result"))


def format_close_general_forum_topic_result(*, chat_id: int) -> str:
    return "\n".join(
        [
            "<b>closeGeneralForumTopic</b>",
            f"Chat ID: {escape(str(chat_id))}",
            "Status: General forum topic closed.",
        ]
    )
