from typing import Any, Optional

import httpx
import structlog

from bot.services.send_message_draft import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()

# Telegram message-style text limit. Bot API 10.0 documents answerGuestQuery as
# returning a text answer to the guest query; keep the same upper bound used for
# ordinary Telegram messages so invalid over-long responses are rejected locally.
ANSWER_GUEST_QUERY_TEXT_LIMIT = 4096


class AnswerGuestQueryError(Exception):
    """Raised when ``answerGuestQuery`` fails validation or the raw call fails.

    The pinned ``aiogram==3.3.0`` predates Bot API 10.0 and has no typed wrapper
    for ``answerGuestQuery``, so this helper calls the raw HTTP endpoint directly.
    Validation failures and request failures are surfaced through this dedicated
    exception; ``error_code`` contains Telegram's ``error_code`` for ``ok: false``
    responses and is ``None`` for local validation or transport errors.
    """

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


async def perform_answer_guest_query(
    bot: Any,
    *,
    guest_query_id: str,
    text: str,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> bool:
    """Answer a Telegram Guest Mode query via raw Bot API ``answerGuestQuery``.

    Guest Mode lets a bot answer a ``guest_message`` without being a member of
    the chat. Telegram provides ``Message.guest_query_id`` on such updates; this
    helper sends the final Claude response back through ``answerGuestQuery``.
    The method requires a non-empty ``guest_query_id`` and response ``text`` and
    returns ``True`` on success.

    Because operator/user content may be present in ``text``, logs include only
    structural metadata such as the query id and text length, never the text.
    """
    if not guest_query_id:
        raise AnswerGuestQueryError("guest_query_id is required.")

    if not text:
        raise AnswerGuestQueryError("text is required.")

    if len(text) > ANSWER_GUEST_QUERY_TEXT_LIMIT:
        raise AnswerGuestQueryError(
            f"Guest query answer is too long: {len(text)} characters "
            f"(max {ANSWER_GUEST_QUERY_TEXT_LIMIT})."
        )

    payload = {
        "guest_query_id": guest_query_id,
        "text": text,
    }
    url = _build_api_url(bot, "answerGuestQuery")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "answer_guest_query_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            guest_query_id=guest_query_id,
        )
        raise AnswerGuestQueryError(
            f"answerGuestQuery request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description = data.get("description", "unknown error")
        logger.warning(
            "answer_guest_query_failed",
            error_code=error_code,
            error=description,
            guest_query_id=guest_query_id,
        )
        raise AnswerGuestQueryError(description, error_code=error_code)

    result = data.get("result", True)
    logger.info(
        "guest_query_answered",
        guest_query_id=guest_query_id,
        text_length=len(text),
    )
    return result
