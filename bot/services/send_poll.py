from typing import Any, Optional

import httpx
import structlog

from bot.services.send_message_draft import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()

PollOptionInput = str | dict[str, Any]


class SendPollError(Exception):
    """Raised when ``sendPoll`` validation or the raw call fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


def _normalize_poll_options(options: list[PollOptionInput]) -> list[dict[str, Any]]:
    if not options:
        raise SendPollError("options must not be empty.")

    normalized = []
    for option in options:
        if isinstance(option, str):
            if not option:
                raise SendPollError("option text must be non-empty.")
            normalized.append({"text": option})
            continue

        if not isinstance(option, dict):
            raise SendPollError("each option must be a string or object.")

        text = option.get("text")
        if not isinstance(text, str) or not text:
            raise SendPollError("option.text must be a non-empty string.")
        normalized.append(dict(option))

    return normalized


async def perform_send_poll(
    bot: Any,
    *,
    chat_id: int | str,
    question: str,
    options: list[PollOptionInput],
    is_anonymous: Optional[bool] = None,
    type: Optional[str] = None,
    allows_multiple_answers: Optional[bool] = None,
    correct_option_id: Optional[int] = None,
    explanation: Optional[str] = None,
    open_period: Optional[int] = None,
    close_date: Optional[Any] = None,
    is_closed: Optional[bool] = None,
    message_thread_id: Optional[int] = None,
    disable_notification: Optional[bool] = None,
    protect_content: Optional[bool] = None,
    business_connection_id: Optional[str] = None,
    question_parse_mode: Optional[str] = None,
    question_entities: Optional[list[dict[str, Any]]] = None,
    allows_revoting: Optional[bool] = None,
    shuffle_options: Optional[bool] = None,
    allow_adding_options: Optional[bool] = None,
    hide_results_until_closes: Optional[bool] = None,
    members_only: Optional[bool] = None,
    country_codes: Optional[list[str]] = None,
    correct_option_ids: Optional[list[int]] = None,
    explanation_parse_mode: Optional[str] = None,
    explanation_entities: Optional[list[dict[str, Any]]] = None,
    explanation_media: Optional[dict[str, Any]] = None,
    description: Optional[str] = None,
    description_parse_mode: Optional[str] = None,
    description_entities: Optional[list[dict[str, Any]]] = None,
    media: Optional[dict[str, Any]] = None,
    allow_paid_broadcast: Optional[bool] = None,
    message_effect_id: Optional[str] = None,
    reply_parameters: Optional[dict[str, Any]] = None,
    reply_markup: Optional[dict[str, Any]] = None,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> Any:
    """Send a native poll using the current raw Telegram Bot API payload.

    The pinned aiogram dependency can lag behind Telegram Bot API poll changes.
    This helper therefore posts directly to ``sendPoll`` and normalizes simple
    string options into Bot API 10.x ``InputPollOption`` objects. Callers that
    need option media, including Bot API 10.1 ``InputMediaLink``, may pass full
    option dictionaries.
    """
    if chat_id == 0 or chat_id == "":
        raise SendPollError("chat_id is required.")
    if not question:
        raise SendPollError("question is required.")

    normalized_options = _normalize_poll_options(options)
    if correct_option_ids is None and correct_option_id is not None:
        correct_option_ids = [correct_option_id]

    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "question": question,
        "options": normalized_options,
    }
    optional = {
        "business_connection_id": business_connection_id,
        "message_thread_id": message_thread_id,
        "question_parse_mode": question_parse_mode,
        "question_entities": question_entities,
        "is_anonymous": is_anonymous,
        "type": type,
        "allows_multiple_answers": allows_multiple_answers,
        "allows_revoting": allows_revoting,
        "shuffle_options": shuffle_options,
        "allow_adding_options": allow_adding_options,
        "hide_results_until_closes": hide_results_until_closes,
        "members_only": members_only,
        "country_codes": country_codes,
        "correct_option_ids": correct_option_ids,
        "explanation": explanation,
        "explanation_parse_mode": explanation_parse_mode,
        "explanation_entities": explanation_entities,
        "explanation_media": explanation_media,
        "open_period": open_period,
        "close_date": close_date,
        "is_closed": is_closed,
        "description": description,
        "description_parse_mode": description_parse_mode,
        "description_entities": description_entities,
        "media": media,
        "disable_notification": disable_notification,
        "protect_content": protect_content,
        "allow_paid_broadcast": allow_paid_broadcast,
        "message_effect_id": message_effect_id,
        "reply_parameters": reply_parameters,
        "reply_markup": reply_markup,
    }
    payload.update({key: value for key, value in optional.items() if value is not None})
    url = _build_api_url(bot, "sendPoll")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "send_poll_failed",
            error_type=exc.__class__.__name__,
            error=str(exc),
            chat_id=chat_id,
        )
        raise SendPollError(f"sendPoll request failed: {exc}") from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "send_poll_failed",
            error_code=error_code,
            error=description,
            chat_id=chat_id,
        )
        raise SendPollError(description, error_code=error_code)

    result = data.get("result") or {}
    logger.info(
        "poll_sent",
        chat_id=chat_id,
        option_count=len(normalized_options),
        is_quiz=type == "quiz",
        has_option_media=any("media" in option for option in normalized_options),
        sent_message_id=getattr(result, "message_id", None)
        if not isinstance(result, dict)
        else result.get("message_id"),
    )
    return result
