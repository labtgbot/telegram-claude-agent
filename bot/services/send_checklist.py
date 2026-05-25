import json
from typing import Any, Optional

import httpx
import structlog

logger = structlog.get_logger()

DEFAULT_REQUEST_TIMEOUT = 60.0


class SendChecklistError(Exception):
    """Raised when the raw ``sendChecklist`` Bot API call fails.

    The pinned ``aiogram==3.3.0`` (Bot API 7.0) predates the Bot API 9.1
    ``sendChecklist`` method and ships no typed wrapper for it, so this helper
    calls the raw HTTP endpoint directly. Failures (transport errors or a
    Telegram ``ok: false`` response) are surfaced through this dedicated
    exception instead of aiogram's ``TelegramAPIError`` so the command handler
    has a single, version-independent error type to catch. ``error_code`` holds
    the Telegram ``error_code`` when the failure comes from a Telegram response.
    """

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


def _build_api_url(bot: Any, method: str) -> str:
    """Resolve the Bot API URL for ``method`` from the bot's session.

    Prefers aiogram's ``bot.session.api.api_url(token, method)`` so a custom
    local Bot API server is honoured, and falls back to the production cloud
    endpoint when the session does not expose that helper (e.g. in tests with a
    minimal bot stub).
    """
    session = getattr(bot, "session", None)
    api = getattr(session, "api", None)
    api_url = getattr(api, "api_url", None)
    if callable(api_url):
        return api_url(token=bot.token, method=method)
    return f"https://api.telegram.org/bot{bot.token}/{method}"


async def perform_send_checklist(
    bot: Any,
    *,
    business_connection_id: str,
    chat_id: int,
    checklist: dict[str, Any],
    disable_notification: Optional[bool] = None,
    protect_content: Optional[bool] = None,
    message_effect_id: Optional[str] = None,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> dict:
    """Send a checklist into a chat via a raw Telegram Bot API call.

    The Telegram ``sendChecklist`` method (Bot API 9.1) sends a checklist on
    behalf of a connected business account: a titled list of 1-30 tasks that
    recipients can tick off. It requires ``business_connection_id`` (the
    business connection on behalf of which the message is sent), ``chat_id`` and
    the ``checklist`` (an ``InputChecklist`` object) and returns the sent
    ``Message`` on success. The checklist ``title`` is limited to 1-255
    characters and each task ``text`` to 1-100 characters after entities
    parsing; every task carries a positive ``id`` that must be unique within the
    checklist. Because the method acts on behalf of a business account, the bot
    must be connected to one and ``business_connection_id`` must be a live
    connection; it cannot be used as an ordinary chat command without
    business-mode.

    Because the pinned ``aiogram==3.3.0`` (Bot API 7.0) has no typed wrapper for
    this Bot API 9.1 method, this is an isolated raw helper: it POSTs the JSON
    payload to the ``sendChecklist`` HTTP endpoint via ``httpx`` and returns the
    parsed ``result`` dict. The ``checklist`` object is JSON-serialized into the
    request body as Telegram expects. Transport failures and Telegram
    ``ok: false`` responses are raised as :class:`SendChecklistError`.

    The checklist title and task texts are operator-provided content, so they
    are intentionally kept out of the structured logs; only the task count and
    the sent message id are logged.
    """
    request_payload: dict[str, Any] = {
        "business_connection_id": business_connection_id,
        "chat_id": chat_id,
        "checklist": json.dumps(checklist),
    }
    optional = {
        "disable_notification": disable_notification,
        "protect_content": protect_content,
        "message_effect_id": message_effect_id,
    }
    request_payload.update(
        {key: value for key, value in optional.items() if value is not None}
    )

    url = _build_api_url(bot, "sendChecklist")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=request_payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "send_checklist_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            chat_id=chat_id,
        )
        raise SendChecklistError(f"sendChecklist request failed: {exc}") from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "send_checklist_failed",
            error_code=error_code,
            error=description,
            chat_id=chat_id,
        )
        raise SendChecklistError(description, error_code=error_code)

    result = data.get("result") or {}
    logger.info(
        "checklist_sent",
        chat_id=chat_id,
        task_count=len(checklist.get("tasks", [])),
        protect_content=bool(protect_content),
        sent_message_id=result.get("message_id"),
    )
    return result
