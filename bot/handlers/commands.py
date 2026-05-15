from aiogram import Router, F
from aiogram.types import Message
from bot.config import settings
from bot.utils.storage import storage
from bot.services.claude_proxy import ClaudeProxyClient

router = Router()

@router.message(F.command == "start")
async def cmd_start(message: Message):
    await message.answer(
        "Welcome to the Telegram Claude Agent! 🤖\n"
        "I'm connected to free-claude-code and ready to help.\n"
        "Use /help to see available commands."
    )

@router.message(F.command == "help")
async def cmd_help(message: Message):
    help_text = (
        "Available commands:\n"
        "/start - Start the bot\n"
        "/help - Show this help\n"
        "/model - Show or change the AI model\n"
        "/settings - Show your settings\n"
        "/clear - Clear conversation history\n"
        "\nYou can send:\n"
        "- Text messages\n"
        "- Images (photos)\n"
        "- Documents (PDF, TXT, DOCX)\n"
        "- Voice messages (transcribed)"
    )
    await message.answer(help_text)

@router.message(F.command == "model")
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
            models_list = "\n".join(f"• {m}" for m in models)
            await message.answer(f"Current model: {current}\nAvailable models:\n{models_list}")
        except Exception as e:
            await message.answer(f"Current model: {current}\nCould not fetch model list: {str(e)}")
        finally:
            await client.close()
    else:
        new_model = args[1].strip()
        storage.set_setting(user_id, "model", new_model)
        await message.answer(f"Model set to: {new_model}")

@router.message(F.command == "settings")
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

@router.message(F.command == "clear")
async def cmd_clear(message: Message):
    user_id = message.from_user.id
    storage.clear_history(user_id)
    await message.answer("✅ Conversation history cleared.")