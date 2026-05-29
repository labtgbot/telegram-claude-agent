from typing import Any, Optional, Union

import httpx
import structlog

from bot.services.send_checklist import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()

ChatId = Union[int, str]


class RemoveChatVerificationError(Exception):
    """Raised when the raw ``removeChatVerification`` Bot API call fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


async def perform_remove_chat_verification(
    bot: Any,
    *,
    chat_id: ChatId,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> bool:
    """Remove a chat's Telegram verification through an isolated raw helper."""
    if isinstance(chat_id, int) and chat_id == 0:
        raise RemoveChatVerificationError("chat_id must not be 0.")
    if isinstance(chat_id, str) and not chat_id.strip():
        raise RemoveChatVerificationError("chat_id must not be empty.")

    request_payload: dict[str, Any] = {"chat_id": chat_id}
    url = _build_api_url(bot, "removeChatVerification")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=request_payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "remove_chat_verification_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            chat_id=chat_id,
        )
        raise RemoveChatVerificationError(
            f"removeChatVerification request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "remove_chat_verification_failed",
            error_code=error_code,
            error=description,
            chat_id=chat_id,
        )
        raise RemoveChatVerificationError(description, error_code=error_code)

    if data.get("result") is not True:
        logger.warning(
            "remove_chat_verification_failed",
            error="unexpected result",
            chat_id=chat_id,
        )
        raise RemoveChatVerificationError(
            "Telegram returned an unexpected removeChatVerification result."
        )

    logger.info("chat_verification_removed", chat_id=chat_id)
    return True
