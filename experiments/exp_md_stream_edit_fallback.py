"""Confirm the streaming final-edit fallback path (handle_streaming) has the SAME
ineffective-fallback defect: edit_text(chunks[0][:LIMIT]) and answer(extra) both
omit parse_mode=None, so bot default HTML re-applies and the retry fails again.

We resolve the parse_mode aiogram would actually use for each fallback call.

Run: PYTHONPATH=. python experiments/exp_md_stream_edit_fallback.py
"""
import asyncio
from aiogram import Bot, types
from aiogram.client.default import DefaultBotProperties, Default
from aiogram.enums import ParseMode


async def main():
    bot = Bot(token="123:abc", default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    msg = types.Message(
        message_id=5, date=0, chat=types.Chat(id=1, type="private"),
        from_user=types.User(id=1, is_bot=False, first_name="T"), text="x",
    ).as_(bot)

    def eff(method):
        pm = getattr(method, "parse_mode", None)
        if isinstance(pm, Default):
            return getattr(bot.default, pm.name)
        return pm

    # Line 391: await sent_msg.edit_text(chunks[0][:LIMIT])  -> fallback for chunk0
    edit_fallback = msg.edit_text("<b><i>x</b></i>")
    # Line 396: await message.answer(extra)                  -> fallback for extra chunks
    answer_fallback = msg.answer("<b><i>x</b></i>")

    print("handle_streaming line 391 edit_text fallback parse_mode ->", repr(eff(edit_fallback)))
    print("handle_streaming line 396 answer  fallback parse_mode ->", repr(eff(answer_fallback)))
    print()
    print("Both resolve to HTML, so a chunk that failed HTML parsing the first")
    print("time fails the 'plain' retry the SAME way. The retry is a no-op.")
    print()
    print("Contrast: the truncated-only fallback also keeps reopened tags, e.g.")
    print("chunks[0][:LIMIT] still contains '<b><i>...' which Telegram rejects.")

    await bot.session.close()


asyncio.run(main())
