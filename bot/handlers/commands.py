from aiogram import Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.types import (
    InputMediaAudio,
    InputMediaDocument,
    InputMediaPhoto,
    InputMediaVideo,
    Message,
)
from bot.config import settings
from bot.services.close import perform_close
from bot.services.copy_message import perform_copy_message
from bot.services.copy_messages import perform_copy_messages
from bot.services.forward_message import perform_forward_message
from bot.services.forward_messages import perform_forward_messages
from bot.services.log_out import perform_log_out
from bot.services.send_animation import perform_send_animation
from bot.services.send_audio import perform_send_audio
from bot.services.send_chat_action import (
    CHAT_ACTIONS,
    SendChatActionError,
    perform_send_chat_action,
)
from bot.services.send_checklist import SendChecklistError, perform_send_checklist
from bot.services.send_contact import perform_send_contact
from bot.services.send_dice import perform_send_dice
from bot.services.send_document import perform_send_document
from bot.services.send_live_photo import SendLivePhotoError, perform_send_live_photo
from bot.services.send_location import perform_send_location
from bot.services.send_media_group import perform_send_media_group
from bot.services.send_message_draft import (
    MESSAGE_DRAFT_TEXT_LIMIT,
    SendMessageDraftError,
    perform_send_message_draft,
)
from bot.services.send_paid_media import SendPaidMediaError, perform_send_paid_media
from bot.services.send_photo import perform_send_photo
from bot.services.send_poll import perform_send_poll
from bot.services.send_venue import perform_send_venue
from bot.services.send_video import perform_send_video
from bot.services.send_video_note import perform_send_video_note
from bot.services.send_voice import perform_send_voice
from bot.services.get_user_profile_photos import (
    GET_USER_PROFILE_PHOTOS_MAX_LIMIT,
    GET_USER_PROFILE_PHOTOS_MIN_LIMIT,
    fetch_user_profile_photos,
    format_user_profile_photos,
)
from bot.services.set_message_reaction import (
    REACTION_EMOJI,
    perform_set_message_reaction,
)
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

VIDEO_NOTE_USAGE = (
    "<b>videonote usage</b>\n"
    "Sends a rounded square video message (video note) into this chat instead "
    "of plain text. Pass a file_id of a video note that already exists on "
    "Telegram servers; Telegram does not support sending video notes by URL.\n"
    "Usage: <code>/videonote &lt;file_id&gt;</code>\n"
    "Video notes have no caption. Telegram expects a square MPEG4 video; the "
    "duration and side length are taken from the file."
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

LOCATION_MIN_LATITUDE = -90.0

LOCATION_MAX_LATITUDE = 90.0

LOCATION_MIN_LONGITUDE = -180.0

LOCATION_MAX_LONGITUDE = 180.0

LOCATION_USAGE = (
    "<b>location usage</b>\n"
    "Sends a point on the map into this chat as a real Telegram location "
    "instead of plain text. Pass the latitude and longitude in decimal "
    "degrees.\n"
    "Usage: <code>/location &lt;latitude&gt; &lt;longitude&gt;</code>\n"
    "Latitude must be between -90 and 90 and longitude between -180 and 180. "
    "Locations have no caption, so any extra text is ignored."
)

VENUE_TITLE_ADDRESS_SEPARATOR = "|"

VENUE_USAGE = (
    "<b>venue usage</b>\n"
    "Sends information about a venue into this chat as a real Telegram venue "
    "(a named place with a title and an address pinned on the map) instead of "
    "plain text. Pass the latitude and longitude in decimal degrees, then the "
    "title and the address separated by a vertical bar.\n"
    "Usage: <code>/venue &lt;latitude&gt; &lt;longitude&gt; &lt;title&gt; "
    "| &lt;address&gt;</code>\n"
    "Latitude must be between -90 and 90 and longitude between -180 and 180. "
    "Both the title and the address are required and must be non-empty."
)

POLL_OPTION_SEPARATOR = "|"

POLL_MIN_OPTIONS = 2

POLL_MAX_OPTIONS = 10

POLL_QUESTION_MAX_LENGTH = 300

POLL_OPTION_MAX_LENGTH = 100

POLL_USAGE = (
    "<b>poll usage</b>\n"
    "Sends a native poll into this chat as a real Telegram poll (an interactive "
    "question with tappable answer options) instead of plain text. Pass the "
    "question followed by the answer options, all separated by a vertical bar.\n"
    "Usage: <code>/poll &lt;question&gt; | &lt;option&gt; | &lt;option&gt; "
    "[| &lt;option&gt; ...]</code>\n"
    "Provide 2-10 options. The question is limited to 300 characters and each "
    "option to 100 characters; the question and every option may contain spaces "
    "and must be non-empty."
)

CONTACT_NAME_SEPARATOR = "|"

CONTACT_USAGE = (
    "<b>contact usage</b>\n"
    "Sends a phone contact into this chat as a real Telegram contact (a name "
    "with a phone number that can be saved to the address book) instead of "
    "plain text. Pass the phone number first, then the contact's first name; an "
    "optional last name follows after a vertical bar.\n"
    "Usage: <code>/contact &lt;phone_number&gt; &lt;first_name&gt; "
    "[| &lt;last_name&gt;]</code>\n"
    "The phone number and the first name are required and must be non-empty. "
    "The first name may contain spaces; the last name is optional."
)

DICE_EMOJI = ("🎲", "🎯", "🏀", "⚽", "🎳", "🎰")

DICE_USAGE = (
    "<b>dice usage</b>\n"
    "Sends an animated dice into this chat as a real Telegram dice (an animated "
    "emoji that shows a random value) instead of plain text. The rolled value "
    "is chosen by Telegram.\n"
    "Usage: <code>/dice [emoji]</code>\n"
    "Without an emoji a 🎲 die is sent. The optional emoji must be one of: "
    + " ".join(DICE_EMOJI)
    + "."
)

CHAT_ACTION_USAGE = (
    "<b>chataction usage</b>\n"
    "Shows a chat action (a transient status like \"typing…\") in this chat via "
    "the Telegram <code>sendChatAction</code> method. The status clears itself "
    "after about five seconds or when the bot next posts a message.\n"
    "Usage: <code>/chataction [action]</code>\n"
    "Without an argument a <code>typing</code> status is shown. The optional "
    "action must be one of: " + ", ".join(CHAT_ACTIONS) + "."
)

MESSAGE_DRAFT_USAGE = (
    "<b>messagedraft usage</b>\n"
    "Streams an ephemeral message draft into this private chat via the Telegram "
    "<code>sendMessageDraft</code> method. The draft is a temporary ~30-second "
    "preview and is not a persisted message; this method only works in private "
    "chats.\n"
    "Usage: <code>/messagedraft [text]</code>\n"
    "Without text a \"Thinking…\" placeholder is shown. The optional text is "
    f"limited to {MESSAGE_DRAFT_TEXT_LIMIT} characters."
)

CHECKLIST_TASK_SEPARATOR = "|"

CHECKLIST_TITLE_MAX_LENGTH = 255

CHECKLIST_TASK_MAX_LENGTH = 100

CHECKLIST_MIN_TASKS = 1

CHECKLIST_MAX_TASKS = 30

CHECKLIST_USAGE = (
    "<b>checklist usage</b>\n"
    "Sends a checklist into this chat as a real Telegram checklist (a titled "
    "list of tasks recipients can tick off) instead of plain text. This method "
    "sends on behalf of a connected business account, so the bot must be "
    "connected to one and you must pass that live business connection id first. "
    "Then pass the checklist title followed by the tasks, all separated by a "
    "vertical bar.\n"
    "Usage: <code>/checklist &lt;business_connection_id&gt; &lt;title&gt; "
    "| &lt;task&gt; [| &lt;task&gt; ...]</code>\n"
    "Provide 1-30 tasks. The title is limited to 255 characters and each task "
    "to 100 characters; the title and every task may contain spaces and must be "
    "non-empty."
)

USER_PROFILE_PHOTOS_USAGE = (
    "<b>userprofilephotos usage</b>\n"
    "Fetches the profile photos of a Telegram user and lists their "
    "<code>file_id</code> values and dimensions. No special bot permissions are "
    "needed; Telegram may return an error when the user has restricted profile "
    "photo visibility in their privacy settings.\n"
    "Usage: <code>/userprofilephotos &lt;user_id&gt; [offset] [limit]</code>\n"
    "The <code>user_id</code> is required. The optional <code>offset</code> "
    "skips the first N photos (default 0) and the optional <code>limit</code> "
    f"caps the number of photos returned (1-{GET_USER_PROFILE_PHOTOS_MAX_LIMIT}, "
    f"default {GET_USER_PROFILE_PHOTOS_MAX_LIMIT})."
)

REACT_BIG_KEYWORD = "big"

REACT_USAGE = (
    "<b>react usage</b>\n"
    "Sets a reaction on a message in this chat via the Telegram "
    "<code>setMessageReaction</code> method. The bot must be able to read the "
    "message; service messages cannot be reacted to. Pass the target message id "
    "and the reaction emoji. To remove all bot reactions from a message omit the "
    "emoji. Append <code>big</code> to use the big animation.\n"
    "Usage: <code>/react &lt;message_id&gt; [emoji] [big]</code>\n"
    "The emoji must be one of the standard Telegram reaction emoji. "
    "Non-premium bots can set at most one reaction per message."
)

MEDIA_GROUP_CAPTION_LIMIT = 1024

MEDIA_GROUP_MIN_ITEMS = 2

MEDIA_GROUP_MAX_ITEMS = 10

MEDIA_GROUP_CAPTION_KEYWORD = "caption"

MEDIA_GROUP_TYPES = {
    "photo": InputMediaPhoto,
    "video": InputMediaVideo,
    "document": InputMediaDocument,
    "audio": InputMediaAudio,
}

MEDIA_GROUP_USAGE = (
    "<b>mediagroup usage</b>\n"
    "Sends several media items into this chat as a single album (media group) "
    "instead of separate messages. All items must be of the same type. Pass "
    "HTTP(S) URLs Telegram can fetch or file_ids of media already on Telegram "
    "servers.\n"
    "Usage: <code>/mediagroup &lt;type&gt; &lt;url_or_file_id&gt; "
    "&lt;url_or_file_id&gt; [&lt;url_or_file_id&gt; ...] [caption &lt;text&gt;]</code>\n"
    "Type is one of photo, video, document or audio. Provide 2-10 items. The "
    "optional caption follows the literal word <code>caption</code> and is "
    "applied to the album (its first item); it is limited to 1024 characters."
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
        "/deletewebhook - Delete webhook before polling/local Bot API switch (restricted)\n"
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
        "/videonote - Send a rounded square video message (video note) into this chat (admin only)\n"
        "/animation - Send an animation (GIF/soundless video) into this chat (admin only)\n"
        "/voice - Send a voice message into this chat as a playable audio clip (admin only)\n"
        "/paidmedia - Send a paid photo into this chat priced in Telegram Stars (admin only)\n"
        "/location - Send a point on the map into this chat as a location (admin only)\n"
        "/venue - Send a venue (named place with title and address) into this chat (admin only)\n"
        "/poll - Send a native poll (question with answer options) into this chat (admin only)\n"
        "/contact - Send a phone contact (name and phone number) into this chat (admin only)\n"
        "/dice - Send an animated dice (random value) into this chat (admin only)\n"
        "/chataction - Show a chat action (e.g. typing…) in this chat (admin only)\n"
        "/messagedraft - Stream an ephemeral message draft into this private chat (admin only)\n"
        "/checklist - Send a checklist (titled list of tasks) into this chat via a business connection (admin only)\n"
        "/mediagroup - Send several media items into this chat as an album (admin only)\n"
        "/userprofilephotos - Fetch profile photos of a Telegram user (admin only)\n"
        "/react - Set or remove a reaction on a message in this chat (admin only)\n"
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

@router.message(Command("videonote"))
async def cmd_video_note(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    video_note = _parse_video_note_args(message.text or "")
    if video_note is None:
        await message.answer(VIDEO_NOTE_USAGE, parse_mode="HTML")
        return

    try:
        await perform_send_video_note(
            message.bot,
            chat_id=message.chat.id,
            video_note=video_note,
        )
    except TelegramAPIError as exc:
        await message.answer(f"Could not send the video note: {exc}")
        return

    await message.answer("Sent video note.")

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

@router.message(Command("location"))
async def cmd_location(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_location_args(message.text or "")
    if parsed is None:
        await message.answer(LOCATION_USAGE, parse_mode="HTML")
        return

    latitude, longitude = parsed
    if not LOCATION_MIN_LATITUDE <= latitude <= LOCATION_MAX_LATITUDE:
        await message.answer(
            f"Latitude must be between {LOCATION_MIN_LATITUDE} and "
            f"{LOCATION_MAX_LATITUDE}."
        )
        return

    if not LOCATION_MIN_LONGITUDE <= longitude <= LOCATION_MAX_LONGITUDE:
        await message.answer(
            f"Longitude must be between {LOCATION_MIN_LONGITUDE} and "
            f"{LOCATION_MAX_LONGITUDE}."
        )
        return

    try:
        await perform_send_location(
            message.bot,
            chat_id=message.chat.id,
            latitude=latitude,
            longitude=longitude,
        )
    except TelegramAPIError as exc:
        await message.answer(f"Could not send the location: {exc}")
        return

    await message.answer("Sent location.")

@router.message(Command("venue"))
async def cmd_venue(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_venue_args(message.text or "")
    if parsed is None:
        await message.answer(VENUE_USAGE, parse_mode="HTML")
        return

    latitude, longitude, title, address = parsed
    if not LOCATION_MIN_LATITUDE <= latitude <= LOCATION_MAX_LATITUDE:
        await message.answer(
            f"Latitude must be between {LOCATION_MIN_LATITUDE} and "
            f"{LOCATION_MAX_LATITUDE}."
        )
        return

    if not LOCATION_MIN_LONGITUDE <= longitude <= LOCATION_MAX_LONGITUDE:
        await message.answer(
            f"Longitude must be between {LOCATION_MIN_LONGITUDE} and "
            f"{LOCATION_MAX_LONGITUDE}."
        )
        return

    try:
        await perform_send_venue(
            message.bot,
            chat_id=message.chat.id,
            latitude=latitude,
            longitude=longitude,
            title=title,
            address=address,
        )
    except TelegramAPIError as exc:
        await message.answer(f"Could not send the venue: {exc}")
        return

    await message.answer("Sent venue.")

@router.message(Command("poll"))
async def cmd_poll(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_poll_args(message.text or "")
    if parsed is None:
        await message.answer(POLL_USAGE, parse_mode="HTML")
        return

    question, options = parsed
    if len(question) > POLL_QUESTION_MAX_LENGTH:
        await message.answer(
            f"Question is too long: {len(question)} characters "
            f"(max {POLL_QUESTION_MAX_LENGTH})."
        )
        return

    if not POLL_MIN_OPTIONS <= len(options) <= POLL_MAX_OPTIONS:
        await message.answer(
            f"A poll needs between {POLL_MIN_OPTIONS} and "
            f"{POLL_MAX_OPTIONS} options."
        )
        return

    too_long = next((opt for opt in options if len(opt) > POLL_OPTION_MAX_LENGTH), None)
    if too_long is not None:
        await message.answer(
            f"Option is too long: {len(too_long)} characters "
            f"(max {POLL_OPTION_MAX_LENGTH})."
        )
        return

    try:
        await perform_send_poll(
            message.bot,
            chat_id=message.chat.id,
            question=question,
            options=options,
        )
    except TelegramAPIError as exc:
        await message.answer(f"Could not send the poll: {exc}")
        return

    await message.answer(f"Sent poll with {len(options)} options.")

@router.message(Command("contact"))
async def cmd_contact(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_contact_args(message.text or "")
    if parsed is None:
        await message.answer(CONTACT_USAGE, parse_mode="HTML")
        return

    phone_number, first_name, last_name = parsed
    try:
        await perform_send_contact(
            message.bot,
            chat_id=message.chat.id,
            phone_number=phone_number,
            first_name=first_name,
            last_name=last_name,
        )
    except TelegramAPIError as exc:
        await message.answer(f"Could not send the contact: {exc}")
        return

    await message.answer("Sent contact.")

@router.message(Command("dice"))
async def cmd_dice(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_dice_args(message.text or "")
    if parsed is None:
        await message.answer(DICE_USAGE, parse_mode="HTML")
        return

    (emoji,) = parsed
    try:
        await perform_send_dice(
            message.bot,
            chat_id=message.chat.id,
            emoji=emoji,
        )
    except TelegramAPIError as exc:
        await message.answer(f"Could not send the dice: {exc}")
        return

    await message.answer("Sent dice.")

@router.message(Command("chataction"))
async def cmd_chat_action(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_chat_action_args(message.text or "")
    if parsed is None:
        await message.answer(CHAT_ACTION_USAGE, parse_mode="HTML")
        return

    (action,) = parsed
    try:
        await perform_send_chat_action(
            message.bot,
            chat_id=message.chat.id,
            action=action,
        )
    except SendChatActionError:
        await message.answer(CHAT_ACTION_USAGE, parse_mode="HTML")
        return
    except TelegramAPIError as exc:
        await message.answer(f"Could not show the chat action: {exc}")
        return

    await message.answer(f"Showed the {action} chat action.")

@router.message(Command("messagedraft"))
async def cmd_message_draft(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    text = _parse_message_draft_args(message.text or "")
    if len(text) > MESSAGE_DRAFT_TEXT_LIMIT:
        await message.answer(
            f"Draft text is too long: {len(text)} characters "
            f"(max {MESSAGE_DRAFT_TEXT_LIMIT})."
        )
        return

    # Message ids are positive, so this satisfies the non-zero draft_id rule.
    draft_id = message.message_id or 1
    try:
        await perform_send_message_draft(
            message.bot,
            chat_id=message.chat.id,
            draft_id=draft_id,
            text=text,
        )
    except SendMessageDraftError as exc:
        await message.answer(f"Could not send the message draft: {exc}")
        return

    await message.answer(
        "Sent message draft." if text else "Sent message draft (Thinking… placeholder)."
    )

@router.message(Command("checklist"))
async def cmd_checklist(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_checklist_args(message.text or "")
    if parsed is None:
        await message.answer(CHECKLIST_USAGE, parse_mode="HTML")
        return

    business_connection_id, title, tasks = parsed
    if len(title) > CHECKLIST_TITLE_MAX_LENGTH:
        await message.answer(
            f"Title is too long: {len(title)} characters "
            f"(max {CHECKLIST_TITLE_MAX_LENGTH})."
        )
        return

    if not CHECKLIST_MIN_TASKS <= len(tasks) <= CHECKLIST_MAX_TASKS:
        await message.answer(
            f"A checklist needs between {CHECKLIST_MIN_TASKS} and "
            f"{CHECKLIST_MAX_TASKS} tasks."
        )
        return

    too_long = next((task for task in tasks if len(task) > CHECKLIST_TASK_MAX_LENGTH), None)
    if too_long is not None:
        await message.answer(
            f"Task is too long: {len(too_long)} characters "
            f"(max {CHECKLIST_TASK_MAX_LENGTH})."
        )
        return

    checklist = {
        "title": title,
        "tasks": [
            {"id": index, "text": task} for index, task in enumerate(tasks, start=1)
        ],
    }
    try:
        await perform_send_checklist(
            message.bot,
            business_connection_id=business_connection_id,
            chat_id=message.chat.id,
            checklist=checklist,
        )
    except SendChecklistError as exc:
        await message.answer(f"Could not send the checklist: {exc}")
        return

    await message.answer(f"Sent checklist with {len(tasks)} tasks.")

@router.message(Command("userprofilephotos"))
async def cmd_user_profile_photos(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_user_profile_photos_args(message.text or "")
    if parsed is None:
        await message.answer(USER_PROFILE_PHOTOS_USAGE, parse_mode="HTML")
        return

    user_id, offset, limit = parsed

    if limit is not None and not (
        GET_USER_PROFILE_PHOTOS_MIN_LIMIT <= limit <= GET_USER_PROFILE_PHOTOS_MAX_LIMIT
    ):
        await message.answer(
            f"Limit must be between {GET_USER_PROFILE_PHOTOS_MIN_LIMIT} and "
            f"{GET_USER_PROFILE_PHOTOS_MAX_LIMIT}."
        )
        return

    try:
        result = await fetch_user_profile_photos(
            message.bot,
            user_id=user_id,
            offset=offset,
            limit=limit,
        )
    except TelegramAPIError as exc:
        await message.answer(f"Could not fetch user profile photos: {exc}")
        return

    await message.answer(
        format_user_profile_photos(result, user_id), parse_mode="HTML"
    )


@router.message(Command("react"))
async def cmd_react(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_react_args(message.text or "")
    if parsed is None:
        await message.answer(REACT_USAGE, parse_mode="HTML")
        return

    message_id, emoji, is_big = parsed

    if emoji is not None and emoji not in REACTION_EMOJI:
        await message.answer(
            f"Unsupported reaction emoji: {emoji!r}. "
            "Use one of the standard Telegram reaction emoji or omit the emoji "
            "to remove all reactions."
        )
        return

    reaction = None
    if emoji is not None:
        from aiogram.types import ReactionTypeEmoji

        reaction = [ReactionTypeEmoji(emoji=emoji)]

    try:
        await perform_set_message_reaction(
            message.bot,
            chat_id=message.chat.id,
            message_id=message_id,
            reaction=reaction,
            is_big=is_big if is_big else None,
        )
    except TelegramAPIError as exc:
        await message.answer(f"Could not set the reaction: {exc}")
        return

    if emoji is not None:
        await message.answer(f"Set reaction {emoji} on message {message_id}.")
    else:
        await message.answer(f"Removed reactions from message {message_id}.")


@router.message(Command("mediagroup"))
async def cmd_media_group(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_media_group_args(message.text or "")
    if parsed is None:
        await message.answer(MEDIA_GROUP_USAGE, parse_mode="HTML")
        return

    media_type, references, caption = parsed
    if media_type not in MEDIA_GROUP_TYPES:
        await message.answer(
            "Unsupported media type. Use one of: "
            + ", ".join(sorted(MEDIA_GROUP_TYPES))
            + "."
        )
        return

    if not MEDIA_GROUP_MIN_ITEMS <= len(references) <= MEDIA_GROUP_MAX_ITEMS:
        await message.answer(
            f"A media group needs between {MEDIA_GROUP_MIN_ITEMS} and "
            f"{MEDIA_GROUP_MAX_ITEMS} items."
        )
        return

    if caption is not None and len(caption) > MEDIA_GROUP_CAPTION_LIMIT:
        await message.answer(
            f"Caption is too long: {len(caption)} characters "
            f"(max {MEDIA_GROUP_CAPTION_LIMIT})."
        )
        return

    media = _build_media_group_items(media_type, references, caption)

    try:
        await perform_send_media_group(
            message.bot,
            chat_id=message.chat.id,
            media=media,
        )
    except TelegramAPIError as exc:
        await message.answer(f"Could not send the media group: {exc}")
        return

    await message.answer(
        f"Sent media group of {len(references)} items with caption."
        if caption
        else f"Sent media group of {len(references)} items."
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


def _parse_video_note_args(text: str):
    """Parse ``/videonote`` arguments into the video note reference.

    Splits the raw command text into the command and the video note reference
    (a ``file_id``; Telegram does not support sending video notes by URL).
    Video notes have no caption, so any extra tokens are ignored. Returns
    ``None`` when no reference is provided so the caller can show usage.
    """
    parts = (text or "").split()
    if len(parts) < 2:
        return None

    video_note = parts[1].strip()
    if not video_note:
        return None

    return video_note


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


def _parse_location_args(text: str):
    """Parse ``/location`` arguments into ``(latitude, longitude)``.

    Splits the raw command text into the command, the ``latitude`` and the
    ``longitude`` given in decimal degrees. Locations have no caption, so any
    extra tokens are ignored. Returns ``None`` when either coordinate is missing
    or is not a number so the caller can show usage. The caller validates the
    latitude/longitude ranges against Telegram's accepted bounds.
    """
    parts = (text or "").split()
    if len(parts) < 3:
        return None

    try:
        latitude = float(parts[1])
        longitude = float(parts[2])
    except ValueError:
        return None

    return latitude, longitude


def _parse_venue_args(text: str):
    """Parse ``/venue`` args into ``(latitude, longitude, title, address)``.

    Splits the raw command text into the command, the ``latitude`` and the
    ``longitude`` given in decimal degrees, followed by the venue ``title`` and
    ``address``. Both the title and the address may contain spaces, so they are
    taken from the remainder of the message and separated by a vertical bar
    (``|``). Returns ``None`` when a coordinate is missing or not a number, when
    the separator is absent, or when either the title or the address is empty so
    the caller can show usage. The caller validates the latitude/longitude
    ranges against Telegram's accepted bounds.
    """
    parts = (text or "").split(maxsplit=3)
    if len(parts) < 4:
        return None

    try:
        latitude = float(parts[1])
        longitude = float(parts[2])
    except ValueError:
        return None

    remainder = parts[3]
    if VENUE_TITLE_ADDRESS_SEPARATOR not in remainder:
        return None

    title, _, address = remainder.partition(VENUE_TITLE_ADDRESS_SEPARATOR)
    title = title.strip()
    address = address.strip()
    if not title or not address:
        return None

    return latitude, longitude, title, address


def _parse_poll_args(text: str):
    """Parse ``/poll`` args into ``(question, options)``.

    Splits the raw command text into the command and the remainder, then splits
    the remainder on the vertical bar (``|``) so the first segment is the poll
    ``question`` and the following segments are the answer ``options``. Every
    segment is trimmed of surrounding whitespace but keeps any internal spaces.
    Returns ``None`` when there are no arguments, when the separator is missing
    so no option is given, or when the question or any option is empty, so the
    caller can show usage. The caller validates the question/option lengths and
    the 2-10 option count against Telegram's limits.
    """
    parts = (text or "").split(maxsplit=1)
    if len(parts) < 2:
        return None

    segments = [segment.strip() for segment in parts[1].split(POLL_OPTION_SEPARATOR)]
    question = segments[0]
    options = segments[1:]
    if not question or not options:
        return None

    if any(not option for option in options):
        return None

    return question, options


def _parse_contact_args(text: str):
    """Parse ``/contact`` args into ``(phone_number, first_name, last_name)``.

    Splits the raw command text into the command, the ``phone_number`` (a single
    whitespace-delimited token) and the remainder holding the contact's
    ``first_name`` and an optional ``last_name``. The first name may contain
    spaces, so the remainder is taken whole; an optional last name is split off
    after the first vertical bar (``|``). Returns ``None`` when the phone number
    or the first name is missing or empty so the caller can show usage. When no
    separator is present the whole remainder is the first name and the last name
    is ``None``; an empty last-name segment also yields ``None`` for the last
    name.
    """
    parts = (text or "").split(maxsplit=2)
    if len(parts) < 3:
        return None

    phone_number = parts[1].strip()
    remainder = parts[2]
    if CONTACT_NAME_SEPARATOR in remainder:
        first_part, _, last_part = remainder.partition(CONTACT_NAME_SEPARATOR)
        first_name = first_part.strip()
        last_name = last_part.strip() or None
    else:
        first_name = remainder.strip()
        last_name = None

    if not phone_number or not first_name:
        return None

    return phone_number, first_name, last_name


def _parse_dice_args(text: str):
    """Parse ``/dice`` args into a single-element ``(emoji,)`` tuple.

    Splits the raw command text into the command and an optional emoji token.
    With no argument the emoji is ``None`` so Telegram sends its default ``🎲``
    die. When a single token is given it must be one of the supported dice emoji
    (:data:`DICE_EMOJI`); the parsed emoji is returned wrapped in a one-element
    tuple so the caller can distinguish "no argument" (``(None,)``) from an
    invalid request. Returns ``None`` when an unsupported emoji or more than one
    argument is supplied so the caller can show usage.
    """
    parts = (text or "").split()
    if len(parts) == 1:
        return (None,)
    if len(parts) > 2:
        return None

    emoji = parts[1]
    if emoji not in DICE_EMOJI:
        return None

    return (emoji,)


def _parse_chat_action_args(text: str):
    """Parse ``/chataction`` args into a single-element ``(action,)`` tuple.

    Splits the raw command text into the command and an optional action token.
    With no argument the action defaults to ``typing``. When a single token is
    given it must be one of the supported chat actions (:data:`CHAT_ACTIONS`);
    the parsed action is returned wrapped in a one-element tuple. Returns
    ``None`` when an unsupported action or more than one argument is supplied so
    the caller can show usage.
    """
    parts = (text or "").split()
    if len(parts) == 1:
        return ("typing",)
    if len(parts) > 2:
        return None

    action = parts[1]
    if action not in CHAT_ACTIONS:
        return None

    return (action,)


def _parse_message_draft_args(text: str) -> str:
    """Parse ``/messagedraft`` args into the optional draft text.

    Strips the command token and returns the remainder as the draft text,
    preserving any internal spaces and trimming the surrounding whitespace. The
    text is optional, so an empty string is returned when no argument is given;
    Telegram shows a "Thinking…" placeholder for empty draft text. The caller
    validates the text length against Telegram's limit.
    """
    parts = (text or "").split(maxsplit=1)
    if len(parts) < 2:
        return ""
    return parts[1].strip()


def _parse_checklist_args(text: str):
    """Parse ``/checklist`` args into ``(business_connection_id, title, tasks)``.

    Splits the raw command text into the command, the ``business_connection_id``
    (a single whitespace-delimited token) and the remainder, then splits the
    remainder on the vertical bar (``|``) so the first segment is the checklist
    ``title`` and the following segments are the task texts. Every segment is
    trimmed of surrounding whitespace but keeps any internal spaces. Returns
    ``None`` when the business connection id is missing, when the separator is
    missing so no task is given, or when the title or any task is empty, so the
    caller can show usage. The caller validates the title/task lengths and the
    1-30 task count against Telegram's limits.
    """
    parts = (text or "").split(maxsplit=2)
    if len(parts) < 3:
        return None

    business_connection_id = parts[1].strip()
    segments = [segment.strip() for segment in parts[2].split(CHECKLIST_TASK_SEPARATOR)]
    title = segments[0]
    tasks = segments[1:]
    if not business_connection_id or not title or not tasks:
        return None

    if any(not task for task in tasks):
        return None

    return business_connection_id, title, tasks


def _parse_user_profile_photos_args(text: str):
    """Parse ``/userprofilephotos`` args into ``(user_id, offset, limit)``.

    Splits the raw command text into the command, the required integer
    ``user_id`` and optional integer ``offset`` and ``limit`` values. Returns
    ``None`` when ``user_id`` is missing or not a valid integer so the caller
    can show usage. ``offset`` and ``limit`` default to ``None`` so the service
    layer can pass them unchanged to Telegram (Telegram ignores ``None`` values
    and uses its own defaults: offset 0, limit 100). The caller validates the
    ``limit`` range (1-100) against Telegram's accepted bounds.
    """
    parts = (text or "").split()
    if len(parts) < 2:
        return None

    try:
        user_id = int(parts[1])
    except ValueError:
        return None

    offset = None
    limit = None

    if len(parts) >= 3:
        try:
            offset = int(parts[2])
        except ValueError:
            return None

    if len(parts) >= 4:
        try:
            limit = int(parts[3])
        except ValueError:
            return None

    return user_id, offset, limit


def _parse_react_args(text: str):
    """Parse ``/react`` args into ``(message_id, emoji, is_big)``.

    Splits the raw command text into the command, the required integer
    ``message_id``, an optional reaction emoji and an optional ``big`` keyword.
    Returns ``None`` when ``message_id`` is missing or not a valid integer so
    the caller can show usage. The emoji defaults to ``None``, which removes
    all bot reactions from the message. The ``big`` flag defaults to
    ``False``. The caller validates the emoji against the supported set.
    """
    parts = (text or "").split()
    if len(parts) < 2:
        return None

    try:
        message_id = int(parts[1])
    except ValueError:
        return None

    rest = parts[2:]

    is_big = False
    if rest and rest[-1].strip().lower() == REACT_BIG_KEYWORD:
        is_big = True
        rest = rest[:-1]

    emoji = rest[0] if rest else None

    return message_id, emoji, is_big


def _parse_media_group_args(text: str):
    """Parse ``/mediagroup`` args into ``(media_type, references, caption)``.

    Splits the raw command text into the command, the media ``type`` and the
    media references (URLs or ``file_id`` values). An optional single album
    caption follows the literal keyword ``caption``; everything after it is
    joined back into the caption text, which may contain spaces. Returns
    ``None`` when the type or at least one media reference is missing so the
    caller can show usage. The caller validates the type, the 2-10 item count
    and the caption length against Telegram's limits.
    """
    parts = (text or "").split()
    if len(parts) < 2:
        return None

    media_type = parts[1].strip().lower()
    rest = parts[2:]

    caption = None
    lowered = [token.lower() for token in rest]
    if MEDIA_GROUP_CAPTION_KEYWORD in lowered:
        keyword_index = lowered.index(MEDIA_GROUP_CAPTION_KEYWORD)
        references = rest[:keyword_index]
        caption = " ".join(rest[keyword_index + 1:]).strip() or None
    else:
        references = rest

    if not references:
        return None

    return media_type, references, caption


def _build_media_group_items(media_type: str, references: list[str], caption):
    """Build the typed ``InputMedia`` album items for ``send_media_group``.

    Maps the validated ``media_type`` to its aiogram ``InputMedia`` class and
    wraps each reference in an item of that type. The single album caption is
    expressed by attaching ``caption`` to the first item only, matching how
    Telegram renders an album caption.
    """
    media_class = MEDIA_GROUP_TYPES[media_type]
    items = []
    for index, reference in enumerate(references):
        if index == 0 and caption is not None:
            items.append(media_class(media=reference, caption=caption))
        else:
            items.append(media_class(media=reference))
    return items
