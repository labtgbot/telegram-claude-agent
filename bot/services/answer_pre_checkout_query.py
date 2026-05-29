from typing import Any, Optional

import httpx
import structlog

from bot.services.send_checklist import DEFAULT_REQUEST_TIMEOUT, _build_api_url

logger = structlog.get_logger()


class AnswerPreCheckoutQueryError(Exception):
    """Raised when the raw ``answerPreCheckoutQuery`` Bot API call fails."""

    def __init__(self, message: str, *, error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


async def perform_answer_pre_checkout_query(
    bot: Any,
    *,
    pre_checkout_query_id: str,
    ok: bool,
    error_message: Optional[str] = None,
    request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
) -> bool:
    """Answer a Telegram pre-checkout query through a raw Bot API helper."""
    if not ok and not error_message:
        raise AnswerPreCheckoutQueryError(
            "error_message is required when rejecting a pre-checkout query."
        )

    request_payload: dict[str, Any] = {
        "pre_checkout_query_id": pre_checkout_query_id,
        "ok": ok,
    }
    if error_message is not None:
        request_payload["error_message"] = error_message

    url = _build_api_url(bot, "answerPreCheckoutQuery")

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(url, json=request_payload)
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "answer_pre_checkout_query_failed",
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise AnswerPreCheckoutQueryError(
            f"answerPreCheckoutQuery request failed: {exc}"
        ) from exc

    if not data.get("ok"):
        error_code = data.get("error_code")
        description_text = data.get("description", "unknown error")
        logger.warning(
            "answer_pre_checkout_query_failed",
            error_code=error_code,
            error=description_text,
        )
        raise AnswerPreCheckoutQueryError(
            description_text,
            error_code=error_code,
        )

    result = bool(data.get("result"))
    logger.info(
        "pre_checkout_query_answered",
        ok=ok,
        has_error_message=error_message is not None,
        result=result,
    )
    return result
