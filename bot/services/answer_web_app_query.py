import json
from typing import Any, Optional

import httpx
import structlog

from bot.services.send_paid_media import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()


class AnswerWebAppQueryError(Exception):
    """Raised when the raw ``answerWebAppQuery`` Bot API call fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


async def perform_answer_web_app_query(
    bot: Any,
    *,
    web_app_query_id: str,
    result: dict[str, Any],
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> dict:
    """Answer a Telegram Web App query via a raw Telegram Bot API call.

    ``answerWebAppQuery`` sets the result of a Web App interaction and sends the
    supplied ``InlineQueryResult`` on behalf of the user to the chat where the
    query originated. The pinned ``aiogram==3.3.0`` predates this method, so the
    helper posts directly to the Bot API endpoint and returns the
    ``SentWebAppMessage`` result dict.
    """
    if not web_app_query_id:
        raise AnswerWebAppQueryError("web_app_query_id is required")
    if not result:
        raise AnswerWebAppQueryError("result is required")

    request_payload = {
        "web_app_query_id": web_app_query_id,
        "result": json.dumps(result),
    }
    url = _build_api_url(bot, "answerWebAppQuery")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=request_payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "answer_web_app_query_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            web_app_query_id=web_app_query_id,
        )
        raise AnswerWebAppQueryError(
            f"answerWebAppQuery request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "answer_web_app_query_failed",
            error_code=error_code,
            error=description,
            web_app_query_id=web_app_query_id,
        )
        raise AnswerWebAppQueryError(description, error_code=error_code)

    sent_message = data.get("result") or {}
    logger.info(
        "web_app_query_answered",
        web_app_query_id=web_app_query_id,
        result_type=result.get("type"),
        inline_message_id=sent_message.get("inline_message_id"),
    )
    return sent_message
