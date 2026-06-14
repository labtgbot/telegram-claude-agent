from aiogram import Router
from aiogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent

from bot.config import settings

router = Router()


def _inline_user_id(query: InlineQuery) -> int | None:
    from_user = getattr(query, "from_user", None)
    return getattr(from_user, "id", None)


def _is_inline_query_allowed(query: InlineQuery) -> bool:
    allowed_ids = settings.allowed_chat_ids
    if not allowed_ids:
        return True

    # InlineQuery has no target chat; private chat ids match Telegram user ids.
    user_id = _inline_user_id(query)
    return user_id in allowed_ids


@router.inline_query()
async def handle_inline_query(query: InlineQuery):
    if not _is_inline_query_allowed(query):
        return

    # Basic inline mode: provide a simple result
    results = [
        InlineQueryResultArticle(
            id="1",
            title="Telegram Claude Agent",
            input_message_content=InputTextMessageContent(
                message_text="🤖 This bot is powered by Claude via free-claude-code.\nSend me a direct message to start chatting!"
            ),
        )
    ]
    await query.answer(results, cache_time=1)
