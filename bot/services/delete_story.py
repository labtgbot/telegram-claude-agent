from typing import Any, Optional

import httpx
import structlog

from bot.services.send_checklist import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()


class DeleteStoryError(Exception):
    """Raised when ``deleteStory`` validation or raw Bot API call fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


async def perform_delete_story(
    bot: Any,
    *,
    business_connection_id: str,
    story_id: int,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> bool:
    """Delete a story posted by the bot for a managed business account.

    Telegram Bot API ``deleteStory`` (Bot API 10.0) requires a live
    ``business_connection_id`` and a positive ``story_id``. The pinned
    ``aiogram==3.3.0`` has no typed wrapper, so this helper uses an isolated
    raw HTTP request.
    """
    business_connection_id = business_connection_id.strip()

    if not business_connection_id:
        raise DeleteStoryError("business_connection_id is required.")
    if story_id <= 0:
        raise DeleteStoryError("story_id must be positive.")

    payload: dict[str, Any] = {
        "business_connection_id": business_connection_id,
        "story_id": story_id,
    }
    url = _build_api_url(bot, "deleteStory")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "delete_story_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            business_connection_id=business_connection_id,
            story_id=story_id,
        )
        raise DeleteStoryError(f"deleteStory request failed: {exc}") from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "delete_story_failed",
            error_code=error_code,
            error=description,
            business_connection_id=business_connection_id,
            story_id=story_id,
        )
        raise DeleteStoryError(description, error_code=error_code)

    logger.info(
        "story_deleted",
        business_connection_id=business_connection_id,
        story_id=story_id,
    )
    return bool(data.get("result"))
