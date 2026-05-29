from html import escape
from typing import Any, Optional

import httpx
import structlog

from bot.services.create_new_sticker_set import _validate_required_text
from bot.services.get_sticker_set import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()


class SetStickerPositionInSetError(Exception):
    """Raised when raw ``setStickerPositionInSet`` validation or request fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


async def perform_set_sticker_position_in_set(
    bot: Any,
    *,
    sticker: str,
    position: int,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> bool:
    """Move a sticker to another zero-based position inside its Telegram set."""
    if position < 0:
        raise SetStickerPositionInSetError(
            "position must be a non-negative integer."
        )

    try:
        normalized_sticker = _validate_required_text(sticker, "sticker")
    except Exception as exc:
        raise SetStickerPositionInSetError(str(exc)) from exc

    payload = {
        "sticker": normalized_sticker,
        "position": position,
    }
    url = _build_api_url(bot, "setStickerPositionInSet")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "set_sticker_position_in_set_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            position=position,
        )
        raise SetStickerPositionInSetError(
            f"setStickerPositionInSet request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "set_sticker_position_in_set_failed",
            error_code=error_code,
            error=description,
            position=position,
        )
        raise SetStickerPositionInSetError(description, error_code=error_code)

    logger.info(
        "sticker_position_set",
        position=position,
    )
    return bool(data.get("result"))


def format_set_sticker_position_in_set_result(
    *,
    sticker: str,
    position: int,
) -> str:
    """Format a successful ``setStickerPositionInSet`` result for HTML."""
    return "\n".join(
        [
            "<b>setStickerPositionInSet</b>",
            "Sticker position updated.",
            f"Sticker file id: <code>{escape(sticker)}</code>",
            f"Position: <code>{position}</code>",
        ]
    )
