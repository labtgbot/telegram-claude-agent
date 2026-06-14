"""Проверка: какой parse_mode применяется к edit_text() без явного аргумента,
когда у бота default parse_mode = HTML (как в bot/main.py)."""
import asyncio
from aiogram import Bot, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

async def main():
    bot = Bot(token="123:abc", default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    # Имитируем sent_msg из handle_streaming
    msg = types.Message(
        message_id=10, date=0,
        chat=types.Chat(id=42, type="private"),
        from_user=types.User(id=7, is_bot=False, first_name="T"),
        text="…",
    ).as_(bot)

    raw_stream_text = "Here is code: if a < b and b > c: print('x & y')"
    method = msg.edit_text(raw_stream_text)  # как в _try_edit_stream_preview (без parse_mode)
    # Резолвим дефолты бота, как это делает session при отправке
    resolved = bot.session.check_response  # noqa
    pm = method.parse_mode
    print("method.parse_mode (до резолва) =", repr(pm))
    # Эмулируем применение дефолтов бота
    from aiogram.client.default import Default
    if isinstance(pm, Default):
        effective = getattr(bot.default, pm.name)
        print("effective parse_mode (после применения bot.default) =", repr(effective))
    print("Текст, отправляемый в Telegram c parse_mode=HTML:", repr(raw_stream_text))
    print("Содержит '<' без экранирования →", "<" in raw_stream_text)
    print(">>> Telegram отклонит это как 'can't parse entities' (Unsupported start tag)")

    await bot.session.close()

asyncio.run(main())
