from html import escape
from typing import Any, Optional

import httpx
import structlog

from bot.services.send_checklist import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()

GET_CHAT_GIFTS_MIN_LIMIT = 1
GET_CHAT_GIFTS_MAX_LIMIT = 100


class GetChatGiftsError(Exception):
    """Raised when ``getChatGifts`` validation or call fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


def normalize_get_chat_gifts_options(
    *,
    exclude_unsaved: bool = False,
    exclude_saved: bool = False,
    exclude_unlimited: bool = False,
    exclude_limited_upgradable: bool = False,
    exclude_limited_non_upgradable: bool = False,
    exclude_from_blockchain: bool = False,
    exclude_unique: bool = False,
    sort_by_price: bool = False,
    offset: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """Validate optional ``getChatGifts`` filters."""
    options = {
        "exclude_unsaved": exclude_unsaved,
        "exclude_saved": exclude_saved,
        "exclude_unlimited": exclude_unlimited,
        "exclude_limited_upgradable": exclude_limited_upgradable,
        "exclude_limited_non_upgradable": exclude_limited_non_upgradable,
        "exclude_from_blockchain": exclude_from_blockchain,
        "exclude_unique": exclude_unique,
        "sort_by_price": sort_by_price,
    }
    for key, value in options.items():
        if not isinstance(value, bool):
            raise GetChatGiftsError(f"{key} must be a boolean.")

    payload: dict[str, Any] = {
        key: value for key, value in options.items() if value
    }
    if offset is not None:
        offset = offset.strip()
        if not offset:
            raise GetChatGiftsError("offset must be non-empty.")
        payload["offset"] = offset
    if limit is not None:
        if not isinstance(limit, int) or isinstance(limit, bool):
            raise GetChatGiftsError("limit must be an integer.")
        if not (GET_CHAT_GIFTS_MIN_LIMIT <= limit <= GET_CHAT_GIFTS_MAX_LIMIT):
            raise GetChatGiftsError("limit must be between 1 and 100.")
        payload["limit"] = limit
    return payload


async def perform_get_chat_gifts(
    bot: Any,
    *,
    chat_id: int | str,
    exclude_unsaved: bool = False,
    exclude_saved: bool = False,
    exclude_unlimited: bool = False,
    exclude_limited_upgradable: bool = False,
    exclude_limited_non_upgradable: bool = False,
    exclude_from_blockchain: bool = False,
    exclude_unique: bool = False,
    sort_by_price: bool = False,
    offset: str | None = None,
    limit: int | None = None,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> dict[str, Any]:
    """Fetch gifts owned by a Telegram channel chat."""
    if isinstance(chat_id, bool):
        raise GetChatGiftsError("chat_id must be an integer or @username.")
    if isinstance(chat_id, str):
        chat_id = chat_id.strip()
        if not chat_id:
            raise GetChatGiftsError("chat_id must be an integer or @username.")
    elif not isinstance(chat_id, int):
        raise GetChatGiftsError("chat_id must be an integer or @username.")

    payload = {
        "chat_id": chat_id,
        **normalize_get_chat_gifts_options(
            exclude_unsaved=exclude_unsaved,
            exclude_saved=exclude_saved,
            exclude_unlimited=exclude_unlimited,
            exclude_limited_upgradable=exclude_limited_upgradable,
            exclude_limited_non_upgradable=exclude_limited_non_upgradable,
            exclude_from_blockchain=exclude_from_blockchain,
            exclude_unique=exclude_unique,
            sort_by_price=sort_by_price,
            offset=offset,
            limit=limit,
        ),
    }
    url = _build_api_url(bot, "getChatGifts")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "get_chat_gifts_failed",
            chat_id=chat_id,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise GetChatGiftsError(f"getChatGifts request failed: {exc}") from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "get_chat_gifts_failed",
            chat_id=chat_id,
            error_code=error_code,
            error=description,
        )
        raise GetChatGiftsError(description, error_code=error_code)

    result = data.get("result")
    if not isinstance(result, dict) or not isinstance(result.get("gifts"), list):
        logger.warning(
            "get_chat_gifts_failed",
            chat_id=chat_id,
            error="unexpected result",
        )
        raise GetChatGiftsError(
            "Telegram returned an unexpected chat gifts result."
        )

    logger.info(
        "chat_gifts_fetched",
        chat_id=chat_id,
        gifts_count=len(result["gifts"]),
        has_next_offset=bool(result.get("next_offset")),
    )
    return result


def format_chat_gifts(gifts: dict[str, Any], *, chat_id: int | str) -> str:
    """Render a compact HTML admin response for ``OwnedGifts``."""
    gift_items = gifts.get("gifts", [])
    if not isinstance(gift_items, list):
        gift_items = []

    lines = [
        "<b>Chat gifts</b>",
        f"Chat: <code>{escape(str(chat_id))}</code>",
        f"Count: <code>{len(gift_items)}</code>",
    ]
    for item in gift_items[:10]:
        if not isinstance(item, dict):
            continue
        owned_gift_id = item.get("owned_gift_id")
        gift = item.get("gift") if isinstance(item.get("gift"), dict) else {}
        gift_id = gift.get("id") or item.get("gift_id") or "unknown"
        line = f"- <code>{escape(str(gift_id))}</code>"
        if owned_gift_id:
            line += f" owned=<code>{escape(str(owned_gift_id))}</code>"
        if item.get("type"):
            line += f" type=<code>{escape(str(item['type']))}</code>"
        if item.get("is_saved") is not None:
            line += f" saved=<code>{escape(str(item['is_saved']).lower())}</code>"
        lines.append(line)

    if len(gift_items) > 10:
        lines.append(f"...and <code>{len(gift_items) - 10}</code> more.")
    if gifts.get("next_offset"):
        lines.append(
            f"Next offset: <code>{escape(str(gifts['next_offset']))}</code>"
        )
    lines.append(
        "Read-only gifts fetch. Conversion, upgrade or transfer require "
        "separate explicit commands."
    )
    return "\n".join(lines)
