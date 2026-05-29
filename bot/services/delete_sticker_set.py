from html import escape
from typing import Any, Optional

import httpx
import structlog

from bot.services.create_new_sticker_set import _validate_required_text
from bot.services.get_sticker_set import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()


class DeleteStickerSetError(Exception):
    """Raised when raw ``deleteStickerSet`` validation or request fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


async def perform_delete_sticker_set(
    bot: Any,
    *,
    name: str,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> bool:
    """Delete a bot-created Telegram sticker set by name."""
    try:
        normalized_name = _validate_required_text(name, "name")
    except Exception as exc:
        raise DeleteStickerSetError(str(exc)) from exc

    payload = {"name": normalized_name}
    url = _build_api_url(bot, "deleteStickerSet")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "delete_sticker_set_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            sticker_set_name=normalized_name,
        )
        raise DeleteStickerSetError(f"deleteStickerSet request failed: {exc}") from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "delete_sticker_set_failed",
            error_code=error_code,
            error=description,
            sticker_set_name=normalized_name,
        )
        raise DeleteStickerSetError(description, error_code=error_code)

    logger.info("sticker_set_deleted", sticker_set_name=normalized_name)
    return bool(data.get("result"))


def format_delete_sticker_set_result(*, name: str) -> str:
    """Format a successful ``deleteStickerSet`` result for HTML."""
    return "\n".join(
        [
            "<b>deleteStickerSet</b>",
            "Sticker set deleted.",
            f"Name: <code>{escape(name)}</code>",
        ]
    )
