"""
EXPERIMENT: What object type does a `dp.update.middleware` actually receive,
and does the from_user=None crash happen via the real dispatcher path?

main.py registers:
    dp.update.middleware(LoggingMiddleware())

The `dp.update` observer wraps the *outermost* layer and is invoked with the
Update object on aiogram 3.x... or is it the Message? We must verify empirically,
because:
  - If it receives `Update`, then `isinstance(event, types.Message)` is False and
    the whole message-logging branch (incl. user.id) is DEAD for messages.
  - If it receives `Message`, the from_user=None AttributeError is live.

We feed a real Update (with a channel-style message, from_user=None) through a
real Dispatcher.feed_update so the exact production wiring is exercised.
"""
import asyncio
from datetime import datetime, timezone

from aiogram import Bot, Dispatcher, Router, types
from aiogram.client.default import DefaultBotProperties

from bot.middlewares.logging import LoggingMiddleware


seen_types = []


async def main():
    dp = Dispatcher()
    dp.update.middleware(LoggingMiddleware())

    router = Router()

    @router.message()
    async def any_message(message: types.Message):
        seen_types.append(("handler", type(message).__name__))
        return "ok"

    dp.include_router(router)

    bot = Bot(token="123:abc", default=DefaultBotProperties())

    # Patch LoggingMiddleware to record the event type it receives.
    orig_call = LoggingMiddleware.__call__

    async def spy_call(self, handler, event, data):
        seen_types.append(("middleware", type(event).__name__))
        return await orig_call(self, handler, event, data)

    LoggingMiddleware.__call__ = spy_call

    # A channel post-style message: from_user is None.
    update = types.Update.model_construct(
        update_id=1,
        message=types.Message.model_construct(
            message_id=1,
            date=datetime.now(timezone.utc),
            chat=types.Chat.model_construct(id=-100123, type="channel"),
            from_user=None,
            text="hi",
        ),
    )

    print("Feeding update with message.from_user =", update.message.from_user)
    try:
        result = await dp.feed_update(bot, update)
        print("feed_update result:", result)
    except Exception as exc:
        print(f">>> feed_update raised: {type(exc).__name__}: {exc}")
    finally:
        LoggingMiddleware.__call__ = orig_call
        await bot.session.close()

    print("Observed event types:", seen_types)
    mw_types = [t for kind, t in seen_types if kind == "middleware"]
    handler_ran = any(kind == "handler" for kind, _ in seen_types)
    print()
    print(f"Middleware received: {mw_types}")
    print(f"Handler ran: {handler_ran}")
    if mw_types == ["Update"]:
        print(">>> The middleware receives an `Update`, so isinstance(event, Message)")
        print(">>> is FALSE: the message-logging branch (and user.id) is DEAD code for")
        print(">>> messages. No crash, but ALSO no per-message logging despite intent.")
    elif "Message" in mw_types:
        print(">>> The middleware receives a `Message`; the from_user=None path is LIVE.")


if __name__ == "__main__":
    asyncio.run(main())
