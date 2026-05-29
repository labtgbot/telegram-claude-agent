from typing import Any, Optional

import httpx
import structlog

from bot.services.send_checklist import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()


class ApproveSuggestedPostError(Exception):
    """Raised when ``approveSuggestedPost`` validation or raw call fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


async def perform_approve_suggested_post(
    bot: Any,
    *,
    chat_id: int | str,
    message_id: int,
    send_date: Optional[int] = None,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> bool:
    """Approve a direct-message suggested post via raw Bot API.

    Telegram Bot API 10.0 added ``approveSuggestedPost`` after the pinned
    aiogram version used by this project, so this helper isolates the raw HTTP
    call. Telegram requires the direct messages chat id and suggested post
    message id; ``send_date`` can schedule the post for a future Unix time.
    """
    if isinstance(chat_id, str):
        chat_id = chat_id.strip()
        if not chat_id:
            raise ApproveSuggestedPostError("chat_id must be provided.")
    if message_id <= 0:
        raise ApproveSuggestedPostError("message_id must be positive.")
    if send_date is not None and send_date <= 0:
        raise ApproveSuggestedPostError("send_date must be a positive Unix time.")

    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "message_id": message_id,
    }
    if send_date is not None:
        payload["send_date"] = send_date

    url = _build_api_url(bot, "approveSuggestedPost")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "approve_suggested_post_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            chat_id=chat_id,
            message_id=message_id,
        )
        raise ApproveSuggestedPostError(
            f"approveSuggestedPost request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "approve_suggested_post_failed",
            error_code=error_code,
            error=description,
            chat_id=chat_id,
            message_id=message_id,
        )
        raise ApproveSuggestedPostError(description, error_code=error_code)

    if data.get("result") is not True:
        raise ApproveSuggestedPostError(
            "Telegram returned an unexpected approveSuggestedPost result."
        )

    logger.info(
        "suggested_post_approved",
        chat_id=chat_id,
        message_id=message_id,
        has_send_date=send_date is not None,
    )
    return True


def format_approve_suggested_post_result(
    *, chat_id: int | str, message_id: int, send_date: Optional[int] = None
) -> str:
    send_date_text = (
        f"\nSend date: <code>{send_date}</code>" if send_date is not None else ""
    )
    return (
        "Approved suggested post with <code>approveSuggestedPost</code>.\n"
        f"Chat: <code>{chat_id}</code>\n"
        f"Message: <code>{message_id}</code>"
        f"{send_date_text}"
    )
