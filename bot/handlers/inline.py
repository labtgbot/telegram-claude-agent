from aiogram import Router
from aiogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent

router = Router()

@router.inline_query()
async def handle_inline_query(query: InlineQuery):
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