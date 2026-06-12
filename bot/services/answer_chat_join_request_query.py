from typing import Any, Optional

import httpx
import structlog

from bot.services.send_message_draft import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()

CHAT_JOIN_REQUEST_QUERY_RESULTS = frozenset({"approve", "decline", "queue"})


class AnswerChatJoinRequestQueryError(Exception):
    """Raised when ``answerChatJoinRequestQuery`` validation or raw call fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


async def perform_answer_chat_join_request_query(
    bot: Any,
    *,
    chat_join_request_query_id: str,
    result: str,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> bool:
    """Process a Bot API 10.1 chat join request query."""
    if not chat_join_request_query_id:
        raise AnswerChatJoinRequestQueryError("chat_join_request_query_id is required.")
    if result not in CHAT_JOIN_REQUEST_QUERY_RESULTS:
        allowed = ", ".join(sorted(CHAT_JOIN_REQUEST_QUERY_RESULTS))
        raise AnswerChatJoinRequestQueryError(f"result must be one of: {allowed}.")

    payload = {
        "chat_join_request_query_id": chat_join_request_query_id,
        "result": result,
    }
    url = _build_api_url(bot, "answerChatJoinRequestQuery")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "answer_chat_join_request_query_failed",
            query_id_length=len(chat_join_request_query_id),
            result=result,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise AnswerChatJoinRequestQueryError(
            f"answerChatJoinRequestQuery request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "answer_chat_join_request_query_failed",
            query_id_length=len(chat_join_request_query_id),
            result=result,
            error_code=error_code,
            error=description,
        )
        raise AnswerChatJoinRequestQueryError(description, error_code=error_code)

    logger.info(
        "chat_join_request_query_answered",
        query_id_length=len(chat_join_request_query_id),
        result=result,
    )
    return data.get("result", True)
