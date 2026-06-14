"""Проверка реальных RateLimitMiddleware и LoggingMiddleware из репозитория,
подключённых через dp.update.middleware() как в bot/main.py."""
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.middlewares.logging import LoggingMiddleware
from bot.middlewares.rate_limit import RateLimitMiddleware

def make_update(bot, uid, text, update_id):
    return types.Update(
        update_id=update_id,
        message=types.Message(
            message_id=update_id,
            date=0,
            chat=types.Chat(id=uid, type="private"),
            from_user=types.User(id=uid, is_bot=False, first_name="T"),
            text=text,
        ).as_(bot),
    )

async def main():
    bot = Bot(token="123:abc", default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    rl = RateLimitMiddleware(requests_per_minute=2)  # лимит 2/мин
    dp.update.middleware(LoggingMiddleware())
    dp.update.middleware(rl)

    handled = []
    @dp.message()
    async def on_message(message: types.Message):
        handled.append(message.text)

    # Отправляем 5 сообщений от одного пользователя при лимите 2/мин
    for i in range(5):
        await dp.feed_update(bot, make_update(bot, 7, f"msg{i}", 100 + i))

    await bot.session.close()
    print("RATE LIMIT = 2/min, отправлено 5 сообщений от одного user")
    print("Обработано хендлером:", handled)
    print("Сколько user_id попало в rate-limiter state:", dict(rl.user_timestamps))
    print()
    if len(handled) == 5:
        print(">>> BUG ПОДТВЕРЖДЁН: rate-limiter НЕ сработал ни разу (все 5 прошли).")
    else:
        print(">>> Rate-limiter сработал, обработано:", len(handled))

asyncio.run(main())
