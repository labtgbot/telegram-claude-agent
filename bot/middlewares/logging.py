import structlog
from aiogram import BaseMiddleware, types

logger = structlog.get_logger()

class LoggingMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        if isinstance(event, types.Message):
            # ``from_user`` is None for channel posts, anonymous group admins
            # and automatic forwards. Guard against it so the middleware logs
            # what it can instead of crashing with AttributeError and dropping
            # the update before any handler runs.
            user = event.from_user
            chat = event.chat
            logger.info(
                "message_received",
                user_id=user.id if user else None,
                username=user.username if user else None,
                chat_id=chat.id if chat else None,
                chat_type=chat.type if chat else None,
                text=event.text,
            )
        elif isinstance(event, types.CallbackQuery):
            user = event.from_user
            logger.info(
                "callback_query",
                user_id=user.id if user else None,
                data=event.data,
            )
        elif isinstance(event, types.InlineQuery):
            user = event.from_user
            logger.info(
                "inline_query",
                user_id=user.id if user else None,
                query=event.query,
            )
        else:
            logger.info("update_received", update_type=type(event).__name__)
        return await handler(event, data)
