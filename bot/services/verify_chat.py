from typing import Any, Optional, Union

import httpx
import structlog

from bot.services.send_checklist import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()

VERIFY_CHAT_DESCRIPTION_LIMIT = 70
ChatId = Union[int, str]


class VerifyChatError(Exception):
    """Raised when the raw ``verifyChat`` Bot API call fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


async def perform_verify_chat(
    bot: Any,
    *,
    chat_id: ChatId,
    custom_description: Optional[str] = None,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> bool:
    """Verify a chat through an isolated raw Bot API helper."""
    if isinstance(chat_id, int) and chat_id == 0:
        raise VerifyChatError("chat_id must not be 0.")
    if isinstance(chat_id, str) and not chat_id.strip():
        raise VerifyChatError("chat_id must not be empty.")
    if (
        custom_description is not None
        and len(custom_description) > VERIFY_CHAT_DESCRIPTION_LIMIT
    ):
        raise VerifyChatError(
            f"custom_description must be at most {VERIFY_CHAT_DESCRIPTION_LIMIT} "
            "characters."
        )

    request_payload: dict[str, Any] = {"chat_id": chat_id}
    if custom_description is not None:
        request_payload["custom_description"] = custom_description

    url = _build_api_url(bot, "verifyChat")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=request_payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "verify_chat_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            chat_id=chat_id,
            has_custom_description=custom_description is not None,
        )
        raise VerifyChatError(f"verifyChat request failed: {exc}") from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "verify_chat_failed",
            error_code=error_code,
            error=description,
            chat_id=chat_id,
            has_custom_description=custom_description is not None,
        )
        raise VerifyChatError(description, error_code=error_code)

    if data.get("result") is not True:
        logger.warning(
            "verify_chat_failed",
            error="unexpected result",
            chat_id=chat_id,
            has_custom_description=custom_description is not None,
        )
        raise VerifyChatError("Telegram returned an unexpected verifyChat result.")

    logger.info(
        "chat_verified",
        chat_id=chat_id,
        has_custom_description=bool(custom_description),
    )
    return True
