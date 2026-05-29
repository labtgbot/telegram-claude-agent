import json
from typing import Any, Optional

import httpx
import structlog

from bot.services.send_checklist import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()


class CreateInvoiceLinkError(Exception):
    """Raised when the raw ``createInvoiceLink`` Bot API call fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


async def perform_create_invoice_link(
    bot: Any,
    *,
    title: str,
    description: str,
    payload: str,
    provider_token: str,
    currency: str,
    prices: list[dict[str, Any]],
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> str:
    """Create a Telegram invoice link through an isolated raw Bot API helper."""
    if not prices:
        raise CreateInvoiceLinkError("prices must contain at least one item.")

    request_payload: dict[str, Any] = {
        "title": title,
        "description": description,
        "payload": payload,
        "provider_token": provider_token,
        "currency": currency,
        "prices": json.dumps(prices),
    }

    url = _build_api_url(bot, "createInvoiceLink")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=request_payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "create_invoice_link_failed",
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise CreateInvoiceLinkError(
            f"createInvoiceLink request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description_text = data.get("description", "unknown error")
        logger.warning(
            "create_invoice_link_failed",
            error_code=error_code,
            error=description_text,
        )
        raise CreateInvoiceLinkError(description_text, error_code=error_code)

    result = data.get("result") or ""
    logger.info(
        "invoice_link_created",
        currency=currency,
        price_count=len(prices),
        has_result=bool(result),
    )
    return result
