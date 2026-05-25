from aiogram import Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.types import Message
from bot.config import settings
from bot.services.close import perform_close
from bot.services.copy_message import perform_copy_message
from bot.services.forward_message import perform_forward_message
from bot.services.forward_messages import perform_forward_messages
from bot.services.log_out import perform_log_out
from bot.services.send_photo import perform_send_photo
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

CLOSE_CONFIRM_KEYWORD = "confirm"

CLOSE_WARNING = (
    "<b>close confirmation required</b>\n"
    "This closes the running bot instance on the current Bot API server. Use "
    "it only before moving the bot from one local Bot API server to another, "
    "and delete the webhook first so the bot is not relaunched after a server "
    "restart. Telegram returns error 429 if it is called within 10 minutes of "
    "the bot being launched.\n"
    "Run <code>/close confirm</code> to proceed."
)

FORWARD_SHARE_KEYWORD = "share"

FORWARD_USAGE = (
    "<b>forward usage</b>\n"
    "Forwards a single message into this chat for support/moderation review. "
    "The bot must be a member of the source chat and the message must not be a "
    "service message or have protected content.\n"
    "Usage: <code>/forward &lt;from_chat_id&gt; &lt;message_id&gt; [share]</code>\n"
    "By default the forwarded copy is protected from further forwarding and "
    "saving. Append <code>share</code> to allow re-forwarding it."
)

FORWARDS_SHARE_KEYWORD = "share"

FORWARDS_MAX_MESSAGE_IDS = 100

FORWARDS_USAGE = (
    "<b>forwards usage</b>\n"
    "Forwards several messages from another chat into this chat for "
    "support/moderation review, preserving album grouping. The bot must be a "
    "member of the source chat; service messages and messages with protected "
    "content cannot be forwarded and are skipped.\n"
    "Usage: <code>/forwards &lt;from_chat_id&gt; &lt;message_id&gt; "
    "[&lt;message_id&gt; ...] [share]</code>\n"
    "Provide 1-100 message ids in strictly increasing order. By default the "
    "forwarded copies are protected from further forwarding and saving. Append "
    "<code>share</code> to allow re-forwarding them."
)

COPY_SHARE_KEYWORD = "share"

COPY_USAGE = (
    "<b>copy usage</b>\n"
    "Copies a single message into this chat as a new message without a link to "
    "the original sender, for support/moderation review. The bot must be a "
    "member of the source chat; service messages, paid media, giveaway and "
    "invoice messages cannot be copied.\n"
    "Usage: <code>/copy &lt;from_chat_id&gt; &lt;message_id&gt; [share]</code>\n"
    "By default the copied message is protected from further forwarding and "
    "saving. Append <code>share</code> to allow re-forwarding it."
)

PHOTO_CAPTION_LIMIT = 1024

PHOTO_USAGE = (
    "<b>photo usage</b>\n"
    "Sends an image into this chat as a real Telegram photo instead of plain "
    "text. Pass an HTTP(S) URL Telegram can fetch or a file_id of a photo "
    "already on Telegram servers.\n"
    "Usage: <code>/photo &lt;url_or_file_id&gt; [caption]</code>\n"
    "The caption is optional and limited to 1024 characters. Telegram limits "
    "the photo to 10 MB, its total width+height to 10000 and its aspect ratio "
    "to 20."
)

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
        "/logout - Log out from the cloud Bot API (admin only)\n"
        "/close - Close the bot instance on the current Bot API (admin only)\n"
        "/forward - Forward a message into this chat for review (admin only)\n"
        "/forwards - Forward several messages into this chat for review (admin only)\n"
        "/copy - Copy a message into this chat without source link (admin only)\n"
        "/photo - Send an image into this chat as a photo (admin only)\n"
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

@router.message(Command("close"))
async def cmd_close(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    args = (message.text or "").split()
    if len(args) < 2 or args[1].strip().lower() != CLOSE_CONFIRM_KEYWORD:
        await message.answer(CLOSE_WARNING, parse_mode="HTML")
        return

    try:
        await perform_close(message.bot)
    except TelegramAPIError as exc:
        await message.answer(f"Could not close the bot instance: {exc}")
        return

    await message.answer(
        "Closed the bot instance on the current Bot API server. Move the bot "
        "to its new Bot API server and start it again to resume processing "
        "updates."
    )

@router.message(Command("forward"))
async def cmd_forward(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    args = (message.text or "").split()
    parsed = _parse_forward_args(args[1:])
    if parsed is None:
        await message.answer(FORWARD_USAGE, parse_mode="HTML")
        return

    from_chat_id, message_id, protect_content = parsed

    try:
        await perform_forward_message(
            message.bot,
            chat_id=message.chat.id,
            from_chat_id=from_chat_id,
            message_id=message_id,
            protect_content=protect_content,
        )
    except TelegramAPIError as exc:
        await message.answer(f"Could not forward the message: {exc}")
        return

    protection = "protected" if protect_content else "shareable"
    await message.answer(
        f"Forwarded message {message_id} from chat {from_chat_id} "
        f"({protection} copy)."
    )

@router.message(Command("forwards"))
async def cmd_forwards(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    args = (message.text or "").split()
    parsed = _parse_forward_messages_args(args[1:])
    if parsed is None:
        await message.answer(FORWARDS_USAGE, parse_mode="HTML")
        return

    from_chat_id, message_ids, protect_content = parsed

    try:
        result = await perform_forward_messages(
            message.bot,
            chat_id=message.chat.id,
            from_chat_id=from_chat_id,
            message_ids=message_ids,
            protect_content=protect_content,
        )
    except TelegramAPIError as exc:
        await message.answer(f"Could not forward the messages: {exc}")
        return

    forwarded_count = len(result) if hasattr(result, "__len__") else len(message_ids)
    protection = "protected" if protect_content else "shareable"
    await message.answer(
        f"Forwarded {forwarded_count} of {len(message_ids)} messages from chat "
        f"{from_chat_id} ({protection} copy)."
    )

@router.message(Command("copy"))
async def cmd_copy(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    args = (message.text or "").split()
    parsed = _parse_copy_args(args[1:])
    if parsed is None:
        await message.answer(COPY_USAGE, parse_mode="HTML")
        return

    from_chat_id, message_id, protect_content = parsed

    try:
        await perform_copy_message(
            message.bot,
            chat_id=message.chat.id,
            from_chat_id=from_chat_id,
            message_id=message_id,
            protect_content=protect_content,
        )
    except TelegramAPIError as exc:
        await message.answer(f"Could not copy the message: {exc}")
        return

    protection = "protected" if protect_content else "shareable"
    await message.answer(
        f"Copied message {message_id} from chat {from_chat_id} "
        f"({protection} copy)."
    )

@router.message(Command("photo"))
async def cmd_photo(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_photo_args(message.text or "")
    if parsed is None:
        await message.answer(PHOTO_USAGE, parse_mode="HTML")
        return

    photo, caption = parsed
    if caption is not None and len(caption) > PHOTO_CAPTION_LIMIT:
        await message.answer(
            f"Caption is too long: {len(caption)} characters "
            f"(max {PHOTO_CAPTION_LIMIT})."
        )
        return

    try:
        await perform_send_photo(
            message.bot,
            chat_id=message.chat.id,
            photo=photo,
            caption=caption,
        )
    except TelegramAPIError as exc:
        await message.answer(f"Could not send the photo: {exc}")
        return

    await message.answer(
        "Sent photo with caption." if caption else "Sent photo."
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


def _is_admin_action_allowed(chat_id: int) -> bool:
    admin_chat_ids = settings.admin_chat_ids
    return bool(admin_chat_ids and chat_id in admin_chat_ids)


def _parse_forward_args(args: list[str]):
    """Parse ``/forward`` arguments into ``(from_chat_id, message_id, protect)``.

    Returns ``None`` when the arguments are missing or invalid so the caller can
    show usage. ``protect`` defaults to ``True`` and is disabled by the optional
    trailing ``share`` keyword.
    """
    if len(args) < 2 or len(args) > 3:
        return None

    try:
        from_chat_id = int(args[0])
        message_id = int(args[1])
    except ValueError:
        return None

    protect_content = True
    if len(args) == 3:
        if args[2].strip().lower() != FORWARD_SHARE_KEYWORD:
            return None
        protect_content = False

    return from_chat_id, message_id, protect_content


def _parse_forward_messages_args(args: list[str]):
    """Parse ``/forwards`` arguments into ``(from_chat_id, message_ids, protect)``.

    Returns ``None`` when the arguments are missing or invalid so the caller can
    show usage. ``protect`` defaults to ``True`` and is disabled by the optional
    trailing ``share`` keyword. Telegram requires 1-100 message ids specified in
    a strictly increasing order, so both bounds are validated here before the
    call instead of relying on a Telegram error.
    """
    protect_content = True
    if args and args[-1].strip().lower() == FORWARDS_SHARE_KEYWORD:
        protect_content = False
        args = args[:-1]

    if len(args) < 2:
        return None

    try:
        from_chat_id = int(args[0])
        message_ids = [int(x) for x in args[1:]]
    except ValueError:
        return None

    if not 1 <= len(message_ids) <= FORWARDS_MAX_MESSAGE_IDS:
        return None

    if any(later <= earlier for earlier, later in zip(message_ids, message_ids[1:])):
        return None

    return from_chat_id, message_ids, protect_content


def _parse_copy_args(args: list[str]):
    """Parse ``/copy`` arguments into ``(from_chat_id, message_id, protect)``.

    Returns ``None`` when the arguments are missing or invalid so the caller can
    show usage. ``protect`` defaults to ``True`` and is disabled by the optional
    trailing ``share`` keyword.
    """
    if len(args) < 2 or len(args) > 3:
        return None

    try:
        from_chat_id = int(args[0])
        message_id = int(args[1])
    except ValueError:
        return None

    protect_content = True
    if len(args) == 3:
        if args[2].strip().lower() != COPY_SHARE_KEYWORD:
            return None
        protect_content = False

    return from_chat_id, message_id, protect_content


def _parse_photo_args(text: str):
    """Parse ``/photo`` arguments into ``(photo, caption)``.

    Splits the raw command text into the command, the photo reference (URL or
    ``file_id``) and an optional free-text caption that may itself contain
    spaces. Returns ``None`` when no photo reference is provided so the caller
    can show usage. The caller validates the caption length against Telegram's
    1024-character limit.
    """
    parts = (text or "").split(maxsplit=2)
    if len(parts) < 2:
        return None

    photo = parts[1].strip()
    if not photo:
        return None

    caption = parts[2].strip() if len(parts) >= 3 else None
    if caption == "":
        caption = None

    return photo, caption
