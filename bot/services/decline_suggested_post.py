from typing import Any, Optional

import httpx
import structlog

from bot.services.send_checklist import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()

DECLINE_SUGGESTED_POST_COMMENT_LIMIT = 128


class DeclineSuggestedPostError(Exception):
    """Raised when ``declineSuggestedPost`` validation or raw call fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


async def perform_decline_suggested_post(
    bot: Any,
    *,
    chat_id: int | str,
    message_id: int,
    comment: Optional[str] = None,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> bool:
    """Decline a direct-message suggested post via raw Bot API.

    Telegram Bot API 10.0 added ``declineSuggestedPost`` after the pinned
    aiogram version used by this project, so this helper isolates the raw HTTP
    call. Telegram requires the direct messages chat id and suggested post
    message id; ``comment`` is optional and is shown to the post creator.
    """
    if isinstance(chat_id, str):
        chat_id = chat_id.strip()
        if not chat_id:
            raise DeclineSuggestedPostError("chat_id must be provided.")
    if message_id <= 0:
        raise DeclineSuggestedPostError("message_id must be positive.")
    if comment is not None:
        comment = comment.strip()
        if len(comment) > DECLINE_SUGGESTED_POST_COMMENT_LIMIT:
            raise DeclineSuggestedPostError(
                "comment must be at most 128 characters."
            )

    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "message_id": message_id,
    }
    if comment is not None:
        payload["comment"] = comment

    url = _build_api_url(bot, "declineSuggestedPost")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "decline_suggested_post_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            chat_id=chat_id,
            message_id=message_id,
        )
        raise DeclineSuggestedPostError(
            f"declineSuggestedPost request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "decline_suggested_post_failed",
            error_code=error_code,
            error=description,
            chat_id=chat_id,
            message_id=message_id,
        )
        raise DeclineSuggestedPostError(description, error_code=error_code)

    if data.get("result") is not True:
        raise DeclineSuggestedPostError(
            "Telegram returned an unexpected declineSuggestedPost result."
        )

    logger.info(
        "suggested_post_declined",
        chat_id=chat_id,
        message_id=message_id,
        has_comment=comment is not None,
    )
    return True


def format_decline_suggested_post_result(
    *, chat_id: int | str, message_id: int, comment: Optional[str] = None
) -> str:
    comment_text = "\nComment: provided" if comment is not None else ""
    return (
        "Declined suggested post with <code>declineSuggestedPost</code>.\n"
        f"Chat: <code>{chat_id}</code>\n"
        f"Message: <code>{message_id}</code>"
        f"{comment_text}"
    )
