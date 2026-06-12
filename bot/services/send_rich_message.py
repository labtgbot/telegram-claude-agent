from typing import Any, Optional

import httpx
import structlog

from bot.services.send_message_draft import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()


class SendRichMessageError(Exception):
    """Raised when ``sendRichMessage`` validation or the raw call fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


def validate_input_rich_message(rich_message: dict[str, Any]) -> None:
    """Validate the Bot API 10.1 ``InputRichMessage`` shape used by this app."""
    if not isinstance(rich_message, dict) or not rich_message:
        raise SendRichMessageError("rich_message must be a non-empty object.")

    has_html = "html" in rich_message
    has_markdown = "markdown" in rich_message
    if has_html == has_markdown:
        raise SendRichMessageError("rich_message must contain exactly one of html or markdown.")

    content_key = "html" if has_html else "markdown"
    content = rich_message.get(content_key)
    if not isinstance(content, str) or not content:
        raise SendRichMessageError(f"rich_message.{content_key} must be a non-empty string.")

    if "is_rtl" in rich_message and not isinstance(rich_message["is_rtl"], bool):
        raise SendRichMessageError("rich_message.is_rtl must be a boolean.")

    if "skip_entity_detection" in rich_message and not isinstance(
        rich_message["skip_entity_detection"], bool
    ):
        raise SendRichMessageError("rich_message.skip_entity_detection must be a boolean.")


async def perform_send_rich_message(
    bot: Any,
    *,
    chat_id: int | str,
    rich_message: dict[str, Any],
    business_connection_id: Optional[str] = None,
    message_thread_id: Optional[int] = None,
    direct_messages_topic_id: Optional[int] = None,
    disable_notification: Optional[bool] = None,
    protect_content: Optional[bool] = None,
    allow_paid_broadcast: Optional[bool] = None,
    message_effect_id: Optional[str] = None,
    suggested_post_parameters: Optional[dict[str, Any]] = None,
    reply_parameters: Optional[dict[str, Any]] = None,
    reply_markup: Optional[dict[str, Any]] = None,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> dict:
    """Send a Telegram Bot API 10.1 rich message through a raw HTTP call."""
    if chat_id == 0 or chat_id == "":
        raise SendRichMessageError("chat_id is required.")
    validate_input_rich_message(rich_message)

    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "rich_message": rich_message,
    }
    optional = {
        "business_connection_id": business_connection_id,
        "message_thread_id": message_thread_id,
        "direct_messages_topic_id": direct_messages_topic_id,
        "disable_notification": disable_notification,
        "protect_content": protect_content,
        "allow_paid_broadcast": allow_paid_broadcast,
        "message_effect_id": message_effect_id,
        "suggested_post_parameters": suggested_post_parameters,
        "reply_parameters": reply_parameters,
        "reply_markup": reply_markup,
    }
    payload.update({key: value for key, value in optional.items() if value is not None})
    url = _build_api_url(bot, "sendRichMessage")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "send_rich_message_failed",
            chat_id=chat_id,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise SendRichMessageError(f"sendRichMessage request failed: {exc}") from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "send_rich_message_failed",
            chat_id=chat_id,
            error_code=error_code,
            error=description,
        )
        raise SendRichMessageError(description, error_code=error_code)

    result = data.get("result") or {}
    logger.info(
        "rich_message_sent",
        chat_id=chat_id,
        sent_message_id=result.get("message_id"),
        content_format="html" if "html" in rich_message else "markdown",
    )
    return result
