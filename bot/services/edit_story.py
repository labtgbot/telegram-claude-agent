import json
from typing import Any, Optional

import httpx
import structlog

from bot.services.post_story import POST_STORY_CAPTION_LIMIT
from bot.services.send_checklist import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()


class EditStoryError(Exception):
    """Raised when ``editStory`` validation or raw Bot API call fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


async def perform_edit_story(
    bot: Any,
    *,
    business_connection_id: str,
    story_id: int,
    content: dict[str, Any],
    caption: Optional[str] = None,
    parse_mode: Optional[str] = None,
    caption_entities: Optional[list[dict[str, Any]]] = None,
    areas: Optional[list[dict[str, Any]]] = None,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> dict[str, Any]:
    """Edit a story posted by the bot for a managed business account.

    Telegram Bot API ``editStory`` (Bot API 10.0) requires a live
    ``business_connection_id``, a positive ``story_id`` and a replacement
    ``InputStoryContent``. The pinned ``aiogram==3.3.0`` has no typed wrapper,
    so this helper uses an isolated raw HTTP request.
    """
    business_connection_id = business_connection_id.strip()
    caption = caption.strip() if caption is not None else None

    if not business_connection_id:
        raise EditStoryError("business_connection_id is required.")
    if story_id <= 0:
        raise EditStoryError("story_id must be positive.")
    if not content:
        raise EditStoryError("content is required.")
    if caption is not None and len(caption) > POST_STORY_CAPTION_LIMIT:
        raise EditStoryError(
            f"caption must be at most {POST_STORY_CAPTION_LIMIT} characters."
        )

    payload: dict[str, Any] = {
        "business_connection_id": business_connection_id,
        "story_id": story_id,
        "content": json.dumps(content),
    }
    optional = {
        "caption": caption,
        "parse_mode": parse_mode,
        "caption_entities": (
            json.dumps(caption_entities) if caption_entities is not None else None
        ),
        "areas": json.dumps(areas) if areas is not None else None,
    }
    payload.update({key: value for key, value in optional.items() if value is not None})

    url = _build_api_url(bot, "editStory")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "edit_story_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            business_connection_id=business_connection_id,
            story_id=story_id,
        )
        raise EditStoryError(f"editStory request failed: {exc}") from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "edit_story_failed",
            error_code=error_code,
            error=description,
            business_connection_id=business_connection_id,
            story_id=story_id,
        )
        raise EditStoryError(description, error_code=error_code)

    result = data.get("result") or {}
    logger.info(
        "story_edited",
        business_connection_id=business_connection_id,
        story_id=story_id,
        has_caption=bool(caption),
        result_story_id=result.get("id"),
    )
    return result
