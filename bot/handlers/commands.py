from aiogram import Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.types import Message
from bot.config import settings
from bot.services.close import perform_close
from bot.services.copy_message import perform_copy_message
from bot.services.copy_messages import perform_copy_messages
from bot.services.forward_message import perform_forward_message
from bot.services.forward_messages import perform_forward_messages
from bot.services.log_out import perform_log_out
from bot.services.send_animation import perform_send_animation
from bot.services.send_audio import perform_send_audio
from bot.services.send_document import perform_send_document
from bot.services.send_live_photo import SendLivePhotoError, perform_send_live_photo
from bot.services.send_paid_media import SendPaidMediaError, perform_send_paid_media
from bot.services.send_photo import perform_send_photo
from bot.services.send_video import perform_send_video
from bot.services.send_voice import perform_send_voice
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

COPIES_SHARE_KEYWORD = "share"

COPIES_NOCAPTION_KEYWORD = "nocaption"

COPIES_MAX_MESSAGE_IDS = 100

COPIES_USAGE = (
    "<b>copies usage</b>\n"
    "Copies several messages from another chat into this chat as new messages "
    "without a link to the original sender, preserving album grouping, for "
    "support/moderation review. The bot must be a member of the source chat; "
    "service, giveaway and invoice messages cannot be copied and are skipped.\n"
    "Usage: <code>/copies &lt;from_chat_id&gt; &lt;message_id&gt; "
    "[&lt;message_id&gt; ...] [share] [nocaption]</code>\n"
    "Provide 1-100 message ids in strictly increasing order. By default the "
    "copied messages are protected from further forwarding and saving. Append "
    "<code>share</code> to allow re-forwarding them and <code>nocaption</code> "
    "to drop their original captions."
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

AUDIO_CAPTION_LIMIT = 1024

AUDIO_USAGE = (
    "<b>audio usage</b>\n"
    "Sends an audio file into this chat as a playable music track instead of "
    "plain text. Pass an HTTP(S) URL Telegram can fetch or a file_id of an "
    "audio file already on Telegram servers.\n"
    "Usage: <code>/audio &lt;url_or_file_id&gt; [caption]</code>\n"
    "The caption is optional and limited to 1024 characters. Telegram expects "
    "the audio in .MP3 or .M4A format and limits a file sent by URL or file_id "
    "to 20 MB."
)

LIVE_PHOTO_CAPTION_LIMIT = 1024

LIVE_PHOTO_USAGE = (
    "<b>livephoto usage</b>\n"
    "Sends a live photo into this chat: a short looping video paired with its "
    "static cover photo, instead of plain text. Telegram does not support "
    "sending live photos by URL, so pass file_id values of media already on "
    "Telegram servers.\n"
    "Usage: <code>/livephoto &lt;live_photo_file_id&gt; &lt;photo_file_id&gt; "
    "[caption]</code>\n"
    "The live_photo video must be at most 10 seconds long and 10 MB. The "
    "caption is optional and limited to 1024 characters."
)

DOCUMENT_CAPTION_LIMIT = 1024

DOCUMENT_USAGE = (
    "<b>document usage</b>\n"
    "Sends a file into this chat as a Telegram document instead of plain "
    "text, for returning large text, PDF or source artifacts when a message "
    "does not fit. Pass an HTTP(S) URL Telegram can fetch or a file_id of a "
    "file already on Telegram servers.\n"
    "Usage: <code>/document &lt;url_or_file_id&gt; [caption]</code>\n"
    "The caption is optional and limited to 1024 characters. Telegram limits "
    "a file sent by URL to 20 MB."
)

VIDEO_CAPTION_LIMIT = 1024

VIDEO_USAGE = (
    "<b>video usage</b>\n"
    "Sends a video into this chat as a playable Telegram video instead of "
    "plain text. Pass an HTTP(S) URL Telegram can fetch or a file_id of a "
    "video already on Telegram servers.\n"
    "Usage: <code>/video &lt;url_or_file_id&gt; [caption]</code>\n"
    "The caption is optional and limited to 1024 characters. Telegram clients "
    "support MPEG4 videos and limit a file sent by URL to 20 MB."
)

ANIMATION_CAPTION_LIMIT = 1024

ANIMATION_USAGE = (
    "<b>animation usage</b>\n"
    "Sends an animation into this chat as a playable GIF or soundless video "
    "instead of plain text. Pass an HTTP(S) URL Telegram can fetch or a file_id "
    "of an animation already on Telegram servers.\n"
    "Usage: <code>/animation &lt;url_or_file_id&gt; [caption]</code>\n"
    "The caption is optional and limited to 1024 characters. Telegram delivers "
    "GIF and H.264/MPEG-4 AVC files without sound and limits a file sent by URL "
    "to 20 MB."
)

VOICE_CAPTION_LIMIT = 1024

VOICE_USAGE = (
    "<b>voice usage</b>\n"
    "Sends a voice message into this chat as a playable audio clip (shown as a "
    "waveform) instead of plain text. Pass an HTTP(S) URL Telegram can fetch or "
    "a file_id of a voice message already on Telegram servers.\n"
    "Usage: <code>/voice &lt;url_or_file_id&gt; [caption]</code>\n"
    "The caption is optional and limited to 1024 characters. For playback as a "
    "voice message Telegram expects an .OGG file encoded with OPUS, or an .MP3 "
    "or .M4A file, and limits a file sent by URL to 20 MB."
)

PAID_MEDIA_CAPTION_LIMIT = 1024

PAID_MEDIA_MIN_STARS = 1

PAID_MEDIA_MAX_STARS = 25000

PAID_MEDIA_USAGE = (
    "<b>paidmedia usage</b>\n"
    "Sends a paid photo into this chat that users must pay for with Telegram "
    "Stars to access. Pass the star price (1-25000), then an HTTP(S) URL "
    "Telegram can fetch or a file_id of a photo already on Telegram servers.\n"
    "Usage: <code>/paidmedia &lt;star_count&gt; &lt;url_or_file_id&gt; [caption]</code>\n"
    "The caption is optional and limited to 1024 characters. When this chat is a "
    "channel the Telegram Star proceeds are credited to the channel balance, "
    "otherwise to the bot balance."
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
        "/copies - Copy several messages into this chat without source link (admin only)\n"
        "/photo - Send an image into this chat as a photo (admin only)\n"
        "/audio - Send an audio file into this chat as a music track (admin only)\n"
        "/livephoto - Send a live photo (video + cover) into this chat (admin only)\n"
        "/document - Send a file into this chat as a document (admin only)\n"
        "/video - Send a video into this chat as a playable video (admin only)\n"
        "/animation - Send an animation (GIF/soundless video) into this chat (admin only)\n"
        "/voice - Send a voice message into this chat as a playable audio clip (admin only)\n"
        "/paidmedia - Send a paid photo into this chat priced in Telegram Stars (admin only)\n"
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

@router.message(Command("copies"))
async def cmd_copies(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    args = (message.text or "").split()
    parsed = _parse_copy_messages_args(args[1:])
    if parsed is None:
        await message.answer(COPIES_USAGE, parse_mode="HTML")
        return

    from_chat_id, message_ids, protect_content, remove_caption = parsed

    try:
        result = await perform_copy_messages(
            message.bot,
            chat_id=message.chat.id,
            from_chat_id=from_chat_id,
            message_ids=message_ids,
            protect_content=protect_content,
            remove_caption=remove_caption,
        )
    except TelegramAPIError as exc:
        await message.answer(f"Could not copy the messages: {exc}")
        return

    copied_count = len(result) if hasattr(result, "__len__") else len(message_ids)
    protection = "protected" if protect_content else "shareable"
    captions = "without captions" if remove_caption else "with captions"
    await message.answer(
        f"Copied {copied_count} of {len(message_ids)} messages from chat "
        f"{from_chat_id} ({protection} copy, {captions})."
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

@router.message(Command("audio"))
async def cmd_audio(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_audio_args(message.text or "")
    if parsed is None:
        await message.answer(AUDIO_USAGE, parse_mode="HTML")
        return

    audio, caption = parsed
    if caption is not None and len(caption) > AUDIO_CAPTION_LIMIT:
        await message.answer(
            f"Caption is too long: {len(caption)} characters "
            f"(max {AUDIO_CAPTION_LIMIT})."
        )
        return

    try:
        await perform_send_audio(
            message.bot,
            chat_id=message.chat.id,
            audio=audio,
            caption=caption,
        )
    except TelegramAPIError as exc:
        await message.answer(f"Could not send the audio: {exc}")
        return

    await message.answer(
        "Sent audio with caption." if caption else "Sent audio."
    )

@router.message(Command("livephoto"))
async def cmd_live_photo(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_live_photo_args(message.text or "")
    if parsed is None:
        await message.answer(LIVE_PHOTO_USAGE, parse_mode="HTML")
        return

    live_photo, photo, caption = parsed
    if caption is not None and len(caption) > LIVE_PHOTO_CAPTION_LIMIT:
        await message.answer(
            f"Caption is too long: {len(caption)} characters "
            f"(max {LIVE_PHOTO_CAPTION_LIMIT})."
        )
        return

    try:
        await perform_send_live_photo(
            message.bot,
            chat_id=message.chat.id,
            live_photo=live_photo,
            photo=photo,
            caption=caption,
        )
    except SendLivePhotoError as exc:
        await message.answer(f"Could not send the live photo: {exc}")
        return

    await message.answer(
        "Sent live photo with caption." if caption else "Sent live photo."
    )

@router.message(Command("document"))
async def cmd_document(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_document_args(message.text or "")
    if parsed is None:
        await message.answer(DOCUMENT_USAGE, parse_mode="HTML")
        return

    document, caption = parsed
    if caption is not None and len(caption) > DOCUMENT_CAPTION_LIMIT:
        await message.answer(
            f"Caption is too long: {len(caption)} characters "
            f"(max {DOCUMENT_CAPTION_LIMIT})."
        )
        return

    try:
        await perform_send_document(
            message.bot,
            chat_id=message.chat.id,
            document=document,
            caption=caption,
        )
    except TelegramAPIError as exc:
        await message.answer(f"Could not send the document: {exc}")
        return

    await message.answer(
        "Sent document with caption." if caption else "Sent document."
    )

@router.message(Command("video"))
async def cmd_video(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_video_args(message.text or "")
    if parsed is None:
        await message.answer(VIDEO_USAGE, parse_mode="HTML")
        return

    video, caption = parsed
    if caption is not None and len(caption) > VIDEO_CAPTION_LIMIT:
        await message.answer(
            f"Caption is too long: {len(caption)} characters "
            f"(max {VIDEO_CAPTION_LIMIT})."
        )
        return

    try:
        await perform_send_video(
            message.bot,
            chat_id=message.chat.id,
            video=video,
            caption=caption,
        )
    except TelegramAPIError as exc:
        await message.answer(f"Could not send the video: {exc}")
        return

    await message.answer(
        "Sent video with caption." if caption else "Sent video."
    )

@router.message(Command("animation"))
async def cmd_animation(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_animation_args(message.text or "")
    if parsed is None:
        await message.answer(ANIMATION_USAGE, parse_mode="HTML")
        return

    animation, caption = parsed
    if caption is not None and len(caption) > ANIMATION_CAPTION_LIMIT:
        await message.answer(
            f"Caption is too long: {len(caption)} characters "
            f"(max {ANIMATION_CAPTION_LIMIT})."
        )
        return

    try:
        await perform_send_animation(
            message.bot,
            chat_id=message.chat.id,
            animation=animation,
            caption=caption,
        )
    except TelegramAPIError as exc:
        await message.answer(f"Could not send the animation: {exc}")
        return

    await message.answer(
        "Sent animation with caption." if caption else "Sent animation."
    )

@router.message(Command("voice"))
async def cmd_voice(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_voice_args(message.text or "")
    if parsed is None:
        await message.answer(VOICE_USAGE, parse_mode="HTML")
        return

    voice, caption = parsed
    if caption is not None and len(caption) > VOICE_CAPTION_LIMIT:
        await message.answer(
            f"Caption is too long: {len(caption)} characters "
            f"(max {VOICE_CAPTION_LIMIT})."
        )
        return

    try:
        await perform_send_voice(
            message.bot,
            chat_id=message.chat.id,
            voice=voice,
            caption=caption,
        )
    except TelegramAPIError as exc:
        await message.answer(f"Could not send the voice message: {exc}")
        return

    await message.answer(
        "Sent voice message with caption." if caption else "Sent voice message."
    )

@router.message(Command("paidmedia"))
async def cmd_paid_media(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_paid_media_args(message.text or "")
    if parsed is None:
        await message.answer(PAID_MEDIA_USAGE, parse_mode="HTML")
        return

    star_count, media, caption = parsed
    if not PAID_MEDIA_MIN_STARS <= star_count <= PAID_MEDIA_MAX_STARS:
        await message.answer(
            f"Star count must be between {PAID_MEDIA_MIN_STARS} and "
            f"{PAID_MEDIA_MAX_STARS}."
        )
        return

    if caption is not None and len(caption) > PAID_MEDIA_CAPTION_LIMIT:
        await message.answer(
            f"Caption is too long: {len(caption)} characters "
            f"(max {PAID_MEDIA_CAPTION_LIMIT})."
        )
        return

    try:
        await perform_send_paid_media(
            message.bot,
            chat_id=message.chat.id,
            star_count=star_count,
            media=[{"type": "photo", "media": media}],
            caption=caption,
        )
    except SendPaidMediaError as exc:
        await message.answer(f"Could not send the paid media: {exc}")
        return

    await message.answer(
        "Sent paid media with caption." if caption else "Sent paid media."
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


def _parse_copy_messages_args(args: list[str]):
    """Parse ``/copies`` args into ``(from_chat_id, ids, protect, remove_caption)``.

    Returns ``None`` when the arguments are missing or invalid so the caller can
    show usage. ``protect`` defaults to ``True`` and is disabled by the optional
    trailing ``share`` keyword; ``remove_caption`` defaults to ``False`` and is
    enabled by the optional trailing ``nocaption`` keyword. Both keywords may
    appear together at the end in any order. Telegram requires 1-100 message ids
    specified in a strictly increasing order, so both bounds are validated here
    before the call instead of relying on a Telegram error.
    """
    protect_content = True
    remove_caption = False
    while args and args[-1].strip().lower() in (
        COPIES_SHARE_KEYWORD,
        COPIES_NOCAPTION_KEYWORD,
    ):
        keyword = args[-1].strip().lower()
        if keyword == COPIES_SHARE_KEYWORD:
            protect_content = False
        else:
            remove_caption = True
        args = args[:-1]

    if len(args) < 2:
        return None

    try:
        from_chat_id = int(args[0])
        message_ids = [int(x) for x in args[1:]]
    except ValueError:
        return None

    if not 1 <= len(message_ids) <= COPIES_MAX_MESSAGE_IDS:
        return None

    if any(later <= earlier for earlier, later in zip(message_ids, message_ids[1:])):
        return None

    return from_chat_id, message_ids, protect_content, remove_caption


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


def _parse_audio_args(text: str):
    """Parse ``/audio`` arguments into ``(audio, caption)``.

    Splits the raw command text into the command, the audio reference (URL or
    ``file_id``) and an optional free-text caption that may itself contain
    spaces. Returns ``None`` when no audio reference is provided so the caller
    can show usage. The caller validates the caption length against Telegram's
    1024-character limit.
    """
    parts = (text or "").split(maxsplit=2)
    if len(parts) < 2:
        return None

    audio = parts[1].strip()
    if not audio:
        return None

    caption = parts[2].strip() if len(parts) >= 3 else None
    if caption == "":
        caption = None

    return audio, caption


def _parse_document_args(text: str):
    """Parse ``/document`` arguments into ``(document, caption)``.

    Splits the raw command text into the command, the document reference (URL or
    ``file_id``) and an optional free-text caption that may itself contain
    spaces. Returns ``None`` when no document reference is provided so the caller
    can show usage. The caller validates the caption length against Telegram's
    1024-character limit.
    """
    parts = (text or "").split(maxsplit=2)
    if len(parts) < 2:
        return None

    document = parts[1].strip()
    if not document:
        return None

    caption = parts[2].strip() if len(parts) >= 3 else None
    if caption == "":
        caption = None

    return document, caption


def _parse_video_args(text: str):
    """Parse ``/video`` arguments into ``(video, caption)``.

    Splits the raw command text into the command, the video reference (URL or
    ``file_id``) and an optional free-text caption that may itself contain
    spaces. Returns ``None`` when no video reference is provided so the caller
    can show usage. The caller validates the caption length against Telegram's
    1024-character limit.
    """
    parts = (text or "").split(maxsplit=2)
    if len(parts) < 2:
        return None

    video = parts[1].strip()
    if not video:
        return None

    caption = parts[2].strip() if len(parts) >= 3 else None
    if caption == "":
        caption = None

    return video, caption


def _parse_animation_args(text: str):
    """Parse ``/animation`` arguments into ``(animation, caption)``.

    Splits the raw command text into the command, the animation reference (URL
    or ``file_id``) and an optional free-text caption that may itself contain
    spaces. Returns ``None`` when no animation reference is provided so the
    caller can show usage. The caller validates the caption length against
    Telegram's 1024-character limit.
    """
    parts = (text or "").split(maxsplit=2)
    if len(parts) < 2:
        return None

    animation = parts[1].strip()
    if not animation:
        return None

    caption = parts[2].strip() if len(parts) >= 3 else None
    if caption == "":
        caption = None

    return animation, caption


def _parse_voice_args(text: str):
    """Parse ``/voice`` arguments into ``(voice, caption)``.

    Splits the raw command text into the command, the voice reference (URL or
    ``file_id``) and an optional free-text caption that may itself contain
    spaces. Returns ``None`` when no voice reference is provided so the caller
    can show usage. The caller validates the caption length against Telegram's
    1024-character limit.
    """
    parts = (text or "").split(maxsplit=2)
    if len(parts) < 2:
        return None

    voice = parts[1].strip()
    if not voice:
        return None

    caption = parts[2].strip() if len(parts) >= 3 else None
    if caption == "":
        caption = None

    return voice, caption


def _parse_live_photo_args(text: str):
    """Parse ``/livephoto`` arguments into ``(live_photo, photo, caption)``.

    Splits the raw command text into the command, the ``live_photo`` video
    reference (a ``file_id``), the static ``photo`` reference (a ``file_id``) and
    an optional free-text caption that may itself contain spaces. Returns
    ``None`` when either media reference is missing so the caller can show usage.
    Telegram does not support sending live photos by URL, so both references are
    expected to be ``file_id`` values. The caller validates the caption length
    against Telegram's 1024-character limit.
    """
    parts = (text or "").split(maxsplit=3)
    if len(parts) < 3:
        return None

    live_photo = parts[1].strip()
    photo = parts[2].strip()
    if not live_photo or not photo:
        return None

    caption = parts[3].strip() if len(parts) >= 4 else None
    if caption == "":
        caption = None

    return live_photo, photo, caption


def _parse_paid_media_args(text: str):
    """Parse ``/paidmedia`` arguments into ``(star_count, media, caption)``.

    Splits the raw command text into the command, the integer ``star_count``,
    the photo reference (URL or ``file_id``) and an optional free-text caption
    that may itself contain spaces. Returns ``None`` when the star price or media
    reference is missing or the star price is not an integer so the caller can
    show usage. The caller validates the ``star_count`` range (1-25000) and the
    caption length against Telegram's 1024-character limit.
    """
    parts = (text or "").split(maxsplit=3)
    if len(parts) < 3:
        return None

    star_count_str = parts[1].strip()
    media = parts[2].strip()
    if not star_count_str or not media:
        return None

    try:
        star_count = int(star_count_str)
    except ValueError:
        return None

    caption = parts[3].strip() if len(parts) >= 4 else None
    if caption == "":
        caption = None

    return star_count, media, caption
