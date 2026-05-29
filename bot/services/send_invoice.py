import json
from typing import Any, Optional

import httpx
import structlog

from bot.services.send_checklist import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()


class SendInvoiceError(Exception):
    """Raised when the raw ``sendInvoice`` Bot API call fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


async def perform_send_invoice(
    bot: Any,
    *,
    chat_id: int,
    title: str,
    description: str,
    payload: str,
    provider_token: str,
    currency: str,
    prices: list[dict[str, Any]],
    start_parameter: Optional[str] = None,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> dict:
    """Send an invoice through an isolated raw Bot API helper.

    ``aiogram==3.3.0`` predates the current payments surface this project
    tracks, so this helper calls ``sendInvoice`` directly. The exposed scenario
    is intentionally narrow: an admin can send a single-price test invoice to
    the current chat. For Telegram Stars invoices, Telegram expects
    ``provider_token`` to be an empty string, ``currency`` to be ``XTR`` and
    exactly one price item.
    """
    if not prices:
        raise SendInvoiceError("prices must contain at least one item.")

    request_payload: dict[str, Any] = {
        "chat_id": chat_id,
        "title": title,
        "description": description,
        "payload": payload,
        "provider_token": provider_token,
        "currency": currency,
        "prices": json.dumps(prices),
    }
    if start_parameter is not None:
        request_payload["start_parameter"] = start_parameter

    url = _build_api_url(bot, "sendInvoice")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=request_payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "send_invoice_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            chat_id=chat_id,
        )
        raise SendInvoiceError(f"sendInvoice request failed: {exc}") from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description_text = data.get("description", "unknown error")
        logger.warning(
            "send_invoice_failed",
            error_code=error_code,
            error=description_text,
            chat_id=chat_id,
        )
        raise SendInvoiceError(description_text, error_code=error_code)

    result = data.get("result") or {}
    logger.info(
        "invoice_sent",
        chat_id=chat_id,
        currency=currency,
        price_count=len(prices),
        has_start_parameter=start_parameter is not None,
        sent_message_id=result.get("message_id"),
    )
    return result
