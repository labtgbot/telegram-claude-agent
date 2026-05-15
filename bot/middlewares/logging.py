import structlog
from aiogram import BaseMiddleware, types

logger = structlog.get_logger()

class LoggingMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        if isinstance(event, types.Message):
            user = event.from_user
            chat = event.chat
            logger.info(
                "message_received",
                user_id=user.id,
                username=user.username,
                chat_id=chat.id,
                chat_type=chat.type,
                text=event.text,
            )
        elif isinstance(event, types.CallbackQuery):
            user = event.from_user
            logger.info(
                "callback_query",
                user_id=user.id,
                data=event.data,
            )
        elif isinstance(event, types.InlineQuery):
            user = event.from_user
            logger.info(
                "inline_query",
                user_id=user.id,
                query=event.query,
            )
        else:
            logger.info("update_received", update_type=type(event).__name__)
        return await handler(event, data)