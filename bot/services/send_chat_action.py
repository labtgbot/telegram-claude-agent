import asyncio
import contextlib
from typing import Any, AsyncIterator, Optional

import structlog
from aiogram.exceptions import (
    TelegramAPIError,
    TelegramNetworkError,
    TelegramRetryAfter,
    TelegramServerError,
)

logger = structlog.get_logger()

# The status indicators Telegram accepts for ``sendChatAction`` in the pinned
# ``aiogram==3.3.0`` (Bot API 7.0) typed wrapper. ``typing`` shows "typing…",
# the ``upload_*``/``record_*`` actions show the matching media hint and
# ``choose_sticker``/``find_location`` cover the remaining cases.
CHAT_ACTIONS = (
    "typing",
    "upload_photo",
    "record_video",
    "upload_video",
    "record_voice",
    "upload_voice",
    "upload_document",
    "choose_sticker",
    "find_location",
    "record_video_note",
    "upload_video_note",
)

# Telegram clears a chat action after about five seconds, so refresh it a little
# sooner to keep the indicator visible while a long-running request is handled.
CHAT_ACTION_REFRESH_SECONDS = 4.5

_RETRYABLE_CHAT_ACTION_ERRORS: tuple[type[TelegramAPIError], ...] = (
    TelegramNetworkError,
    TelegramRetryAfter,
    TelegramServerError,
)


class SendChatActionError(ValueError):
    """Raised when ``sendChatAction`` is asked to show an unsupported action.

    The Telegram method only accepts the fixed set of status strings in
    :data:`CHAT_ACTIONS`; this dedicated exception lets callers reject an
    unknown action before any Telegram request is made.
    """


async def perform_send_chat_action(
    bot: Any,
    *,
    chat_id: int,
    action: str = "typing",
    message_thread_id: Optional[int] = None,
    business_connection_id: Optional[str] = None,
) -> bool:
    """Show a chat action (e.g. "typing…") in a chat via the typed aiogram API.

    Calls the typed aiogram ``Bot.send_chat_action()`` wrapper for the Telegram
    ``sendChatAction`` method so the bot can tell the user it is busy — for
    example showing "typing…" while Claude/proxy handles a noticeably long
    request — instead of leaving the chat silent. The Telegram method requires
    ``chat_id`` and ``action`` and returns ``True`` on success; the status is
    cleared automatically after about five seconds or as soon as the bot sends a
    message. ``action`` must be one of :data:`CHAT_ACTIONS` and an unsupported
    value is rejected with :class:`SendChatActionError` before any request is
    made. ``message_thread_id`` targets a specific forum topic and
    ``business_connection_id`` sends the action on behalf of a business
    connection; both are the optional parameters available in the pinned
    ``aiogram==3.3.0`` (Bot API 7.0) typed wrapper.

    The action carries no operator-provided content, so the chosen action, the
    chat and whether a forum topic or business connection was targeted are
    logged.
    """
    if action not in CHAT_ACTIONS:
        raise SendChatActionError(
            f"Unsupported chat action: {action!r}. "
            f"Use one of: {', '.join(CHAT_ACTIONS)}."
        )

    try:
        result = await bot.send_chat_action(
            chat_id=chat_id,
            action=action,
            message_thread_id=message_thread_id,
            business_connection_id=business_connection_id,
        )
    except TelegramAPIError as exc:
        logger.warning(
            "send_chat_action_failed",
            error_type=type(exc).__name__,
            error=str(exc),
            chat_id=chat_id,
            action=action,
        )
        raise

    logger.info(
        "chat_action_sent",
        chat_id=chat_id,
        action=action,
        has_thread=message_thread_id is not None,
        has_business_connection=business_connection_id is not None,
    )
    return result


def _is_retryable_chat_action_error(exc: TelegramAPIError) -> bool:
    return isinstance(exc, _RETRYABLE_CHAT_ACTION_ERRORS)


@contextlib.asynccontextmanager
async def keep_chat_action(
    bot: Any,
    *,
    chat_id: int,
    action: str = "typing",
    message_thread_id: Optional[int] = None,
    business_connection_id: Optional[str] = None,
    refresh_seconds: float = CHAT_ACTION_REFRESH_SECONDS,
) -> AsyncIterator[None]:
    """Keep a chat action visible while a long-running block runs.

    Sends ``action`` immediately and then refreshes it every ``refresh_seconds``
    until the ``async with`` block exits, because Telegram clears the indicator
    after about five seconds. This is the intended use for showing "typing…"
    while Claude/proxy processes a request. Telegram API errors raised while
    refreshing are logged (in :func:`perform_send_chat_action`) and swallowed so
    a transient failure to display the indicator never breaks the request being
    handled. Permanent Telegram errors stop the refresher because the same call
    cannot succeed on the next interval. The background refresh task is always
    cancelled when the block exits.
    """

    async def _runner() -> None:
        while True:
            try:
                await perform_send_chat_action(
                    bot,
                    chat_id=chat_id,
                    action=action,
                    message_thread_id=message_thread_id,
                    business_connection_id=business_connection_id,
                )
            except TelegramAPIError as exc:
                # Already logged by perform_send_chat_action. Keep retrying only
                # for temporary Telegram/API transport failures.
                if not _is_retryable_chat_action_error(exc):
                    break
            await asyncio.sleep(refresh_seconds)

    task = asyncio.create_task(_runner())
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
