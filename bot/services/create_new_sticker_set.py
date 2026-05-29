from html import escape
from typing import Any, Optional

import httpx
import structlog

from bot.services.get_sticker_set import DEFAULT_REQUEST_TIMEOUT, _build_api_url
from bot.services.upload_sticker_file import validate_sticker_format

logger = structlog.get_logger()

STICKER_TYPES = {"regular", "mask", "custom_emoji"}


class CreateNewStickerSetError(Exception):
    """Raised when raw ``createNewStickerSet`` validation or request fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


def validate_sticker_type(sticker_type: str) -> str:
    """Validate the Telegram sticker set type value."""
    normalized = sticker_type.strip().lower()
    if normalized not in STICKER_TYPES:
        raise CreateNewStickerSetError(
            "sticker_type must be one of: custom_emoji, mask, regular."
        )
    return normalized


def _validate_required_text(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise CreateNewStickerSetError(f"{field_name} must not be empty.")
    return normalized


async def perform_create_new_sticker_set(
    bot: Any,
    *,
    user_id: int,
    name: str,
    title: str,
    sticker_type: str,
    sticker_format: str,
    sticker: str,
    emoji_list: list[str],
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> bool:
    """Create a Telegram sticker set through raw Bot API.

    The project pins ``aiogram==3.3.0``, so ``createNewStickerSet`` is kept in
    an isolated raw helper. The command intentionally supports the smallest
    auditable lifecycle scenario: one pre-uploaded sticker ``file_id`` plus an
    emoji list. Operators can get that ``file_id`` through ``uploadStickerFile``.
    """
    if user_id <= 0:
        raise CreateNewStickerSetError("user_id must be a positive integer.")

    normalized_name = _validate_required_text(name, "name")
    normalized_title = _validate_required_text(title, "title")
    normalized_type = validate_sticker_type(sticker_type)
    normalized_format = validate_sticker_format(sticker_format)
    normalized_sticker = _validate_required_text(sticker, "sticker")
    normalized_emoji_list = [emoji.strip() for emoji in emoji_list if emoji.strip()]
    if not normalized_emoji_list:
        raise CreateNewStickerSetError("emoji_list must contain at least one emoji.")

    payload = {
        "user_id": user_id,
        "name": normalized_name,
        "title": normalized_title,
        "sticker_type": normalized_type,
        "stickers": [
            {
                "sticker": normalized_sticker,
                "format": normalized_format,
                "emoji_list": normalized_emoji_list,
            }
        ],
    }
    url = _build_api_url(bot, "createNewStickerSet")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "create_new_sticker_set_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            sticker_set_name=normalized_name,
            user_id=user_id,
        )
        raise CreateNewStickerSetError(
            f"createNewStickerSet request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "create_new_sticker_set_failed",
            error_code=error_code,
            error=description,
            sticker_set_name=normalized_name,
            user_id=user_id,
        )
        raise CreateNewStickerSetError(description, error_code=error_code)

    logger.info(
        "sticker_set_created",
        sticker_set_name=normalized_name,
        user_id=user_id,
        sticker_type=normalized_type,
        sticker_format=normalized_format,
        emoji_count=len(normalized_emoji_list),
    )
    return bool(data.get("result"))


def format_create_new_sticker_set_result(
    *,
    user_id: int,
    name: str,
    title: str,
    sticker_type: str,
    sticker_format: str,
    sticker: str,
    emoji_list: list[str],
) -> str:
    """Format a successful ``createNewStickerSet`` result for HTML responses."""
    return "\n".join(
        [
            "<b>createNewStickerSet</b>",
            "Sticker set created.",
            f"User: <code>{user_id}</code>",
            f"Name: <code>{escape(name)}</code>",
            f"Title: {escape(title)}",
            f"Type: {escape(sticker_type)}",
            f"Format: {escape(sticker_format)}",
            f"Sticker file id: <code>{escape(sticker)}</code>",
            f"Emoji: {escape(', '.join(emoji_list))}",
        ]
    )
