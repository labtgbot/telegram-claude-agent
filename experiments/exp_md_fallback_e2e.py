"""End-to-end proof that the plain-text FALLBACK in send_reply_safely (and the
streaming final-edit path) is ineffective because the bot's default parse_mode is
HTML and the fallback call omits parse_mode=None.

We build a real aiogram Message bound to a Bot whose default parse_mode=HTML, and
replace the bot.session with a fake that:
  * raises TelegramBadRequest when it receives HTML that overlaps tags
    (mirrors Telegram 'can't parse entities'),
  * records what was 'delivered' otherwise.
Then we call the REAL send_reply_safely from bot.handlers.chat and observe that
the user receives nothing for an LLM '***heading***' message.

Run: PYTHONPATH=. python experiments/exp_md_fallback_e2e.py
"""
import asyncio
from html.parser import HTMLParser

from aiogram import Bot, types
from aiogram.client.default import DefaultBotProperties, Default
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest

from bot.handlers.chat import md_to_html, send_reply_safely


class _Strict(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.error = None

    def handle_starttag(self, tag, attrs):
        self.stack.append(tag)

    def handle_endtag(self, tag):
        if not self.stack or self.stack[-1] != tag:
            self.error = f"overlap </{tag}> over {self.stack[-1:] or 'EMPTY'}"
        else:
            self.stack.pop()


def _telegram_rejects(html):
    p = _Strict()
    p.feed(html)
    return p.error or (f"unclosed {p.stack}" if p.stack else None)


delivered = []  # (text, effective_parse_mode)


class FakeSession:
    async def __call__(self, bot, method, timeout=None):
        text = getattr(method, "text", None)
        pm = getattr(method, "parse_mode", None)
        if isinstance(pm, Default):
            pm = getattr(bot.default, pm.name)
        # Telegram only validates entities when parse_mode is set.
        if pm in ("HTML", ParseMode.HTML) and text is not None:
            reason = _telegram_rejects(text)
            if reason:
                raise TelegramBadRequest(
                    method=method,
                    message=f"Bad Request: can't parse entities: {reason}",
                )
        delivered.append((text, str(pm)))

        class R:  # minimal fake Message response
            message_id = 999
        return R()

    async def close(self):
        pass


async def main():
    bot = Bot(token="123:abc", default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    bot.session = FakeSession()
    msg = types.Message(
        message_id=1, date=0, chat=types.Chat(id=1, type="private"),
        from_user=types.User(id=1, is_bot=False, first_name="T"), text="hi",
    ).as_(bot)

    user_md = "Here is the answer.\n\n***Important note*** about your code."
    rendered = md_to_html(user_md)
    print("LLM markdown :", repr(user_md))
    print("rendered HTML:", repr(rendered))
    print("Telegram rejects rendered? ->", _telegram_rejects(rendered))
    print()

    await send_reply_safely(msg, rendered)

    print("MESSAGES THE USER ACTUALLY RECEIVED:")
    if not delivered:
        print("   <<< NOTHING — both the HTML send and the 'plain' fallback failed >>>")
    for d in delivered:
        print("   ", d)

    await bot.session.close()


asyncio.run(main())
