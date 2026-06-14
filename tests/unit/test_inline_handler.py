from types import SimpleNamespace
from unittest.mock import AsyncMock

from bot.handlers import inline


def _inline_query(user_id: int | None = 42):
    from_user = None
    if user_id is not None:
        from_user = SimpleNamespace(id=user_id, username="tester")

    return SimpleNamespace(
        id="inline-1",
        from_user=from_user,
        query="",
        answer=AsyncMock(),
    )


async def test_inline_query_rejects_unlisted_user_when_allowlist_is_configured(
    monkeypatch,
):
    monkeypatch.setattr(inline.settings, "telegram_allowed_chat_ids", "111")
    query = _inline_query(user_id=999)

    await inline.handle_inline_query(query)

    query.answer.assert_not_awaited()


async def test_inline_query_allows_listed_private_chat_user(monkeypatch):
    monkeypatch.setattr(inline.settings, "telegram_allowed_chat_ids", "111")
    query = _inline_query(user_id=111)

    await inline.handle_inline_query(query)

    query.answer.assert_awaited_once()


async def test_inline_query_allows_open_deployments(monkeypatch):
    monkeypatch.setattr(inline.settings, "telegram_allowed_chat_ids", "")
    query = _inline_query(user_id=999)

    await inline.handle_inline_query(query)

    query.answer.assert_awaited_once()
