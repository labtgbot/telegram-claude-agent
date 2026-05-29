from html import escape
from typing import Any, Optional

import httpx
import structlog

from bot.services.send_checklist import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()


class TransferGiftError(Exception):
    """Raised when ``transferGift`` validation or call fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


async def perform_transfer_gift(
    bot: Any,
    *,
    business_connection_id: str,
    owned_gift_id: str,
    new_owner_chat_id: int,
    star_count: Optional[int] = None,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> bool:
    """Transfer a unique gift owned by a managed business account."""
    business_connection_id = business_connection_id.strip()
    if not business_connection_id:
        raise TransferGiftError("business_connection_id is required.")

    owned_gift_id = owned_gift_id.strip()
    if not owned_gift_id:
        raise TransferGiftError("owned_gift_id is required.")

    if not isinstance(new_owner_chat_id, int) or new_owner_chat_id == 0:
        raise TransferGiftError("new_owner_chat_id must be a non-zero integer.")

    if star_count is not None:
        if not isinstance(star_count, int):
            raise TransferGiftError("star_count must be an integer.")
        if star_count < 0:
            raise TransferGiftError("star_count must be a non-negative integer.")

    payload: dict[str, Any] = {
        "business_connection_id": business_connection_id,
        "owned_gift_id": owned_gift_id,
        "new_owner_chat_id": new_owner_chat_id,
    }
    if star_count is not None:
        payload["star_count"] = star_count

    url = _build_api_url(bot, "transferGift")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "transfer_gift_failed",
            business_connection_id=business_connection_id,
            owned_gift_id=owned_gift_id,
            new_owner_chat_id=new_owner_chat_id,
            star_count=star_count,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise TransferGiftError(f"transferGift request failed: {exc}") from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "transfer_gift_failed",
            business_connection_id=business_connection_id,
            owned_gift_id=owned_gift_id,
            new_owner_chat_id=new_owner_chat_id,
            star_count=star_count,
            error_code=error_code,
            error=description,
        )
        raise TransferGiftError(description, error_code=error_code)

    result = data.get("result")
    if result is not True:
        raise TransferGiftError("Telegram returned an unexpected transferGift result.")

    logger.info(
        "gift_transferred",
        business_connection_id=business_connection_id,
        owned_gift_id=owned_gift_id,
        new_owner_chat_id=new_owner_chat_id,
        star_count=star_count,
    )
    return True


def format_transfer_gift_result(
    *,
    business_connection_id: str,
    owned_gift_id: str,
    new_owner_chat_id: int,
    star_count: Optional[int] = None,
) -> str:
    """Format a successful ``transferGift`` result."""
    lines = [
        "<b>transferGift</b>",
        f"Business connection: <code>{escape(business_connection_id)}</code>",
        f"Owned gift: <code>{escape(owned_gift_id)}</code>",
        f"New owner chat: <code>{escape(str(new_owner_chat_id))}</code>",
    ]
    if star_count is not None:
        lines.append(f"Transfer Stars: <code>{escape(str(star_count))}</code>")
    lines.extend(
        [
            "Status: gift transferred to the new owner.",
            "Rollback: this transfer cannot be reversed by the bot.",
        ]
    )
    return "\n".join(lines)
