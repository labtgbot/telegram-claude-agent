import asyncio
import structlog
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.types import Update

from bot.config import settings
from bot.handlers.commands import router as commands_router
from bot.handlers.chat import router as chat_router
from bot.handlers.inline import router as inline_router
from bot.middlewares.logging import LoggingMiddleware
from bot.middlewares.rate_limit import RateLimitMiddleware
from bot.utils.storage import storage

# Logging configuration
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ]
)

app = FastAPI(title="Telegram Claude Agent")
bot = Bot(token=settings.telegram_bot_token, parse_mode=ParseMode.HTML)
dp = Dispatcher()

# Register middlewares
dp.update.middleware(LoggingMiddleware())
dp.update.middleware(RateLimitMiddleware(settings.rate_limit_requests_per_minute))

# Register routers
dp.include_router(commands_router)
dp.include_router(chat_router)
dp.include_router(inline_router)

polling_task = None

@app.on_event("startup")
async def on_startup():
    global polling_task
    # Ensure bot username is cached
    await bot.get_me()
    if settings.telegram_webhook_url:
        await bot.set_webhook(
            url=settings.telegram_webhook_url,
            secret_token=settings.api_secret_token,
        )
    else:
        # Start polling in background task
        polling_task = asyncio.create_task(dp.start_polling(bot, skip_updates=True))

@app.on_event("shutdown")
async def on_shutdown():
    global polling_task
    if polling_task:
        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            pass
    await bot.session.close()

@app.post("/webhook")
async def telegram_webhook(request: Request):
    if settings.api_secret_token:
        header_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if header_token != settings.api_secret_token:
            raise HTTPException(status_code=403, detail="Invalid secret token")
    try:
        update_data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    update = Update.model_validate(update_data)
    await dp.feed_update(bot, update)
    return JSONResponse({"status": "ok"})

@app.get("/health")
async def health_check():
    return {"status": "ok"}