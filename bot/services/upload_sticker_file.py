from html import escape
from pathlib import Path
from typing import Any, Optional

import httpx
import structlog
from aiogram.types import File

from bot.services.get_sticker_set import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()

STICKER_FORMATS = {"static", "animated", "video"}


class UploadStickerFileError(Exception):
    """Raised when raw ``uploadStickerFile`` validation or upload fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


def validate_sticker_format(sticker_format: str) -> str:
    """Validate the Telegram sticker format value."""
    normalized = sticker_format.strip().lower()
    if normalized not in STICKER_FORMATS:
        raise UploadStickerFileError(
            "sticker_format must be one of: animated, static, video."
        )
    return normalized


async def perform_upload_sticker_file(
    bot: Any,
    *,
    user_id: int,
    sticker_path: str,
    sticker_format: str,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> File:
    """Upload a sticker file for later sticker set lifecycle operations.

    Telegram ``uploadStickerFile`` accepts a target ``user_id``, a local sticker
    file, and the sticker format. The project pins ``aiogram==3.3.0``, so this
    Bot API method is isolated in a raw multipart helper and parsed back into
    aiogram's typed ``File`` model on success.
    """
    if user_id <= 0:
        raise UploadStickerFileError("user_id must be a positive integer.")

    normalized_format = validate_sticker_format(sticker_format)
    path = Path(sticker_path)
    if not path.is_file():
        raise UploadStickerFileError(f"Sticker file does not exist: {sticker_path}")

    url = _build_api_url(bot, "uploadStickerFile")

    try:
        with path.open("rb") as sticker_file:
            async with httpx.AsyncClient(timeout=request_timeout) as client:
                response = await client.post(
                    url,
                    data={
                        "user_id": str(user_id),
                        "sticker_format": normalized_format,
                    },
                    files={"sticker": (path.name, sticker_file)},
                )
                data = response.json()
    except (OSError, httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "upload_sticker_file_failed",
            user_id=user_id,
            sticker_path=sticker_path,
            sticker_format=normalized_format,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise UploadStickerFileError(
            f"uploadStickerFile request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "upload_sticker_file_failed",
            user_id=user_id,
            sticker_path=sticker_path,
            sticker_format=normalized_format,
            error_code=error_code,
            error=description,
        )
        raise UploadStickerFileError(description, error_code=error_code)

    result = data.get("result")
    if not isinstance(result, dict):
        raise UploadStickerFileError(
            "Telegram returned an unexpected uploadStickerFile result."
        )

    uploaded_file = File.model_validate(result)
    logger.info(
        "sticker_file_uploaded",
        user_id=user_id,
        sticker_path=sticker_path,
        sticker_format=normalized_format,
        file_id=uploaded_file.file_id,
    )
    return uploaded_file


def format_upload_sticker_file_result(
    *,
    user_id: int,
    sticker_path: str,
    sticker_format: str,
    file: File,
) -> str:
    """Format a successful ``uploadStickerFile`` result for HTML responses."""
    lines = [
        "<b>uploadStickerFile</b>",
        f"User: <code>{user_id}</code>",
        f"Sticker: {escape(sticker_path)}",
        f"Format: {escape(sticker_format)}",
        f"File id: <code>{escape(file.file_id)}</code>",
    ]
    file_unique_id = getattr(file, "file_unique_id", None)
    if file_unique_id:
        lines.append(f"File unique id: <code>{escape(file_unique_id)}</code>")
    file_size = getattr(file, "file_size", None)
    if file_size is not None:
        lines.append(f"File size: {file_size}")
    return "\n".join(lines)
