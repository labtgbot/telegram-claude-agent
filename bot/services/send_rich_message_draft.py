from typing import Any, Optional

import httpx
import structlog

from bot.services.send_message_draft import DEFAULT_REQUEST_TIMEOUT, _build_api_url
from bot.services.send_rich_message import SendRichMessageError, validate_input_rich_message

logger = structlog.get_logger()


class SendRichMessageDraftError(Exception):
    """Raised when ``sendRichMessageDraft`` validation or the raw call fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


def _validate_rich_message_draft_args(
    *,
    chat_id: int,
    draft_id: int,
    rich_message: dict[str, Any],
) -> None:
    if chat_id == 0:
        raise SendRichMessageDraftError("chat_id must be non-zero.")
    if draft_id == 0:
        raise SendRichMessageDraftError("draft_id must be non-zero.")
    try:
        validate_input_rich_message(rich_message)
    except SendRichMessageError as exc:
        raise SendRichMessageDraftError(exc.message) from exc


async def perform_send_rich_message_draft(
    bot: Any,
    *,
    chat_id: int,
    draft_id: int,
    rich_message: dict[str, Any],
    message_thread_id: Optional[int] = None,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> bool:
    """Stream a Bot API 10.1 rich message draft through a raw HTTP call."""
    _validate_rich_message_draft_args(
        chat_id=chat_id,
        draft_id=draft_id,
        rich_message=rich_message,
    )

    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "draft_id": draft_id,
        "rich_message": rich_message,
    }
    if message_thread_id is not None:
        payload["message_thread_id"] = message_thread_id

    url = _build_api_url(bot, "sendRichMessageDraft")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "send_rich_message_draft_failed",
            chat_id=chat_id,
            draft_id=draft_id,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise SendRichMessageDraftError(
            f"sendRichMessageDraft request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "send_rich_message_draft_failed",
            chat_id=chat_id,
            draft_id=draft_id,
            error_code=error_code,
            error=description,
        )
        raise SendRichMessageDraftError(description, error_code=error_code)

    logger.info(
        "rich_message_draft_sent",
        chat_id=chat_id,
        draft_id=draft_id,
        has_thread=message_thread_id is not None,
        content_format="html" if "html" in rich_message else "markdown",
    )
    return data.get("result", True)
