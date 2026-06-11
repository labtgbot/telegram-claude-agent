import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Awaitable, Callable

import structlog
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Update
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from bot.config import settings
from bot.handlers.commands import router as commands_router
from bot.handlers.callbacks import router as callbacks_router
from bot.handlers.chat import router as chat_router
from bot.handlers.inline import router as inline_router
from bot.middlewares.logging import LoggingMiddleware
from bot.middlewares.rate_limit import RateLimitMiddleware
from bot.services.get_my_name import audit_configured_bot_name
from bot.services.get_my_description import audit_configured_bot_description
from bot.services.get_my_short_description import (
    audit_configured_bot_short_description,
)
from bot.services.get_my_default_administrator_rights import (
    audit_configured_my_default_administrator_rights,
)
from bot.services.set_my_description import sync_configured_bot_description
from bot.services.set_my_name import sync_configured_bot_name
from bot.services.set_my_short_description import sync_configured_bot_short_description
from bot.services.set_my_default_administrator_rights import (
    parse_default_administrator_rights_configured,
    sync_configured_my_default_administrator_rights,
)
from bot.handlers.commands import _default_administrator_rights_for_preset

# Logging configuration
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ]
)
logger = structlog.get_logger()

POLLING_RETRY_BASE_DELAY_SECONDS = 1
POLLING_RETRY_MAX_DELAY_SECONDS = 60
SleepCallable = Callable[[float], Awaitable[None]]


@dataclass
class PollingSupervisorState:
    mode: str = "polling"
    status: str = "not_started"
    consecutive_failures: int = 0
    last_error: str | None = None
    retry_delay_seconds: float | None = None

    @property
    def ready(self) -> bool:
        if self.mode == "webhook":
            return True
        return self.status == "running"

    def reset(self) -> None:
        self.mode = "polling"
        self.status = "not_started"
        self.consecutive_failures = 0
        self.last_error = None
        self.retry_delay_seconds = None

    def mark_webhook(self) -> None:
        self.mode = "webhook"
        self.status = "disabled"
        self.consecutive_failures = 0
        self.last_error = None
        self.retry_delay_seconds = None

    def mark_running(self) -> None:
        self.mode = "polling"
        self.status = "running"
        self.retry_delay_seconds = None

    def mark_degraded(self, error: str, *, retry_delay_seconds: float) -> None:
        self.mode = "polling"
        self.status = "degraded"
        self.consecutive_failures += 1
        self.last_error = error
        self.retry_delay_seconds = retry_delay_seconds

    def mark_stopped(self) -> None:
        self.status = "stopped"
        self.retry_delay_seconds = None

    def snapshot(self) -> dict:
        return {
            "mode": self.mode,
            "status": self.status,
            "consecutive_failures": self.consecutive_failures,
            "last_error": self.last_error,
            "retry_delay_seconds": self.retry_delay_seconds,
        }


@asynccontextmanager
async def lifespan(_: FastAPI):
    await on_startup()
    try:
        yield
    finally:
        await on_shutdown()


app = FastAPI(title="Telegram Claude Agent", lifespan=lifespan)
bot = Bot(
    token=settings.telegram_bot_token,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher()

# Register middlewares
dp.update.middleware(LoggingMiddleware())
dp.update.middleware(RateLimitMiddleware(settings.rate_limit_requests_per_minute))

# Register routers
dp.include_router(commands_router)
dp.include_router(callbacks_router)
dp.include_router(chat_router)
dp.include_router(inline_router)

polling_task = None
polling_state = PollingSupervisorState()


def _exception_message(exc: Exception) -> str:
    return str(exc) or exc.__class__.__name__


async def _ensure_bot_identity_cached(telegram_bot: Bot):
    try:
        return await telegram_bot.get_me()
    except Exception as exc:
        logger.error(
            "telegram_bot_startup_validation_failed",
            error=_exception_message(exc),
        )
        raise RuntimeError("Failed to validate Telegram bot token during startup") from exc


async def _run_supervised_polling(
    dispatcher: Dispatcher,
    telegram_bot: Bot,
    *,
    sleep: SleepCallable = asyncio.sleep,
    base_delay_seconds: float = POLLING_RETRY_BASE_DELAY_SECONDS,
    max_delay_seconds: float = POLLING_RETRY_MAX_DELAY_SECONDS,
) -> None:
    retry_delay_seconds = base_delay_seconds
    try:
        while True:
            polling_state.mark_running()
            try:
                logger.info("polling_started")
                await dispatcher.start_polling(telegram_bot, skip_updates=True)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                error = _exception_message(exc)
                polling_state.mark_degraded(error, retry_delay_seconds=retry_delay_seconds)
                logger.exception(
                    "polling_failed",
                    error=error,
                    retry_delay_seconds=retry_delay_seconds,
                )
            else:
                error = "start_polling returned unexpectedly"
                polling_state.mark_degraded(error, retry_delay_seconds=retry_delay_seconds)
                logger.error(
                    "polling_stopped_unexpectedly",
                    retry_delay_seconds=retry_delay_seconds,
                )

            await sleep(retry_delay_seconds)
            retry_delay_seconds = min(retry_delay_seconds * 2, max_delay_seconds)
    except asyncio.CancelledError:
        polling_state.mark_stopped()
        logger.info("polling_supervisor_cancelled")
        raise


async def on_startup():
    global polling_task
    # Ensure bot username is cached
    await _ensure_bot_identity_cached(bot)
    await sync_configured_bot_name(
        bot,
        name=settings.telegram_bot_name,
        language_code=settings.telegram_bot_name_language_code,
    )
    await audit_configured_bot_name(
        bot,
        language_code=settings.telegram_bot_name_language_code,
    )
    await sync_configured_bot_short_description(
        bot,
        short_description=settings.telegram_bot_short_description,
        language_code=settings.telegram_bot_short_description_language_code,
    )
    await audit_configured_bot_short_description(
        bot,
        language_code=settings.telegram_bot_short_description_language_code,
    )
    await sync_configured_bot_description(
        bot,
        description=settings.telegram_bot_description,
        language_code=settings.telegram_bot_description_language_code,
    )
    await audit_configured_bot_description(
        bot,
        language_code=settings.telegram_bot_description_language_code,
    )
    await sync_configured_my_default_administrator_rights(
        bot,
        rights=_default_administrator_rights_for_preset(
            settings.telegram_bot_default_administrator_rights or ""
        ),
        for_channels=settings.telegram_bot_default_administrator_rights_for_channels,
        configured=parse_default_administrator_rights_configured(
            settings.telegram_bot_default_administrator_rights
        ),
    )
    await audit_configured_my_default_administrator_rights(
        bot,
        for_channels=settings.telegram_bot_default_administrator_rights_for_channels,
    )
    if settings.telegram_webhook_url:
        await bot.set_webhook(
            url=settings.telegram_webhook_url,
            secret_token=settings.api_secret_token,
        )
        polling_state.mark_webhook()
    else:
        polling_state.mark_running()
        polling_task = asyncio.create_task(_run_supervised_polling(dp, bot))


async def on_shutdown():
    global polling_task
    if polling_task:
        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            pass
        polling_task = None
    await bot.session.close()

@app.post("/webhook")
async def telegram_webhook(request: Request):
    # The secret token is mandatory: without it the endpoint cannot prove that
    # an update genuinely originates from Telegram, so reject every request
    # instead of silently feeding unauthenticated updates into the dispatcher.
    if not settings.api_secret_token:
        raise HTTPException(status_code=403, detail="Webhook secret token not configured")
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
    ready = polling_state.ready
    return JSONResponse(
        {
            "status": "ok" if ready else "degraded",
            "polling": polling_state.snapshot(),
        },
        status_code=200 if ready else 503,
    )
