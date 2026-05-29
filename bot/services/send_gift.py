from typing import Any, Optional

import httpx
import structlog

from bot.services.send_checklist import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()


class SendGiftError(Exception):
    """Raised when the raw ``sendGift`` Bot API call fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


async def perform_send_gift(
    bot: Any,
    *,
    gift_id: str,
    user_id: Optional[int] = None,
    chat_id: Optional[int | str] = None,
    pay_for_upgrade: Optional[bool] = None,
    text: Optional[str] = None,
    text_parse_mode: Optional[str] = None,
    text_entities: Optional[list[dict[str, Any]]] = None,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> bool:
    """Send a Telegram gift through an isolated raw Bot API helper.

    ``aiogram==3.3.0`` predates Bot API 10.0 ``sendGift``, so this helper
    calls the raw endpoint directly. Telegram requires ``gift_id`` and exactly
    one receiver: ``user_id`` for a user or ``chat_id`` for a channel chat.
    The gift cost is withdrawn from the bot's Stars balance, so callers should
    keep this behind an admin allowlist and an explicit confirmation step.
    """
    if (user_id is None) == (chat_id is None):
        raise SendGiftError("Specify exactly one of user_id or chat_id.")

    request_payload: dict[str, Any] = {"gift_id": gift_id}
    if user_id is not None:
        request_payload["user_id"] = user_id
    if chat_id is not None:
        request_payload["chat_id"] = chat_id

    optional = {
        "pay_for_upgrade": pay_for_upgrade,
        "text": text,
        "text_parse_mode": text_parse_mode,
        "text_entities": text_entities,
    }
    request_payload.update(
        {key: value for key, value in optional.items() if value is not None}
    )

    url = _build_api_url(bot, "sendGift")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=request_payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "send_gift_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            gift_id=gift_id,
            receiver_type="user" if user_id is not None else "chat",
        )
        raise SendGiftError(f"sendGift request failed: {exc}") from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "send_gift_failed",
            error_code=error_code,
            error=description,
            gift_id=gift_id,
            receiver_type="user" if user_id is not None else "chat",
        )
        raise SendGiftError(description, error_code=error_code)

    if data.get("result") is not True:
        logger.warning("send_gift_failed", error="unexpected result")
        raise SendGiftError("Telegram returned an unexpected sendGift result.")

    logger.info(
        "gift_sent",
        gift_id=gift_id,
        receiver_type="user" if user_id is not None else "chat",
        pay_for_upgrade=bool(pay_for_upgrade),
        has_text=bool(text),
    )
    return True
