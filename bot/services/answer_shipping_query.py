from typing import NoReturn, Optional

import structlog

logger = structlog.get_logger()


ANSWER_SHIPPING_QUERY_BLOCK_REASON = (
    "answerShippingQuery is blocked by product scope: telegram-claude-agent "
    "does not sell physical goods, does not request shipping addresses, and "
    "has no shipping-options catalog to validate."
)


class AnswerShippingQueryBlockedByProductError(Exception):
    """Raised when product scope does not allow answering shipping queries."""

    def __init__(self, message: str = ANSWER_SHIPPING_QUERY_BLOCK_REASON):
        super().__init__(message)
        self.message = message


def explain_answer_shipping_query_status() -> str:
    """Return the product decision for ``answerShippingQuery`` support."""
    return ANSWER_SHIPPING_QUERY_BLOCK_REASON


async def perform_answer_shipping_query(
    *,
    shipping_query_id: str,
    ok: bool,
    shipping_options: Optional[list[dict]] = None,
    error_message: Optional[str] = None,
) -> NoReturn:
    """Reject ``answerShippingQuery`` until a physical-goods flow is designed."""
    logger.info(
        "answer_shipping_query_blocked_by_product",
        has_shipping_query_id=bool(shipping_query_id),
        ok=ok,
        shipping_options_count=len(shipping_options or []),
        has_error_message=bool(error_message),
    )
    raise AnswerShippingQueryBlockedByProductError()
