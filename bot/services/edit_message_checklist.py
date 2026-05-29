import json
from typing import Any, Optional

import httpx
import structlog

from bot.services.send_checklist import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()


class EditMessageChecklistError(Exception):
    """Raised when ``editMessageChecklist`` validation or raw Bot API call fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


async def perform_edit_message_checklist(
    bot: Any,
    *,
    business_connection_id: str,
    chat_id: int | str,
    message_id: int,
    checklist: dict[str, Any],
    reply_markup: Optional[dict[str, Any]] = None,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> dict[str, Any]:
    """Edit a checklist message via raw Telegram Bot API ``editMessageChecklist``.

    Telegram Bot API 10.0 exposes this method only for checklists sent on
    behalf of a connected business account. The pinned ``aiogram==3.3.0`` has no
    typed wrapper for it, so this helper posts the JSON payload directly and
    returns the edited ``Message`` object. Checklist title/task content is kept
    out of logs; only ids, task count and error shape are logged.
    """
    business_connection_id = (business_connection_id or "").strip()
    if not business_connection_id:
        raise EditMessageChecklistError("business_connection_id is required.")
    if message_id <= 0:
        raise EditMessageChecklistError("message_id must be positive.")
    if not isinstance(checklist, dict) or not checklist:
        raise EditMessageChecklistError("checklist is required.")

    payload: dict[str, Any] = {
        "business_connection_id": business_connection_id,
        "chat_id": chat_id,
        "message_id": message_id,
        "checklist": json.dumps(checklist),
    }
    if reply_markup is not None:
        payload["reply_markup"] = json.dumps(reply_markup)

    url = _build_api_url(bot, "editMessageChecklist")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "edit_message_checklist_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            chat_id=chat_id,
            message_id=message_id,
        )
        raise EditMessageChecklistError(
            f"editMessageChecklist request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "edit_message_checklist_failed",
            error_code=error_code,
            error=description,
            chat_id=chat_id,
            message_id=message_id,
        )
        raise EditMessageChecklistError(description, error_code=error_code)

    result = data.get("result") or {}
    logger.info(
        "message_checklist_edited",
        chat_id=chat_id,
        message_id=message_id,
        task_count=len(checklist.get("tasks", [])),
        edited_message_id=result.get("message_id"),
    )
    return result
