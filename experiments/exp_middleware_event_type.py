"""Проверка: какой тип event получает middleware на dp.update.middleware()."""
import asyncio
from aiogram import Bot, Dispatcher, BaseMiddleware, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

seen_event_types = []

class ProbeMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        seen_event_types.append(type(event).__name__)
        # эмулируем логику RateLimitMiddleware/LoggingMiddleware
        is_message = isinstance(event, types.Message)
        print(f"  middleware saw event type = {type(event).__name__}; isinstance(Message) = {is_message}")
        return await handler(event, data)

async def main():
    bot = Bot(token="123:abc", default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.update.middleware(ProbeMiddleware())  # точно как в bot/main.py

    handled = []
    @dp.message()
    async def on_message(message: types.Message):
        handled.append(message.text)
        print(f"  handler received Message text={message.text!r}")

    update = types.Update(
        update_id=1,
        message=types.Message(
            message_id=10,
            date=0,
            chat=types.Chat(id=42, type="private"),
            from_user=types.User(id=7, is_bot=False, first_name="T"),
            text="hello",
        ).as_(bot),
    )
    await dp.feed_update(bot, update)
    await bot.session.close()
    print("seen_event_types:", seen_event_types)
    print("handler invoked:", handled)

asyncio.run(main())
