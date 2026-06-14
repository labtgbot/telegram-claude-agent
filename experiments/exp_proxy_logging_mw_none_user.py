"""
EXPERIMENT: LoggingMiddleware crashes on Message with from_user=None.

bot/middlewares/logging.py:
    if isinstance(event, types.Message):
        user = event.from_user
        chat = event.chat
        logger.info("message_received", user_id=user.id, username=user.username, ...)

For several real Telegram update kinds, Message.from_user is None:
  - channel posts (chat.type == "channel")
  - anonymous group admins (sender is the group itself)
  - Guest Mode `guest_message` updates can also lack a from_user in some shapes
  - automatic forwards

If from_user is None, `user.id` raises AttributeError. The middleware is the
OUTERMOST layer, so an exception here means the update is never dispatched to
ANY handler. We construct a real aiogram Message with from_user=None and run the
real middleware to see whether it raises.
"""
import asyncio

from aiogram import types
from bot.middlewares.logging import LoggingMiddleware


async def passthrough(event, data):
    return "handler-ran"


async def main():
    mw = LoggingMiddleware()

    # Build a minimal but VALID aiogram Message with from_user = None.
    # channel_post-style: chat is a channel, no from_user.
    msg = types.Message.model_construct(
        message_id=1,
        date=0,
        chat=types.Chat.model_construct(id=-1001234567890, type="channel"),
        from_user=None,
        text="hello from a channel/anon admin",
    )

    print("from_user is:", msg.from_user)
    try:
        result = await mw(passthrough, msg, {})
        print("middleware returned:", result)
        print(">>> RESULT: no crash (from_user handled).")
    except Exception as exc:
        print(f">>> RESULT: LoggingMiddleware RAISED {type(exc).__name__}: {exc}")
        print(">>> => Any Message update with from_user=None (channel post, anonymous")
        print(">>>    admin, certain guest updates) crashes the outermost middleware,")
        print(">>>    so the update is dropped and no handler runs.")


if __name__ == "__main__":
    asyncio.run(main())
