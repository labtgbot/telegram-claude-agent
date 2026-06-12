import structlog
from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.types import CallbackQuery

from bot.config import settings
from bot.services.answer_callback_query import perform_answer_callback_query
from bot.services.close import perform_close
from bot.services.log_out import perform_log_out
from bot.utils.admin_auth import is_admin_action_allowed as check_admin_action_allowed
from bot.utils.storage import storage
from bot.utils.user_errors import format_user_error, log_user_error_context

router = Router()
logger = structlog.get_logger()

CALLBACK_SETTINGS_REFRESH = "settings:refresh"
CALLBACK_MODEL_PREFIX = "model:set:"
CALLBACK_CLEAR_HISTORY = "history:clear"
CALLBACK_LOGOUT_CONFIRM = "admin:logout:confirm"
CALLBACK_CLOSE_CONFIRM = "admin:close:confirm"
CALLBACK_CANCEL = "action:cancel"


async def _ack(query: CallbackQuery, text: str | None = None, *, show_alert: bool = False):
    try:
        await perform_answer_callback_query(
            query.bot,
            callback_query_id=query.id,
            text=text,
            show_alert=show_alert,
        )
    except TelegramAPIError:
        logger.warning(
            "callback_query_ack_failed",
            callback_query_id=query.id,
            data=query.data,
        )


def _is_admin_action_allowed(chat_id: int, user_id: int | None = None) -> bool:
    return check_admin_action_allowed(
        chat_id=chat_id,
        user_id=user_id,
        admin_chat_ids=settings.admin_chat_ids,
        admin_user_ids=settings.admin_user_ids,
    )


def _callback_user_id(query: CallbackQuery) -> int | None:
    from_user = getattr(query, "from_user", None)
    return getattr(from_user, "id", None)


async def _answer_operation_failed(
    query: CallbackQuery, summary: str, exc: Exception
) -> None:
    log_user_error_context(
        logger,
        "callback_handler_failed",
        exc,
        callback_query_id=query.id,
        data=query.data,
        chat_id=getattr(query.message.chat, "id", None) if query.message else None,
        operation=summary,
    )
    if query.message:
        await query.message.answer(format_user_error(summary))


@router.callback_query(F.data == CALLBACK_SETTINGS_REFRESH)
async def handle_settings_refresh_callback(query: CallbackQuery):
    user_id = query.from_user.id
    current_model = storage.get_setting(user_id, "model", settings.free_claude_default_model)
    await _ack(query, "Settings refreshed.")
    if query.message:
        await query.message.answer(f"Current model: {current_model}")


@router.callback_query(F.data.startswith(CALLBACK_MODEL_PREFIX))
async def handle_model_set_callback(query: CallbackQuery):
    model = (query.data or "").removeprefix(CALLBACK_MODEL_PREFIX).strip()
    if not model:
        await _ack(query, "Model is missing.", show_alert=True)
        return

    storage.set_setting(query.from_user.id, "model", model)
    await _ack(query, f"Model set to: {model}")
    if query.message:
        await query.message.answer(f"Model set to: {model}")


@router.callback_query(F.data == CALLBACK_CLEAR_HISTORY)
async def handle_clear_history_callback(query: CallbackQuery):
    if query.message is None:
        await _ack(query, "Message context is missing.", show_alert=True)
        return

    storage.clear_history(query.message.chat.id, query.from_user.id)
    await _ack(query, "Conversation history cleared.")
    await query.message.answer("Conversation history cleared.")


@router.callback_query(F.data == CALLBACK_LOGOUT_CONFIRM)
async def handle_logout_confirm_callback(query: CallbackQuery):
    if query.message is None or not _is_admin_action_allowed(
        query.message.chat.id,
        _callback_user_id(query),
    ):
        await _ack(query, "This action is restricted to admin chats.", show_alert=True)
        return

    try:
        await perform_log_out(query.bot)
    except TelegramAPIError as exc:
        await _ack(query, "Could not log out from the cloud Bot API.", show_alert=True)
        await _answer_operation_failed(query, "Could not log out from the cloud Bot API", exc)
        return

    await _ack(query, "Logged out.")
    await query.message.answer(
        "Logged out from the cloud Bot API server. The bot will not receive "
        "updates until it logs in again, and cloud login is blocked for 10 "
        "minutes."
    )


@router.callback_query(F.data == CALLBACK_CLOSE_CONFIRM)
async def handle_close_confirm_callback(query: CallbackQuery):
    if query.message is None or not _is_admin_action_allowed(
        query.message.chat.id,
        _callback_user_id(query),
    ):
        await _ack(query, "This action is restricted to admin chats.", show_alert=True)
        return

    try:
        await perform_close(query.bot)
    except TelegramAPIError as exc:
        await _ack(query, "Could not close the bot instance.", show_alert=True)
        await _answer_operation_failed(query, "Could not close the bot instance", exc)
        return

    await _ack(query, "Bot instance closed.")
    await query.message.answer(
        "Closed the bot instance on the current Bot API server. Move the bot "
        "to its new Bot API server and start it again to resume processing "
        "updates."
    )


@router.callback_query(F.data == CALLBACK_CANCEL)
async def handle_cancel_callback(query: CallbackQuery):
    await _ack(query, "Cancelled.")
    if query.message:
        await query.message.answer("Cancelled.")
