import json
from typing import Any, Optional

import httpx
import structlog

from bot.services.send_checklist import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()

POST_STORY_ACTIVE_PERIODS = (6 * 3600, 12 * 3600, 86400, 2 * 86400)
POST_STORY_CAPTION_LIMIT = 2048


class PostStoryError(Exception):
    """Raised when ``postStory`` validation or raw Bot API call fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


async def perform_post_story(
    bot: Any,
    *,
    business_connection_id: str,
    content: dict[str, Any],
    active_period: int,
    caption: Optional[str] = None,
    parse_mode: Optional[str] = None,
    caption_entities: Optional[list[dict[str, Any]]] = None,
    areas: Optional[list[dict[str, Any]]] = None,
    post_to_chat_page: Optional[bool] = None,
    protect_content: Optional[bool] = None,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> dict:
    """Post a story on behalf of a managed business account.

    Telegram Bot API ``postStory`` (Bot API 10.0) requires a live
    ``business_connection_id`` and the ``can_manage_stories`` business bot
    right. The pinned ``aiogram==3.3.0`` does not expose this method, so this
    helper uses an isolated raw HTTP request and returns Telegram's ``Story``
    result as a dict.
    """
    business_connection_id = business_connection_id.strip()
    caption = caption.strip() if caption is not None else None

    if not business_connection_id:
        raise PostStoryError("business_connection_id is required.")
    if not content:
        raise PostStoryError("content is required.")
    if active_period not in POST_STORY_ACTIVE_PERIODS:
        allowed = ", ".join(str(value) for value in POST_STORY_ACTIVE_PERIODS)
        raise PostStoryError(f"active_period must be one of: {allowed}.")
    if caption is not None and len(caption) > POST_STORY_CAPTION_LIMIT:
        raise PostStoryError(
            f"caption must be at most {POST_STORY_CAPTION_LIMIT} characters."
        )

    payload: dict[str, Any] = {
        "business_connection_id": business_connection_id,
        "content": json.dumps(content),
        "active_period": active_period,
    }
    optional = {
        "caption": caption,
        "parse_mode": parse_mode,
        "caption_entities": (
            json.dumps(caption_entities) if caption_entities is not None else None
        ),
        "areas": json.dumps(areas) if areas is not None else None,
        "post_to_chat_page": post_to_chat_page,
        "protect_content": protect_content,
    }
    payload.update({key: value for key, value in optional.items() if value is not None})

    url = _build_api_url(bot, "postStory")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "post_story_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            business_connection_id=business_connection_id,
        )
        raise PostStoryError(f"postStory request failed: {exc}") from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "post_story_failed",
            error_code=error_code,
            error=description,
            business_connection_id=business_connection_id,
        )
        raise PostStoryError(description, error_code=error_code)

    result = data.get("result") or {}
    logger.info(
        "story_posted",
        business_connection_id=business_connection_id,
        active_period=active_period,
        has_caption=bool(caption),
        post_to_chat_page=bool(post_to_chat_page),
        protect_content=bool(protect_content),
        story_id=result.get("id"),
    )
    return result
