from typing import Any, Optional

import httpx
import structlog

from bot.services.post_story import POST_STORY_ACTIVE_PERIODS
from bot.services.send_checklist import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()


class RepostStoryError(Exception):
    """Raised when ``repostStory`` validation or raw Bot API call fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


async def perform_repost_story(
    bot: Any,
    *,
    business_connection_id: str,
    from_chat_id: int,
    from_story_id: int,
    active_period: int,
    post_to_chat_page: Optional[bool] = None,
    protect_content: Optional[bool] = None,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> dict[str, Any]:
    """Repost a bot-posted story between managed business accounts.

    Telegram Bot API ``repostStory`` (Bot API 10.0) requires both business
    accounts to be managed by the same bot and the ``can_manage_stories`` right
    on both accounts. The pinned ``aiogram==3.3.0`` has no typed wrapper, so
    this helper uses an isolated raw HTTP request.
    """
    business_connection_id = business_connection_id.strip()

    if not business_connection_id:
        raise RepostStoryError("business_connection_id is required.")
    if from_chat_id == 0:
        raise RepostStoryError("from_chat_id is required.")
    if from_story_id <= 0:
        raise RepostStoryError("from_story_id must be positive.")
    if active_period not in POST_STORY_ACTIVE_PERIODS:
        allowed = ", ".join(str(value) for value in POST_STORY_ACTIVE_PERIODS)
        raise RepostStoryError(f"active_period must be one of: {allowed}.")

    payload: dict[str, Any] = {
        "business_connection_id": business_connection_id,
        "from_chat_id": from_chat_id,
        "from_story_id": from_story_id,
        "active_period": active_period,
    }
    optional = {
        "post_to_chat_page": post_to_chat_page,
        "protect_content": protect_content,
    }
    payload.update({key: value for key, value in optional.items() if value is not None})

    url = _build_api_url(bot, "repostStory")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "repost_story_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            business_connection_id=business_connection_id,
            from_chat_id=from_chat_id,
            from_story_id=from_story_id,
        )
        raise RepostStoryError(f"repostStory request failed: {exc}") from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "repost_story_failed",
            error_code=error_code,
            error=description,
            business_connection_id=business_connection_id,
            from_chat_id=from_chat_id,
            from_story_id=from_story_id,
        )
        raise RepostStoryError(description, error_code=error_code)

    result = data.get("result") or {}
    logger.info(
        "story_reposted",
        business_connection_id=business_connection_id,
        from_chat_id=from_chat_id,
        from_story_id=from_story_id,
        active_period=active_period,
        post_to_chat_page=bool(post_to_chat_page),
        protect_content=bool(protect_content),
        story_id=result.get("id"),
    )
    return result
