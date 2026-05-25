from aiogram import Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.types import Message
from bot.config import settings
from bot.services.log_out import perform_log_out
from bot.services.webhook_delete import delete_webhook
from bot.services.webhook_info import fetch_webhook_info, format_webhook_info
from bot.utils.storage import storage
from bot.services.claude_proxy import ClaudeProxyClient

router = Router()

LOGOUT_CONFIRM_KEYWORD = "confirm"

LOGOUT_WARNING = (
    "<b>logOut confirmation required</b>\n"
    "This logs the bot out of the cloud Telegram Bot API server. After a "
    "successful logout the bot stops receiving updates and cannot log back "
    "into the cloud Bot API server for 10 minutes. Use this only before "
    "switching to a local Bot API server.\n"
    "Run <code>/logout confirm</code> to proceed."
)

DELETE_WEBHOOK_USAGE = "Usage: /deletewebhook [drop_pending_updates=true|false]"
DROP_PENDING_UPDATES_TRUE_VALUES = {
    "--drop-pending-updates",
    "--drop-pending-updates=true",
    "1",
    "drop",
    "drop_pending_updates=true",
    "true",
    "yes",
}
DROP_PENDING_UPDATES_FALSE_VALUES = {
    "--drop-pending-updates=false",
    "0",
    "drop_pending_updates=false",
    "false",
    "keep",
    "no",
}

@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "Welcome to the Telegram Claude Agent!\n"
        "I'm connected to free-claude-code and ready to help.\n"
        "Use /help to see available commands."
    )

@router.message(Command("help"))
async def cmd_help(message: Message):
    help_text = (
        "Available commands:\n"
        "/start - Start the bot\n"
        "/help - Show this help\n"
        "/model - Show or change the AI model\n"
        "/settings - Show your settings\n"
        "/webhook - Show webhook diagnostics (restricted)\n"
        "/deletewebhook - Delete webhook before polling/local Bot API switch (restricted)\n"
        "/logout - Log out from the cloud Bot API (admin only)\n"
        "/clear - Clear conversation history\n"
        "\nYou can send:\n"
        "- Text messages\n"
        "- Images (photos)\n"
        "- Documents (PDF, TXT, DOCX)\n"
        "- Voice messages (transcribed)"
    )
    await message.answer(help_text)

@router.message(Command("model"))
async def cmd_model(message: Message):
    user_id = message.from_user.id
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        current = storage.get_setting(user_id, "model", settings.free_claude_default_model)
        client = ClaudeProxyClient(
            settings.free_claude_base_url,
            settings.free_claude_auth_token,
            settings.free_claude_timeout_seconds,
        )
        try:
            models = await client.list_models()
            models_list = "\n".join(f"- {m}" for m in models)
            await message.answer(f"Current model: {current}\nAvailable models:\n{models_list}")
        except Exception as e:
            await message.answer(f"Current model: {current}\nCould not fetch model list: {str(e)}")
        finally:
            await client.close()
    else:
        new_model = args[1].strip()
        storage.set_setting(user_id, "model", new_model)
        await message.answer(f"Model set to: {new_model}")

@router.message(Command("settings"))
async def cmd_settings(message: Message):
    user_id = message.from_user.id
    current_model = storage.get_setting(user_id, "model", settings.free_claude_default_model)
    streaming = settings.free_claude_streaming_enabled
    guest_mode = settings.telegram_guest_mode_enabled
    rate_limit = settings.rate_limit_requests_per_minute
    settings_text = (
        f"<b>Your settings:</b>\n"
        f"Model: {current_model}\n"
        f"Streaming: {'enabled' if streaming else 'disabled'}\n"
        f"Guest mode: {'enabled' if guest_mode else 'disabled'}\n"
        f"Rate limit: {rate_limit} requests per minute"
    )
    await message.answer(settings_text, parse_mode="HTML")

@router.message(Command("webhook"))
async def cmd_webhook_info(message: Message):
    if not _is_diagnostics_allowed(message.chat.id):
        await message.answer("Webhook diagnostics are restricted.")
        return

    try:
        info = await fetch_webhook_info(message.bot)
    except TelegramAPIError as exc:
        await message.answer(f"Could not fetch webhook diagnostics: {exc}")
        return

    await message.answer(format_webhook_info(info), parse_mode="HTML")


@router.message(Command("deletewebhook"))
async def cmd_delete_webhook(message: Message):
    if not _is_operational_command_allowed(message.chat.id):
        await message.answer("Webhook lifecycle operations are restricted.")
        return

    try:
        drop_pending_updates = _parse_drop_pending_updates(message.text)
    except ValueError:
        await message.answer(DELETE_WEBHOOK_USAGE)
        return

    try:
        await delete_webhook(message.bot, drop_pending_updates=drop_pending_updates)
    except TelegramAPIError as exc:
        await message.answer(f"Could not delete webhook: {exc}")
        return

    pending_updates_status = "dropped" if drop_pending_updates else "kept"
    await message.answer(f"Webhook deleted. Pending updates were {pending_updates_status}.")


@router.message(Command("logout"))
async def cmd_log_out(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    args = (message.text or "").split()
    if len(args) < 2 or args[1].strip().lower() != LOGOUT_CONFIRM_KEYWORD:
        await message.answer(LOGOUT_WARNING, parse_mode="HTML")
        return

    try:
        await perform_log_out(message.bot)
    except TelegramAPIError as exc:
        await message.answer(f"Could not log out from the cloud Bot API: {exc}")
        return

    await message.answer(
        "Logged out from the cloud Bot API server. The bot will not receive "
        "updates until it logs in again, and cloud login is blocked for 10 "
        "minutes."
    )

@router.message(Command("clear"))
async def cmd_clear(message: Message):
    storage.clear_history(message.chat.id, message.from_user.id)
    await message.answer("Conversation history cleared.")


def _is_diagnostics_allowed(chat_id: int) -> bool:
    admin_chat_ids = settings.admin_chat_ids
    if admin_chat_ids:
        return chat_id in admin_chat_ids

    allowed_chat_ids = settings.allowed_chat_ids
    return bool(allowed_chat_ids and chat_id in allowed_chat_ids)


def _is_operational_command_allowed(chat_id: int) -> bool:
    admin_chat_ids = settings.admin_chat_ids
    if admin_chat_ids:
        return chat_id in admin_chat_ids

    allowed_chat_ids = settings.allowed_chat_ids
    return bool(allowed_chat_ids and chat_id in allowed_chat_ids)


def _is_admin_action_allowed(chat_id: int) -> bool:
    admin_chat_ids = settings.admin_chat_ids
    return bool(admin_chat_ids and chat_id in admin_chat_ids)


def _parse_drop_pending_updates(text: str | None) -> bool:
    parts = (text or "").split(maxsplit=1)
    if len(parts) == 1:
        return False

    value = parts[1].strip().lower()
    if not value:
        return False
    if value in DROP_PENDING_UPDATES_TRUE_VALUES:
        return True
    if value in DROP_PENDING_UPDATES_FALSE_VALUES:
        return False
    raise ValueError(f"Unsupported drop_pending_updates argument: {parts[1]}")
