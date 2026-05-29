import pytest

from bot.services.answer_shipping_query import (
    ANSWER_SHIPPING_QUERY_BLOCK_REASON,
    AnswerShippingQueryBlockedByProductError,
    explain_answer_shipping_query_status,
    perform_answer_shipping_query,
)


def test_explain_answer_shipping_query_status_documents_product_block():
    status = explain_answer_shipping_query_status()

    assert status == ANSWER_SHIPPING_QUERY_BLOCK_REASON
    assert "blocked by product scope" in status
    assert "physical goods" in status
    assert "shipping-options catalog" in status


async def test_perform_answer_shipping_query_is_blocked_before_telegram_call():
    with pytest.raises(AnswerShippingQueryBlockedByProductError) as excinfo:
        await perform_answer_shipping_query(
            shipping_query_id="shipping-query-1",
            ok=True,
            shipping_options=[
                {
                    "id": "standard",
                    "title": "Standard delivery",
                    "prices": [{"label": "Delivery", "amount": 100}],
                }
            ],
        )

    assert str(excinfo.value) == ANSWER_SHIPPING_QUERY_BLOCK_REASON


async def test_perform_answer_shipping_query_error_path_is_also_blocked():
    with pytest.raises(AnswerShippingQueryBlockedByProductError):
        await perform_answer_shipping_query(
            shipping_query_id="shipping-query-1",
            ok=False,
            error_message="Shipping is unavailable.",
        )
