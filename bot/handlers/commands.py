import re

from aiogram import Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.types import (
    BotCommand,
    BotCommandScopeAllChatAdministrators,
    BotCommandScopeAllGroupChats,
    BotCommandScopeAllPrivateChats,
    BotCommandScopeChat,
    BotCommandScopeChatAdministrators,
    BotCommandScopeChatMember,
    BotCommandScopeDefault,
    ChatPermissions,
    InputMediaAudio,
    InputMediaDocument,
    InputMediaPhoto,
    InputMediaVideo,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    MenuButtonCommands,
    MenuButtonDefault,
    MenuButtonWebApp,
    Message,
    WebAppInfo,
)
from bot.config import settings
from bot.services.close import perform_close
from bot.services.approve_chat_join_request import (
    ApproveChatJoinRequestError,
    format_approve_chat_join_request_result,
    perform_approve_chat_join_request,
)
from bot.services.decline_chat_join_request import (
    DeclineChatJoinRequestError,
    format_decline_chat_join_request_result,
    perform_decline_chat_join_request,
)
from bot.services.delete_chat_photo import (
    format_delete_chat_photo_result,
    perform_delete_chat_photo,
)
from bot.services.set_chat_description import (
    SET_CHAT_DESCRIPTION_LIMIT,
    format_set_chat_description_result,
    perform_set_chat_description,
)
from bot.services.set_chat_title import (
    SET_CHAT_TITLE_LIMIT,
    format_set_chat_title_result,
    perform_set_chat_title,
)
from bot.services.set_chat_menu_button import (
    format_set_chat_menu_button_result,
    perform_set_chat_menu_button,
)
from bot.services.set_my_commands import (
    format_set_my_commands_result,
    perform_set_my_commands,
)
from bot.services.set_my_name import (
    SET_MY_NAME_LIMIT,
    SetMyNameValidationError,
    format_set_my_name_result,
    perform_set_my_name,
)
from bot.services.set_my_description import (
    SET_MY_DESCRIPTION_LIMIT,
    SetMyDescriptionValidationError,
    format_set_my_description_result,
    perform_set_my_description,
)
from bot.services.set_my_short_description import (
    SET_MY_SHORT_DESCRIPTION_LIMIT,
    SetMyShortDescriptionValidationError,
    format_set_my_short_description_result,
    perform_set_my_short_description,
)
from bot.services.get_my_name import (
    format_get_my_name_result,
    perform_get_my_name,
)
from bot.services.get_my_description import (
    format_get_my_description_result,
    perform_get_my_description,
)
from bot.services.get_my_short_description import (
    format_get_my_short_description_result,
    perform_get_my_short_description,
)
from bot.services.get_my_commands import (
    format_get_my_commands_result,
    perform_get_my_commands,
)
from bot.services.delete_my_commands import (
    format_delete_my_commands_result,
    perform_delete_my_commands,
)
from bot.services.set_chat_photo import (
    format_set_chat_photo_result,
    perform_set_chat_photo,
)
from bot.services.set_my_profile_photo import (
    SetMyProfilePhotoError,
    format_set_my_profile_photo_result,
    perform_set_my_profile_photo,
)
from bot.services.remove_my_profile_photo import (
    RemoveMyProfilePhotoError,
    format_remove_my_profile_photo_result,
    perform_remove_my_profile_photo,
)
from bot.services.set_chat_sticker_set import (
    format_set_chat_sticker_set_result,
    perform_set_chat_sticker_set,
)
from bot.services.delete_chat_sticker_set import (
    format_delete_chat_sticker_set_result,
    perform_delete_chat_sticker_set,
)
from bot.services.copy_message import perform_copy_message
from bot.services.copy_messages import perform_copy_messages
from bot.services.forward_message import perform_forward_message
from bot.services.forward_messages import perform_forward_messages
from bot.services.log_out import perform_log_out
from bot.services.export_chat_invite_link import (
    format_export_chat_invite_link_result,
    perform_export_chat_invite_link,
)
from bot.services.leave_chat import format_leave_chat_result, perform_leave_chat
from bot.services.create_chat_invite_link import (
    CreateChatInviteLinkError,
    format_create_chat_invite_link_result,
    perform_create_chat_invite_link,
)
from bot.services.create_chat_subscription_invite_link import (
    CreateChatSubscriptionInviteLinkError,
    format_create_chat_subscription_invite_link_result,
    perform_create_chat_subscription_invite_link,
)
from bot.services.edit_chat_invite_link import (
    EditChatInviteLinkError,
    format_edit_chat_invite_link_result,
    perform_edit_chat_invite_link,
)
from bot.services.revoke_chat_invite_link import (
    RevokeChatInviteLinkError,
    format_revoke_chat_invite_link_result,
    perform_revoke_chat_invite_link,
)
from bot.services.edit_chat_subscription_invite_link import (
    EditChatSubscriptionInviteLinkError,
    format_edit_chat_subscription_invite_link_result,
    perform_edit_chat_subscription_invite_link,
)
from bot.services.promote_chat_member import (
    format_promote_result,
    perform_promote_chat_member,
)
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
from bot.services.get_user_profile_audios import (
    GET_USER_PROFILE_AUDIOS_MAX_LIMIT,
    GET_USER_PROFILE_AUDIOS_MIN_LIMIT,
    fetch_user_profile_audios,
    format_user_profile_audios,
)
from bot.services.get_user_profile_photos import (
    GET_USER_PROFILE_PHOTOS_MAX_LIMIT,
    GET_USER_PROFILE_PHOTOS_MIN_LIMIT,
    fetch_user_profile_photos,
    format_user_profile_photos,
)
from bot.services.get_chat import format_get_chat_result, perform_get_chat
from bot.services.get_chat_administrators import (
    format_get_chat_administrators_result,
    perform_get_chat_administrators,
)
from bot.services.get_forum_topic_icon_stickers import (
    GetForumTopicIconStickersError,
    format_forum_topic_icon_stickers,
    perform_get_forum_topic_icon_stickers,
)
from bot.services.create_forum_topic import (
    CreateForumTopicError,
    FORUM_TOPIC_NAME_LIMIT as CREATE_FORUM_TOPIC_NAME_LIMIT,
    format_create_forum_topic_result,
    perform_create_forum_topic,
)
from bot.services.edit_forum_topic import (
    EditForumTopicError,
    FORUM_TOPIC_NAME_LIMIT,
    format_edit_forum_topic_result,
    perform_edit_forum_topic,
)
from bot.services.edit_general_forum_topic import (
    EditGeneralForumTopicError,
    GENERAL_FORUM_TOPIC_NAME_LIMIT,
    format_edit_general_forum_topic_result,
    perform_edit_general_forum_topic,
)
from bot.services.close_forum_topic import (
    CloseForumTopicError,
    format_close_forum_topic_result,
    perform_close_forum_topic,
)
from bot.services.close_general_forum_topic import (
    CloseGeneralForumTopicError,
    format_close_general_forum_topic_result,
    perform_close_general_forum_topic,
)
from bot.services.reopen_forum_topic import (
    ReopenForumTopicError,
    format_reopen_forum_topic_result,
    perform_reopen_forum_topic,
)
from bot.services.reopen_general_forum_topic import (
    ReopenGeneralForumTopicError,
    format_reopen_general_forum_topic_result,
    perform_reopen_general_forum_topic,
)
from bot.services.hide_general_forum_topic import (
    HideGeneralForumTopicError,
    format_hide_general_forum_topic_result,
    perform_hide_general_forum_topic,
)
from bot.services.unhide_general_forum_topic import (
    UnhideGeneralForumTopicError,
    format_unhide_general_forum_topic_result,
    perform_unhide_general_forum_topic,
)
from bot.services.delete_forum_topic import (
    DeleteForumTopicError,
    format_delete_forum_topic_result,
    perform_delete_forum_topic,
)
from bot.services.unpin_all_forum_topic_messages import (
    UnpinAllForumTopicMessagesError,
    format_unpin_all_forum_topic_messages_result,
    perform_unpin_all_forum_topic_messages,
)
from bot.services.unpin_all_general_forum_topic_messages import (
    UnpinAllGeneralForumTopicMessagesError,
    format_unpin_all_general_forum_topic_messages_result,
    perform_unpin_all_general_forum_topic_messages,
)
from bot.services.get_user_personal_chat_messages import (
    GET_USER_PERSONAL_CHAT_MESSAGES_MAX_LIMIT,
    GET_USER_PERSONAL_CHAT_MESSAGES_MIN_LIMIT,
    format_get_user_personal_chat_messages_result,
    perform_get_user_personal_chat_messages,
)
from bot.services.get_user_chat_boosts import (
    format_get_user_chat_boosts_result,
    perform_get_user_chat_boosts,
)
from bot.services.get_chat_member_count import (
    format_get_chat_member_count_result,
    perform_get_chat_member_count,
)
from bot.services.get_chat_member import (
    format_get_chat_member_result,
    perform_get_chat_member,
)
from bot.services.get_business_connection import (
    GetBusinessConnectionError,
    format_business_connection,
    perform_get_business_connection,
)
from bot.services.get_managed_bot_token import (
    GetManagedBotTokenError,
    format_managed_bot_token,
    perform_get_managed_bot_token,
)
from bot.services.get_managed_bot_access_settings import (
    GetManagedBotAccessSettingsError,
    format_managed_bot_access_settings,
    perform_get_managed_bot_access_settings,
)
from bot.services.set_managed_bot_access_settings import (
    SetManagedBotAccessSettingsError,
    format_set_managed_bot_access_settings_result,
    perform_set_managed_bot_access_settings,
)
from bot.services.replace_managed_bot_token import (
    ReplaceManagedBotTokenError,
    format_replaced_managed_bot_token,
    perform_replace_managed_bot_token,
)
from bot.services.set_message_reaction import (
    REACTION_EMOJI,
    perform_set_message_reaction,
)
from bot.services.set_chat_administrator_custom_title import (
    format_set_chat_administrator_custom_title_result,
    perform_set_chat_administrator_custom_title,
)
from bot.services.set_chat_member_tag import (
    format_set_chat_member_tag_result,
    perform_set_chat_member_tag,
)
from bot.services.set_user_emoji_status import perform_set_user_emoji_status
from bot.services.webhook_delete import delete_webhook
from bot.services.webhook_info import fetch_webhook_info, format_webhook_info
from bot.services.ban_chat_member import format_ban_result, perform_ban_chat_member
from bot.services.ban_chat_sender_chat import (
    format_ban_sender_chat_result,
    perform_ban_chat_sender_chat,
)
from bot.services.restrict_chat_member import (
    format_restrict_result,
    perform_restrict_chat_member,
)
from bot.services.set_chat_permissions import (
    format_set_chat_permissions_result,
    perform_set_chat_permissions,
)
from bot.services.unban_chat_member import (
    format_unban_result,
    perform_unban_chat_member,
)
from bot.services.unban_chat_sender_chat import (
    format_unban_sender_chat_result,
    perform_unban_chat_sender_chat,
)
from bot.services.unpin_chat_message import (
    format_unpin_chat_message_result,
    perform_unpin_chat_message,
)
from bot.services.unpin_all_chat_messages import (
    format_unpin_all_chat_messages_result,
    perform_unpin_all_chat_messages,
)
from bot.services.pin_chat_message import (
    format_pin_chat_message_result,
    perform_pin_chat_message,
)
from bot.utils.storage import storage
from bot.services.claude_proxy import ClaudeProxyClient

router = Router()

LOGOUT_CONFIRM_KEYWORD = "confirm"
CALLBACK_SETTINGS_REFRESH = "settings:refresh"
CALLBACK_MODEL_PREFIX = "model:set:"
CALLBACK_CLEAR_HISTORY = "history:clear"
CALLBACK_LOGOUT_CONFIRM = "admin:logout:confirm"
CALLBACK_CLOSE_CONFIRM = "admin:close:confirm"
CALLBACK_CANCEL = "action:cancel"
TELEGRAM_CALLBACK_DATA_LIMIT = 64

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

BUSINESS_CONNECTION_USAGE = (
    "<b>businessconnection usage</b>\n"
    "Fetches Telegram <code>getBusinessConnection</code> diagnostics for a "
    "connected business account. This is an admin-only surface because the "
    "response exposes business owner and lifecycle metadata.\n"
    "Usage: <code>/businessconnection &lt;business_connection_id&gt;</code>\n"
    "The id must come from a live business connection update or another "
    "trusted operator source. This command is unavailable unless "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code> contains the current chat."
)

MANAGED_BOT_TOKEN_USAGE = (
    "<b>managedbottoken usage</b>\n"
    "Fetches Telegram <code>getManagedBotToken</code> for a managed bot by "
    "its user id. This returns a live bot token, so the command is admin-only, "
    "disabled unless <code>TELEGRAM_ADMIN_CHAT_IDS</code> contains the current "
    "chat, and keeps the token out of structured logs.\n"
    "Usage: <code>/managedbottoken &lt;managed_bot_user_id&gt;</code>\n"
    "The id must come from a trusted <code>managed_bot</code> update, "
    "<code>managed_bot_created</code> message, or another operator-controlled "
    "source. Telegram allows only the manager/owner flow to access the token."
)

MANAGED_BOT_ACCESS_SETTINGS_USAGE = (
    "<b>managedbotaccess usage</b>\n"
    "Fetches Telegram <code>getManagedBotAccessSettings</code> for a managed "
    "bot by its user id. This exposes the bot access allowlist, so the command "
    "is admin-only, disabled unless <code>TELEGRAM_ADMIN_CHAT_IDS</code> "
    "contains the current chat, and keeps returned user objects out of "
    "structured logs.\n"
    "Usage: <code>/managedbotaccess &lt;managed_bot_user_id&gt;</code>\n"
    "The id must come from a trusted <code>managed_bot</code> update, "
    "<code>managed_bot_created</code> message, or another operator-controlled "
    "source. Telegram allows only the manager/owner flow to read these settings."
)

SET_MANAGED_BOT_ACCESS_SETTINGS_CONFIRM_KEYWORD = "confirm"

SET_MANAGED_BOT_ACCESS_SETTINGS_USAGE = (
    "<b>setmanagedbotaccess usage</b>\n"
    "Updates Telegram <code>setManagedBotAccessSettings</code> for a managed "
    "bot by its user id. This changes who can access the managed bot, so the "
    "command is admin-only, disabled unless "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code> contains the current chat, and keeps "
    "allowlist values out of structured logs.\n"
    "Usage: <code>/setmanagedbotaccess &lt;managed_bot_user_id&gt; "
    "&lt;restricted|open&gt; [added_user_id ...] confirm</code>\n"
    "Use <code>restricted</code> to limit access to the owner and listed users, "
    "or <code>open</code> to remove the access allowlist. The id must come "
    "from a trusted <code>managed_bot</code> update, "
    "<code>managed_bot_created</code> message, or another operator-controlled "
    "source."
)

SET_MANAGED_BOT_ACCESS_SETTINGS_WARNING = (
    "<b>setmanagedbotaccess confirmation required</b>\n"
    "This changes access settings for a Telegram managed bot. Before changing "
    "them, fetch the current state with <code>/managedbotaccess</code> so it "
    "can be restored if needed.\n"
    "Run <code>/setmanagedbotaccess &lt;managed_bot_user_id&gt; "
    "&lt;restricted|open&gt; [added_user_id ...] confirm</code> to proceed."
)

REPLACE_MANAGED_BOT_TOKEN_CONFIRM_KEYWORD = "confirm"

REPLACE_MANAGED_BOT_TOKEN_USAGE = (
    "<b>replacemanagedbottoken usage</b>\n"
    "Rotates Telegram <code>replaceManagedBotToken</code> for a managed bot by "
    "its user id and returns the newly issued token. This revokes the previous "
    "token, so the command is admin-only, disabled unless "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code> contains the current chat, and keeps "
    "token values out of structured logs.\n"
    "Usage: <code>/replacemanagedbottoken &lt;managed_bot_user_id&gt; "
    "confirm</code>\n"
    "The id must come from a trusted <code>managed_bot</code> update, "
    "<code>managed_bot_created</code> message, or another operator-controlled "
    "source. Telegram allows only the manager/owner flow to replace the token."
)

REPLACE_MANAGED_BOT_TOKEN_WARNING = (
    "<b>replacemanagedbottoken confirmation required</b>\n"
    "This rotates the token for a Telegram managed bot and returns the new "
    "credential in this admin chat. The previous token may stop working, so "
    "update deployments and secret stores immediately after success.\n"
    "Run <code>/replacemanagedbottoken &lt;managed_bot_user_id&gt; "
    "confirm</code> to proceed."
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

SET_EMOJI_STATUS_USAGE = (
    "<b>setemojistatus usage</b>\n"
    "Sets or removes the emoji status of a Telegram user who previously granted "
    "the bot permission to manage their emoji status via the Mini App method "
    "<code>requestEmojiStatusAccess</code>. "
    "Pass an empty string as the custom emoji ID to remove the current status. "
    "Without the user's explicit grant the call will fail with a Telegram error.\n"
    "Usage: <code>/setemojistatus &lt;user_id&gt; [custom_emoji_id]</code>\n"
    "The <code>user_id</code> is required. The optional "
    "<code>custom_emoji_id</code> is the custom emoji identifier to set; "
    "omit it or pass an empty string to remove the user's current emoji status."
)

USER_PROFILE_AUDIOS_USAGE = (
    "<b>userprofileaudios usage</b>\n"
    "Fetches the profile audios of a Telegram user and lists their "
    "<code>file_id</code> values, duration, performer and title. No special "
    "bot permissions are needed; Telegram may return an error when the user "
    "has restricted profile audio visibility in their privacy settings.\n"
    "Usage: <code>/userprofileaudios &lt;user_id&gt; [offset] [limit]</code>\n"
    "The <code>user_id</code> is required. The optional <code>offset</code> "
    "skips the first N audios (default 0) and the optional <code>limit</code> "
    f"caps the number of audios returned (1-{GET_USER_PROFILE_AUDIOS_MAX_LIMIT}, "
    f"default {GET_USER_PROFILE_AUDIOS_MAX_LIMIT})."
)

BAN_CHAT_MEMBER_USAGE = (
    "<b>banchatmember usage</b>\n"
    "Bans a user from the specified chat. The bot must be an administrator "
    "with the <code>can_restrict_members</code> right in the target chat.\n"
    "Usage: <code>/banchatmember &lt;chat_id&gt; &lt;user_id&gt; "
    "[until_date_unix] [revoke=true|false]</code>\n"
    "The <code>chat_id</code> and <code>user_id</code> are required. "
    "The optional <code>until_date_unix</code> is a Unix timestamp (seconds) "
    "at which the ban expires; Telegram ignores values less than 30 seconds "
    "or more than 366 days in the future (a permanent ban is used instead). "
    "Omit it or pass 0 for a permanent ban. "
    "The optional <code>revoke</code> flag (true/false) controls whether the "
    "user's messages are deleted; defaults to Telegram's behaviour (always "
    "revoked for supergroups/channels)."
)

BAN_CHAT_SENDER_CHAT_USAGE = (
    "<b>banchatsenderchat usage</b>\n"
    "Bans a channel chat from sending messages as itself into the specified "
    "supergroup or channel. The bot must be an administrator with the "
    "<code>can_restrict_members</code> right in the target chat. This command "
    "is deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/banchatsenderchat &lt;chat_id&gt; "
    "&lt;sender_chat_id&gt;</code>\n"
    "The <code>chat_id</code> is the target chat. The "
    "<code>sender_chat_id</code> is the channel chat to ban from posting as a "
    "sender chat."
)

UNBAN_CHAT_SENDER_CHAT_USAGE = (
    "<b>unbanchatsenderchat usage</b>\n"
    "Unbans a channel chat so it can send messages as itself into the "
    "specified supergroup or channel again. The bot must be an administrator "
    "with the <code>can_restrict_members</code> right in the target chat. "
    "This command is deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/unbanchatsenderchat &lt;chat_id&gt; "
    "&lt;sender_chat_id&gt;</code>\n"
    "The <code>chat_id</code> is the target chat. The "
    "<code>sender_chat_id</code> is the channel chat to unban from posting as "
    "a sender chat."
)

UNBAN_CHAT_MEMBER_USAGE = (
    "<b>unbanchatmember usage</b>\n"
    "Unbans a user from the specified group, supergroup or channel. The bot "
    "must be an administrator with the <code>can_restrict_members</code> right "
    "in the target chat. This command is deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/unbanchatmember &lt;chat_id&gt; &lt;user_id&gt; "
    "[only_if_banned=true|false]</code>\n"
    "The <code>chat_id</code> and <code>user_id</code> are required. The "
    "optional <code>only_if_banned</code> flag asks Telegram to unban the user "
    "only when the user is currently banned; omit it to use Telegram's default."
)

RESTRICT_CHAT_MEMBER_USAGE = (
    "<b>restrictchatmember usage</b>\n"
    "Restricts a user in the specified group or supergroup. The bot must be "
    "an administrator with the <code>can_restrict_members</code> right in the "
    "target chat. This command is deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/restrictchatmember &lt;chat_id&gt; &lt;user_id&gt; "
    "&lt;mute|readonly|unrestrict&gt; [until_date_unix] "
    "[independent=true|false]</code>\n"
    "Presets: <code>mute</code> denies sending messages; "
    "<code>readonly</code> allows text messages but denies media, polls, link "
    "previews, reactions, invites, pins and topic management; "
    "<code>unrestrict</code> restores common member permissions. Omit "
    "<code>until_date_unix</code> or pass 0 for a permanent restriction. "
    "Telegram treats values less than 30 seconds or more than 366 days in the "
    "future as permanent."
)

SET_CHAT_PERMISSIONS_USAGE = (
    "<b>setchatpermissions usage</b>\n"
    "Sets default permissions for all non-administrator members in the "
    "specified group or supergroup. The bot must be an administrator with the "
    "<code>can_restrict_members</code> right in the target chat. This command "
    "is deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/setchatpermissions &lt;chat_id&gt; "
    "&lt;closed|text|media|open&gt; [independent=true|false]</code>\n"
    "Presets: <code>closed</code> denies sending messages; "
    "<code>text</code> allows text messages only; <code>media</code> allows "
    "text and common media messages; <code>open</code> restores common member "
    "permissions including invites, pins and topic management. Telegram does "
    "not change administrator permissions with this method."
)

UNPIN_CHAT_MESSAGE_USAGE = (
    "<b>unpinchatmessage usage</b>\n"
    "Unpins a message from the specified group, supergroup or channel. The bot "
    "must be an administrator with <code>can_pin_messages</code> in groups and "
    "supergroups or <code>can_edit_messages</code> in channels. This command is "
    "deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/unpinchatmessage &lt;chat_id&gt; [message_id]</code>\n"
    "Omit <code>message_id</code> to unpin the most recent pinned message. "
    "Rollback is manual: pin the message again in Telegram or with another "
    "operational tool."
)

UNPIN_ALL_CHAT_MESSAGES_USAGE = (
    "<b>unpinallchatmessages usage</b>\n"
    "Unpins all pinned messages from the specified group, supergroup or "
    "channel. The bot must be an administrator with "
    "<code>can_pin_messages</code> in groups and supergroups or "
    "<code>can_edit_messages</code> in channels. This command is "
    "deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/unpinallchatmessages &lt;chat_id&gt;</code>\n"
    "Rollback is manual: pin required messages again in Telegram or with "
    "<code>/pinchatmessage</code>."
)

PIN_CHAT_MESSAGE_USAGE = (
    "<b>pinchatmessage usage</b>\n"
    "Pins a message in the specified group, supergroup or channel. The bot "
    "must be an administrator with <code>can_pin_messages</code> in groups and "
    "supergroups or <code>can_edit_messages</code> in channels. This command is "
    "deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/pinchatmessage &lt;chat_id&gt; &lt;message_id&gt; "
    "[silent|loud]</code>\n"
    "Pass <code>silent</code> to pin without notification, or <code>loud</code> "
    "to force notification. Omit the flag to use Telegram's default. Rollback "
    "is manual: unpin the message in Telegram or with "
    "<code>/unpinchatmessage</code>."
)

DELETE_CHAT_PHOTO_USAGE = (
    "<b>deletechatphoto usage</b>\n"
    "Deletes the current photo from the specified group or supergroup. The bot "
    "must be an administrator with the right to change chat information in the "
    "target chat. This command is deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/deletechatphoto &lt;chat_id&gt;</code>\n"
    "Rollback is manual: set a new chat photo in Telegram chat administration."
)

SET_CHAT_PHOTO_USAGE = (
    "<b>setchatphoto usage</b>\n"
    "Sets a new photo for the specified group or supergroup. Telegram requires "
    "the bot to upload a fresh image file, so pass a local file path available "
    "to the running bot process. The bot must be an administrator with the "
    "right to change chat information in the target chat. This command is "
    "deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/setchatphoto &lt;chat_id&gt; &lt;photo_path&gt;</code>\n"
    "Rollback is manual: run this command again with the previous photo, or "
    "use Telegram chat administration."
)

SET_MY_PROFILE_PHOTO_USAGE = (
    "<b>setmyprofilephoto usage</b>\n"
    "Sets a new profile photo for this bot. Telegram requires the bot to "
    "upload a fresh image file, so pass a local file path available to the "
    "running bot process. This command is deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/setmyprofilephoto &lt;photo_path&gt;</code>\n"
    "Rollback is manual: run this command again with the previous photo, or "
    "remove the photo in BotFather/Telegram if needed."
)

REMOVE_MY_PROFILE_PHOTO_USAGE = (
    "<b>removemyprofilephoto usage</b>\n"
    "Removes the current profile photo from this bot. Telegram does not require "
    "chat administrator rights or specific update types for this Bot API "
    "method, but it changes the public bot profile. This command is "
    "deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/removemyprofilephoto confirm</code>\n"
    "Rollback: run <code>/setmyprofilephoto &lt;photo_path&gt;</code> with the "
    "previous image."
)

SET_CHAT_DESCRIPTION_USAGE = (
    "<b>setchatdescription usage</b>\n"
    "Sets the description for the specified group, supergroup or channel. The "
    "bot must be an administrator with the right to change chat information in "
    "the target chat. This command is deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/setchatdescription &lt;chat_id&gt; [description]</code>\n"
    f"The description may be empty to clear it and is limited to "
    f"{SET_CHAT_DESCRIPTION_LIMIT} characters."
)

SET_CHAT_TITLE_USAGE = (
    "<b>setchattitle usage</b>\n"
    "Sets the title for the specified group, supergroup or channel. The bot "
    "must be an administrator with the right to change chat information in "
    "the target chat. This command is deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/setchattitle &lt;chat_id&gt; &lt;title&gt;</code>\n"
    f"The title is limited to {SET_CHAT_TITLE_LIMIT} characters."
)

SET_CHAT_MENU_BUTTON_USAGE = (
    "<b>setchatmenubutton usage</b>\n"
    "Sets the menu button for a specific chat or the default menu button via "
    "<code>setChatMenuButton</code>. This command changes the bot's public UI, "
    "is deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/setchatmenubutton [chat_id=&lt;id&gt;] "
    "default|commands|web_app &lt;text&gt; &lt;url&gt;</code>\n"
    "Examples: <code>/setchatmenubutton commands</code>, "
    "<code>/setchatmenubutton chat_id=-100123 web_app Support https://example.com</code>"
)

SET_MY_COMMANDS_USAGE = (
    "<b>setmycommands usage</b>\n"
    "Sets the bot command list shown in Telegram clients via "
    "<code>setMyCommands</code>. Telegram accepts 0-100 commands; command names "
    "must be lowercase Latin letters, digits or underscores, 1-32 characters "
    "long, and descriptions must be 1-256 characters. This command changes the "
    "bot's public UI, is deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/setmycommands command:Description | command2:Description</code>\n"
    "Example: <code>/setmycommands start:Start the bot | help:Show help</code>"
)

SET_MY_NAME_USAGE = (
    "<b>setmyname usage</b>\n"
    "Sets the bot display name shown in Telegram clients via "
    "<code>setMyName</code>. Use configuration "
    "<code>TELEGRAM_BOT_NAME</code> and optional "
    "<code>TELEGRAM_BOT_NAME_LANGUAGE_CODE</code> for startup sync. Passing an "
    "empty name clears the selected name. This command changes the bot's "
    "public profile, is deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/setmyname &lt;name&gt; [language=&lt;code&gt;]</code> or "
    "<code>/setmyname --clear [language=&lt;code&gt;]</code>\n"
    f"The name is limited to {SET_MY_NAME_LIMIT} characters."
)

SET_MY_DESCRIPTION_USAGE = (
    "<b>setmydescription usage</b>\n"
    "Sets the bot description shown in Telegram clients via "
    "<code>setMyDescription</code>. Use configuration "
    "<code>TELEGRAM_BOT_DESCRIPTION</code> and optional "
    "<code>TELEGRAM_BOT_DESCRIPTION_LANGUAGE_CODE</code> for startup sync. "
    "Passing an empty description clears the selected description. This command "
    "changes the bot's public profile, is deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/setmydescription &lt;description&gt; [language=&lt;code&gt;]</code> "
    "or <code>/setmydescription --clear [language=&lt;code&gt;]</code>\n"
    f"The description is limited to {SET_MY_DESCRIPTION_LIMIT} characters."
)

SET_MY_SHORT_DESCRIPTION_USAGE = (
    "<b>setmyshortdescription usage</b>\n"
    "Sets the bot short description shown in Telegram clients via "
    "<code>setMyShortDescription</code>. Use configuration "
    "<code>TELEGRAM_BOT_SHORT_DESCRIPTION</code> and optional "
    "<code>TELEGRAM_BOT_SHORT_DESCRIPTION_LANGUAGE_CODE</code> for startup "
    "sync. Passing an empty short description clears the selected short "
    "description. This command changes the bot's public profile, is "
    "deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/setmyshortdescription &lt;short_description&gt; "
    "[language=&lt;code&gt;]</code> or "
    "<code>/setmyshortdescription --clear [language=&lt;code&gt;]</code>\n"
    f"The short description is limited to {SET_MY_SHORT_DESCRIPTION_LIMIT} "
    "characters."
)

GET_MY_NAME_USAGE = (
    "<b>getmyname usage</b>\n"
    "Fetches the bot display name shown in Telegram clients via "
    "<code>getMyName</code> for the default or selected language. Use this to "
    "verify the actual Telegram profile after startup sync, "
    "<code>/setmyname</code> or BotFather changes. The method is read-only, "
    "does not require chat administrator rights or update subscriptions, but "
    "this command is deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/getmyname [language=&lt;code&gt;]</code>\n"
    "Example: <code>/getmyname language=en</code>"
)

GET_MY_DESCRIPTION_USAGE = (
    "<b>getmydescription usage</b>\n"
    "Fetches the bot description shown in Telegram clients via "
    "<code>getMyDescription</code> for the default or selected language. Use "
    "this to verify the actual Telegram profile after startup sync, "
    "<code>/setmydescription</code> or BotFather changes. The method is "
    "read-only, does not require chat administrator rights or update "
    "subscriptions, but this command is deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/getmydescription [language=&lt;code&gt;]</code>\n"
    "Example: <code>/getmydescription language=en</code>"
)

GET_MY_SHORT_DESCRIPTION_USAGE = (
    "<b>getmyshortdescription usage</b>\n"
    "Fetches the bot short description shown in Telegram clients via "
    "<code>getMyShortDescription</code> for the default or selected language. "
    "Use this to verify the actual Telegram profile after startup sync, "
    "<code>/setmyshortdescription</code> or BotFather changes. The method is "
    "read-only, does not require chat administrator rights or update "
    "subscriptions, but this command is deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/getmyshortdescription [language=&lt;code&gt;]</code>\n"
    "Example: <code>/getmyshortdescription language=en</code>"
)

DELETE_MY_COMMANDS_USAGE = (
    "<b>deletemycommands usage</b>\n"
    "Deletes the bot command list shown in Telegram clients via "
    "<code>deleteMyCommands</code>. Use it before re-syncing commands for a "
    "specific scope or language. This command changes the bot's public UI, is "
    "deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/deletemycommands [scope=default|all_private_chats|"
    "all_group_chats|all_chat_administrators|chat|chat_administrators|"
    "chat_member] [chat_id=&lt;id&gt;] [user_id=&lt;id&gt;] [language=&lt;code&gt;]</code>\n"
    "Examples: <code>/deletemycommands</code>, "
    "<code>/deletemycommands scope=chat chat_id=-100123 language=en</code>"
)

GET_MY_COMMANDS_USAGE = (
    "<b>getmycommands usage</b>\n"
    "Fetches the bot command list shown in Telegram clients via "
    "<code>getMyCommands</code> for the default or selected scope/language. "
    "Use this to verify the actual Telegram command menu after "
    "<code>/setmycommands</code> or BotFather changes. This command is "
    "read-only, deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/getmycommands [scope=default|all_private_chats|"
    "all_group_chats|all_chat_administrators|chat|chat_administrators|"
    "chat_member] [chat_id=&lt;id&gt;] [user_id=&lt;id&gt;] "
    "[language=&lt;code&gt;]</code>\n"
    "Examples: <code>/getmycommands</code>, "
    "<code>/getmycommands scope=chat chat_id=-100123 language=en</code>"
)

SET_CHAT_STICKER_SET_USAGE = (
    "<b>setchatstickerset usage</b>\n"
    "Sets a sticker set for the specified supergroup. The bot must be an "
    "administrator with the right to change chat information in the target "
    "chat. This command is deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/setchatstickerset &lt;chat_id&gt; &lt;sticker_set_name&gt;</code>"
)

DELETE_CHAT_STICKER_SET_USAGE = (
    "<b>deletechatstickerset usage</b>\n"
    "Deletes the sticker set from the specified supergroup. The bot must be "
    "an administrator with the right to change chat information in the target "
    "chat. This command is deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/deletechatstickerset &lt;chat_id&gt;</code>\n"
    "Rollback is manual: run <code>/setchatstickerset</code> with the previous "
    "sticker set name."
)

PROMOTE_CHAT_MEMBER_USAGE = (
    "<b>promotechatmember usage</b>\n"
    "Promotes or demotes a user in the specified group, supergroup or channel. "
    "The bot must be an administrator with the "
    "<code>can_promote_members</code> right in the target chat. This command "
    "is deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/promotechatmember &lt;chat_id&gt; &lt;user_id&gt; "
    "&lt;moderator|manager|demote&gt;</code>\n"
    "Presets: <code>moderator</code> grants common moderation rights; "
    "<code>manager</code> also grants invite, pin and topic rights; "
    "<code>demote</code> clears common administrator rights."
)

APPROVE_CHAT_JOIN_REQUEST_USAGE = (
    "<b>approvechatjoinrequest usage</b>\n"
    "Approves a pending request to join the specified group, supergroup or "
    "channel. The bot must be an administrator with the "
    "<code>can_invite_users</code> right in the target chat. This command is "
    "deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/approvechatjoinrequest &lt;chat_id&gt; &lt;user_id&gt;</code>\n"
    "The <code>user_id</code> must identify a user with a currently pending "
    "join request for the target chat."
)

DECLINE_CHAT_JOIN_REQUEST_USAGE = (
    "<b>declinechatjoinrequest usage</b>\n"
    "Declines a pending request to join the specified group, supergroup or "
    "channel. The bot must be an administrator with the "
    "<code>can_invite_users</code> right in the target chat. This command is "
    "deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/declinechatjoinrequest &lt;chat_id&gt; &lt;user_id&gt;</code>\n"
    "The <code>user_id</code> must identify a user with a currently pending "
    "join request for the target chat."
)

EXPORT_CHAT_INVITE_LINK_USAGE = (
    "<b>exportchatinvitelink usage</b>\n"
    "Exports a new primary invite link for the specified group, supergroup or "
    "channel. The bot must be an administrator with the "
    "<code>can_invite_users</code> right in the target chat. Telegram revokes "
    "the previously generated primary invite link when this method succeeds. "
    "This command is deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/exportchatinvitelink &lt;chat_id&gt;</code>"
)

GET_CHAT_USAGE = (
    "<b>getchat usage</b>\n"
    "Fetches Telegram chat metadata for a private chat, group, supergroup or "
    "channel through <code>getChat</code>. The bot must be able to access the "
    "target chat. This command is deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/getchat &lt;chat_id&gt;</code>"
)

GET_CHAT_MEMBER_COUNT_USAGE = (
    "<b>getchatmembercount usage</b>\n"
    "Fetches the number of members in a group, supergroup or channel through "
    "<code>getChatMemberCount</code>. The bot must be able to access the "
    "target chat. This command is deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/getchatmembercount &lt;chat_id&gt;</code>"
)

GET_CHAT_MEMBER_USAGE = (
    "<b>getchatmember usage</b>\n"
    "Fetches a single chat member status through <code>getChatMember</code>. "
    "The bot must be able to access the target chat and may need "
    "administrator rights depending on chat type and privacy settings. This "
    "command is deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/getchatmember &lt;chat_id&gt; &lt;user_id&gt;</code>"
)

GET_CHAT_ADMINISTRATORS_USAGE = (
    "<b>getchatadministrators usage</b>\n"
    "Fetches the list of administrators in a group, supergroup or channel "
    "through <code>getChatAdministrators</code>. The bot must be able to "
    "access the target chat and may need administrator rights depending on "
    "chat type and privacy settings. This command is deny-by-default and only "
    "works from <code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/getchatadministrators &lt;chat_id&gt;</code>"
)

FORUM_TOPIC_ICON_STICKERS_USAGE = (
    "<b>forumtopiciconstickers usage</b>\n"
    "Fetches the custom emoji stickers Telegram allows as forum topic icons "
    "through <code>getForumTopicIconStickers</code>. This is an admin triage "
    "helper for choosing <code>icon_custom_emoji_id</code> values before "
    "creating or editing forum topics in supergroups. The method has no "
    "parameters and needs no special update subscription. This command is "
    "deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/forumtopiciconstickers</code>"
)

CREATE_FORUM_TOPIC_USAGE = (
    "<b>createforumtopic usage</b>\n"
    "Creates a forum topic in a supergroup through "
    "<code>createForumTopic</code>. The bot must be an administrator with the "
    "right to manage topics in the target supergroup. This command is "
    "deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/createforumtopic &lt;chat_id&gt; &lt;name&gt; "
    "[icon_color=&lt;rgb_int&gt;] [icon_custom_emoji_id=&lt;id&gt;]</code>\n"
    f"The name is required and limited to "
    f"{CREATE_FORUM_TOPIC_NAME_LIMIT} characters."
)

EDIT_FORUM_TOPIC_USAGE = (
    "<b>editforumtopic usage</b>\n"
    "Edits a forum topic in a supergroup through "
    "<code>editForumTopic</code>. The bot must be an administrator with the "
    "right to manage topics in the target supergroup. This command is "
    "deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/editforumtopic &lt;chat_id&gt; &lt;message_thread_id&gt; "
    "[name=&lt;text&gt;] [icon_custom_emoji_id=&lt;id&gt;]</code>\n"
    f"Provide at least one editable field. The name is limited to "
    f"{FORUM_TOPIC_NAME_LIMIT} characters."
)

EDIT_GENERAL_FORUM_TOPIC_USAGE = (
    "<b>editgeneralforumtopic usage</b>\n"
    "Edits the General forum topic in a supergroup through "
    "<code>editGeneralForumTopic</code>. The bot must be an administrator "
    "with the right to manage topics in the target supergroup. This command "
    "is deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/editgeneralforumtopic &lt;chat_id&gt; "
    "&lt;name&gt;</code>\n"
    f"The name is required and limited to "
    f"{GENERAL_FORUM_TOPIC_NAME_LIMIT} characters."
)

CLOSE_FORUM_TOPIC_USAGE = (
    "<b>closeforumtopic usage</b>\n"
    "Closes a forum topic in a supergroup through "
    "<code>closeForumTopic</code>. The bot must be an administrator with the "
    "right to manage topics in the target supergroup. This command is "
    "deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/closeforumtopic &lt;chat_id&gt; "
    "&lt;message_thread_id&gt;</code>"
)

CLOSE_GENERAL_FORUM_TOPIC_USAGE = (
    "<b>closegeneralforumtopic usage</b>\n"
    "Closes the General forum topic in a supergroup through "
    "<code>closeGeneralForumTopic</code>. The bot must be an administrator "
    "with the right to manage topics in the target supergroup. This command "
    "is deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/closegeneralforumtopic &lt;chat_id&gt;</code>"
)

REOPEN_FORUM_TOPIC_USAGE = (
    "<b>reopenforumtopic usage</b>\n"
    "Reopens a closed forum topic in a supergroup through "
    "<code>reopenForumTopic</code>. The bot must be an administrator with the "
    "right to manage topics in the target supergroup. This command is "
    "deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/reopenforumtopic &lt;chat_id&gt; "
    "&lt;message_thread_id&gt;</code>"
)

REOPEN_GENERAL_FORUM_TOPIC_USAGE = (
    "<b>reopengeneralforumtopic usage</b>\n"
    "Reopens the closed General forum topic in a supergroup through "
    "<code>reopenGeneralForumTopic</code>. The bot must be an administrator "
    "with the right to manage topics in the target supergroup. This command "
    "is deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/reopengeneralforumtopic &lt;chat_id&gt;</code>"
)

HIDE_GENERAL_FORUM_TOPIC_USAGE = (
    "<b>hidegeneralforumtopic usage</b>\n"
    "Hides the General forum topic in a supergroup through "
    "<code>hideGeneralForumTopic</code>. The bot must be an administrator "
    "with the right to manage topics in the target supergroup. This command "
    "is deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/hidegeneralforumtopic &lt;chat_id&gt;</code>"
)

UNHIDE_GENERAL_FORUM_TOPIC_USAGE = (
    "<b>unhidegeneralforumtopic usage</b>\n"
    "Unhides the General forum topic in a supergroup through "
    "<code>unhideGeneralForumTopic</code>. The bot must be an administrator "
    "with the right to manage topics in the target supergroup. This command "
    "is deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/unhidegeneralforumtopic &lt;chat_id&gt;</code>"
)

DELETE_FORUM_TOPIC_USAGE = (
    "<b>deleteforumtopic usage</b>\n"
    "Deletes a forum topic in a supergroup through "
    "<code>deleteForumTopic</code>. The bot must be an administrator with the "
    "right to manage topics in the target supergroup. This command is "
    "deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/deleteforumtopic &lt;chat_id&gt; "
    "&lt;message_thread_id&gt;</code>\n"
    "Rollback is manual: recreate the topic with <code>/createforumtopic</code> "
    "and move or copy relevant messages if needed."
)

UNPIN_ALL_FORUM_TOPIC_MESSAGES_USAGE = (
    "<b>unpinallforumtopicmessages usage</b>\n"
    "Unpins all pinned messages in a forum topic through "
    "<code>unpinAllForumTopicMessages</code>. The bot must be an "
    "administrator with the right to manage topics in the target supergroup. "
    "This command is deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/unpinallforumtopicmessages &lt;chat_id&gt; "
    "&lt;message_thread_id&gt;</code>\n"
    "Rollback is manual: pin required messages again in Telegram or with "
    "<code>/pinchatmessage</code>."
)

UNPIN_ALL_GENERAL_FORUM_TOPIC_MESSAGES_USAGE = (
    "<b>unpinallgeneralforumtopicmessages usage</b>\n"
    "Unpins all pinned messages in the General forum topic through "
    "<code>unpinAllGeneralForumTopicMessages</code>. The bot must be an "
    "administrator with the right to manage topics in the target supergroup. "
    "This command is deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/unpinallgeneralforumtopicmessages &lt;chat_id&gt;</code>\n"
    "Rollback is manual: pin required General topic messages again in "
    "Telegram or with <code>/pinchatmessage</code>."
)

GET_USER_PERSONAL_CHAT_MESSAGES_USAGE = (
    "<b>userpersonalchatmessages usage</b>\n"
    "Fetches recent messages from the personal chat between a user and this "
    "bot through <code>getUserPersonalChatMessages</code>. This command can "
    "expose private conversation metadata and is deny-by-default: it only "
    "works from <code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/userpersonalchatmessages &lt;user_id&gt; [limit]</code>\n"
    f"The optional <code>limit</code> must be between "
    f"{GET_USER_PERSONAL_CHAT_MESSAGES_MIN_LIMIT} and "
    f"{GET_USER_PERSONAL_CHAT_MESSAGES_MAX_LIMIT}; default "
    f"{GET_USER_PERSONAL_CHAT_MESSAGES_MAX_LIMIT}."
)

GET_USER_CHAT_BOOSTS_USAGE = (
    "<b>userchatboosts usage</b>\n"
    "Fetches boosts that a user added to a chat through "
    "<code>getUserChatBoosts</code>. The bot must be an administrator in the "
    "target chat, and this command is deny-by-default: it only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/userchatboosts &lt;chat_id&gt; &lt;user_id&gt;</code>"
)

LEAVE_CHAT_CONFIRM_KEYWORD = "confirm"

LEAVE_CHAT_USAGE = (
    "<b>leavechat usage</b>\n"
    "Makes the bot leave the specified group, supergroup or channel via "
    "Telegram <code>leaveChat</code>. The bot must currently be a member of "
    "the target chat. This command is deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/leavechat &lt;chat_id&gt; confirm</code>\n"
    "Rollback is manual: add the bot to the chat again and restore required "
    "administrator rights."
)

LEAVE_CHAT_WARNING = (
    "<b>leavechat confirmation required</b>\n"
    "This removes the bot from the target group, supergroup or channel. After "
    "a successful call the bot stops receiving updates from that chat until "
    "someone adds it again and restores any required administrator rights.\n"
    "Run <code>/leavechat &lt;chat_id&gt; confirm</code> to proceed."
)

CREATE_CHAT_INVITE_LINK_USAGE = (
    "<b>createchatinvitelink usage</b>\n"
    "Creates an additional invite link for the specified group, supergroup or "
    "channel. The bot must be an administrator with the "
    "<code>can_invite_users</code> right in the target chat. This command is "
    "deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/createchatinvitelink &lt;chat_id&gt; "
    "[name=&lt;text&gt;] [expire_date=&lt;unix_time&gt;] "
    "[member_limit=&lt;1-99999&gt;] [creates_join_request=true|false]</code>\n"
    "<code>creates_join_request=true</code> cannot be used with "
    "<code>member_limit</code>."
)

EDIT_CHAT_INVITE_LINK_USAGE = (
    "<b>editchatinvitelink usage</b>\n"
    "Edits an existing non-primary invite link for the specified group, "
    "supergroup or channel. The bot must be an administrator with the "
    "<code>can_invite_users</code> right in the target chat. This command is "
    "deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/editchatinvitelink &lt;chat_id&gt; &lt;invite_link&gt; "
    "[name=&lt;text&gt;] [expire_date=&lt;unix_time&gt;] "
    "[member_limit=&lt;1-99999&gt;] [creates_join_request=true|false]</code>\n"
    "<code>creates_join_request=true</code> cannot be used with "
    "<code>member_limit</code>."
)

REVOKE_CHAT_INVITE_LINK_USAGE = (
    "<b>revokechatinvitelink usage</b>\n"
    "Revokes an invite link created by the bot for the specified group, "
    "supergroup or channel. If the primary link is revoked, Telegram "
    "automatically generates a new one. The bot must be an administrator with "
    "the <code>can_invite_users</code> right in the target chat. This command "
    "is deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/revokechatinvitelink &lt;chat_id&gt; &lt;invite_link&gt;</code>"
)

CREATE_CHAT_SUBSCRIPTION_INVITE_LINK_USAGE = (
    "<b>createchatsubscriptioninvitelink usage</b>\n"
    "Creates a subscription invite link for the specified supergroup or "
    "channel. The bot must be an administrator with the "
    "<code>can_invite_users</code> right in the target chat. This command is "
    "deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/createchatsubscriptioninvitelink &lt;chat_id&gt; "
    "&lt;subscription_price&gt; [name=&lt;text&gt;] "
    "[subscription_period=2592000]</code>\n"
    "The optional <code>name</code> must be 0-32 characters. "
    "<code>subscription_price</code> must be 1-10000 Telegram Stars; Telegram "
    "currently requires a 2592000-second subscription period."
)

EDIT_CHAT_SUBSCRIPTION_INVITE_LINK_USAGE = (
    "<b>editchatsubscriptioninvitelink usage</b>\n"
    "Edits a subscription invite link created by the bot for the specified "
    "supergroup or channel. The bot must be an administrator with the "
    "<code>can_invite_users</code> right in the target chat. This command is "
    "deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/editchatsubscriptioninvitelink &lt;chat_id&gt; "
    "&lt;invite_link&gt; [name=&lt;text&gt;]</code>\n"
    "The optional <code>name</code> must be 0-32 characters."
)

SET_CHAT_ADMINISTRATOR_CUSTOM_TITLE_USAGE = (
    "<b>setchatadministratortitle usage</b>\n"
    "Sets a custom title for an administrator in the specified supergroup. "
    "The bot must be an administrator with the "
    "<code>can_promote_members</code> right in the target chat. This command "
    "is deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/setchatadministratortitle &lt;chat_id&gt; "
    "&lt;user_id&gt; &lt;custom_title&gt;</code>\n"
    "The <code>custom_title</code> may contain spaces."
)

SET_CHAT_MEMBER_TAG_USAGE = (
    "<b>setchatmembertag usage</b>\n"
    "Sets or clears a tag for a member in the specified chat. The bot must "
    "be an administrator with the required Telegram rights in the target "
    "chat. This command is deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/setchatmembertag &lt;chat_id&gt; &lt;user_id&gt; "
    "&lt;tag|clear&gt;</code>\n"
    "The <code>tag</code> may contain spaces. Pass <code>clear</code>, "
    "<code>none</code> or <code>-</code> to clear the member tag."
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
        "/managedbottoken - Fetch a managed bot token by user id (admin only)\n"
        "/managedbotaccess - Fetch managed bot access settings by user id (admin only)\n"
        "/setmanagedbotaccess - Update managed bot access settings by user id (admin only)\n"
        "/replacemanagedbottoken - Rotate a managed bot token by user id (admin only)\n"
        "/mediagroup - Send several media items into this chat as an album (admin only)\n"
        "/userprofilephotos - Fetch profile photos of a Telegram user (admin only)\n"
        "/userprofileaudios - Fetch profile audios of a Telegram user (admin only)\n"
        "/userpersonalchatmessages - Fetch user personal chat messages (admin only)\n"
        "/userchatboosts - Fetch boosts a user added to a chat (admin only)\n"
        "/getchat - Fetch chat metadata from Telegram (admin only)\n"
        "/getchatmember - Fetch a chat member status from Telegram (admin only)\n"
        "/getchatmembercount - Fetch chat member count from Telegram (admin only)\n"
        "/getchatadministrators - Fetch chat administrators from Telegram (admin only)\n"
        "/forumtopiciconstickers - Fetch available forum topic icon stickers (admin only)\n"
        "/createforumtopic - Create a forum topic in a supergroup (admin only)\n"
        "/editforumtopic - Edit a forum topic in a supergroup (admin only)\n"
        "/editgeneralforumtopic - Edit the General forum topic in a supergroup (admin only)\n"
        "/closeforumtopic - Close a forum topic in a supergroup (admin only)\n"
        "/closegeneralforumtopic - Close the General forum topic in a supergroup (admin only)\n"
        "/reopenforumtopic - Reopen a closed forum topic in a supergroup (admin only)\n"
        "/reopengeneralforumtopic - Reopen the General forum topic in a supergroup (admin only)\n"
        "/deleteforumtopic - Delete a forum topic in a supergroup (admin only)\n"
        "/unpinallforumtopicmessages - Unpin all pinned messages in a forum topic (admin only)\n"
        "/unpinallgeneralforumtopicmessages - Unpin all pinned messages in the General forum topic (admin only)\n"
        "/banchatmember - Ban a user from a chat (admin only)\n"
        "/banchatsenderchat - Ban a sender chat from a chat (admin only)\n"
        "/unbanchatmember - Unban a user from a chat (admin only)\n"
        "/unbanchatsenderchat - Unban a sender chat from a chat (admin only)\n"
        "/restrictchatmember - Restrict a user in a chat (admin only)\n"
        "/setchatpermissions - Set default chat permissions (admin only)\n"
        "/pinchatmessage - Pin a message in a chat (admin only)\n"
        "/unpinchatmessage - Unpin a message from a chat (admin only)\n"
        "/setchatphoto - Set a group or supergroup photo (admin only)\n"
        "/setmyprofilephoto - Set the bot profile photo (admin only)\n"
        "/removemyprofilephoto - Remove the bot profile photo (admin only)\n"
        "/setchatdescription - Set or clear a chat description (admin only)\n"
        "/setchattitle - Set a group, supergroup or channel title (admin only)\n"
        "/setchatmenubutton - Set the bot menu button for a chat or by default (admin only)\n"
        "/setmyname - Set or clear the bot display name (admin only)\n"
        "/getmyname - Fetch the bot display name (admin only)\n"
        "/setmydescription - Set or clear the bot description (admin only)\n"
        "/getmydescription - Fetch the bot description (admin only)\n"
        "/setmyshortdescription - Set or clear the bot short description (admin only)\n"
        "/getmyshortdescription - Fetch the bot short description (admin only)\n"
        "/setmycommands - Set the bot command list shown in Telegram clients (admin only)\n"
        "/getmycommands - Fetch and diagnose the bot command list (admin only)\n"
        "/deletemycommands - Delete bot commands by scope/language (admin only)\n"
        "/setchatstickerset - Set a supergroup sticker set (admin only)\n"
        "/deletechatstickerset - Delete a supergroup sticker set (admin only)\n"
        "/promotechatmember - Promote or demote a user in a chat (admin only)\n"
        "/approvechatjoinrequest - Approve a pending chat join request (admin only)\n"
        "/declinechatjoinrequest - Decline a pending chat join request (admin only)\n"
        "/exportchatinvitelink - Export a new primary chat invite link (admin only)\n"
        "/leavechat - Make the bot leave a chat (admin only)\n"
        "/editchatinvitelink - Edit a non-primary chat invite link (admin only)\n"
        "/revokechatinvitelink - Revoke a chat invite link (admin only)\n"
        "/editchatsubscriptioninvitelink - Edit a subscription invite link (admin only)\n"
        "/setchatadministratortitle - Set a chat administrator custom title (admin only)\n"
        "/setchatmembertag - Set or clear a chat member tag (admin only)\n"
        "/react - Set or remove a reaction on a message in this chat (admin only)\n"
        "/setemojistatus - Set or remove the emoji status of a user (admin only)\n"
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
            model_buttons = [
                [
                    InlineKeyboardButton(
                        text=m,
                        callback_data=f"{CALLBACK_MODEL_PREFIX}{m}",
                    )
                ]
                for m in models[:10]
                if len(f"{CALLBACK_MODEL_PREFIX}{m}".encode("utf-8"))
                <= TELEGRAM_CALLBACK_DATA_LIMIT
            ]
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=model_buttons
            )
            kwargs = {"reply_markup": keyboard} if model_buttons else {}
            await message.answer(
                f"Current model: {current}\nAvailable models:\n{models_list}",
                **kwargs,
            )
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
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Refresh",
                    callback_data=CALLBACK_SETTINGS_REFRESH,
                )
            ]
        ]
    )
    await message.answer(settings_text, parse_mode="HTML", reply_markup=keyboard)

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
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Confirm logOut",
                        callback_data=CALLBACK_LOGOUT_CONFIRM,
                    ),
                    InlineKeyboardButton(text="Cancel", callback_data=CALLBACK_CANCEL),
                ]
            ]
        )
        await message.answer(LOGOUT_WARNING, parse_mode="HTML", reply_markup=keyboard)
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
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Confirm close",
                        callback_data=CALLBACK_CLOSE_CONFIRM,
                    ),
                    InlineKeyboardButton(text="Cancel", callback_data=CALLBACK_CANCEL),
                ]
            ]
        )
        await message.answer(CLOSE_WARNING, parse_mode="HTML", reply_markup=keyboard)
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

@router.message(Command("businessconnection"))
async def cmd_business_connection(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    business_connection_id = _parse_business_connection_args(message.text or "")
    if business_connection_id is None:
        await message.answer(BUSINESS_CONNECTION_USAGE, parse_mode="HTML")
        return

    try:
        connection = await perform_get_business_connection(
            message.bot,
            business_connection_id=business_connection_id,
        )
    except GetBusinessConnectionError as exc:
        await message.answer(f"Could not fetch the business connection: {exc}")
        return

    await message.answer(format_business_connection(connection), parse_mode="HTML")


@router.message(Command("managedbottoken"))
async def cmd_managed_bot_token(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    user_id = _parse_managed_bot_token_args(message.text or "")
    if user_id is None:
        await message.answer(MANAGED_BOT_TOKEN_USAGE, parse_mode="HTML")
        return

    try:
        token = await perform_get_managed_bot_token(
            message.bot,
            user_id=user_id,
        )
    except GetManagedBotTokenError as exc:
        await message.answer(f"Could not fetch the managed bot token: {exc}")
        return

    await message.answer(
        format_managed_bot_token(user_id=user_id, token=token),
        parse_mode="HTML",
    )


@router.message(Command("managedbotaccess"))
async def cmd_managed_bot_access_settings(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    user_id = _parse_managed_bot_access_settings_args(message.text or "")
    if user_id is None:
        await message.answer(
            MANAGED_BOT_ACCESS_SETTINGS_USAGE,
            parse_mode="HTML",
        )
        return

    try:
        settings = await perform_get_managed_bot_access_settings(
            message.bot,
            user_id=user_id,
        )
    except GetManagedBotAccessSettingsError as exc:
        await message.answer(
            f"Could not fetch the managed bot access settings: {exc}"
        )
        return

    await message.answer(
        format_managed_bot_access_settings(user_id=user_id, settings=settings),
        parse_mode="HTML",
    )


@router.message(Command("setmanagedbotaccess"))
async def cmd_set_managed_bot_access_settings(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_set_managed_bot_access_settings_args(message.text or "")
    if parsed is None:
        await message.answer(
            SET_MANAGED_BOT_ACCESS_SETTINGS_USAGE,
            parse_mode="HTML",
        )
        return

    user_id, is_access_restricted, added_user_ids, confirmed = parsed
    if not confirmed:
        await message.answer(
            SET_MANAGED_BOT_ACCESS_SETTINGS_WARNING,
            parse_mode="HTML",
        )
        return

    try:
        await perform_set_managed_bot_access_settings(
            message.bot,
            user_id=user_id,
            is_access_restricted=is_access_restricted,
            added_user_ids=added_user_ids,
        )
    except SetManagedBotAccessSettingsError as exc:
        await message.answer(
            f"Could not set the managed bot access settings: {exc}"
        )
        return

    await message.answer(
        format_set_managed_bot_access_settings_result(
            user_id=user_id,
            is_access_restricted=is_access_restricted,
            added_user_ids=added_user_ids,
        ),
        parse_mode="HTML",
    )


@router.message(Command("replacemanagedbottoken"))
async def cmd_replace_managed_bot_token(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_replace_managed_bot_token_args(message.text or "")
    if parsed is None:
        await message.answer(REPLACE_MANAGED_BOT_TOKEN_USAGE, parse_mode="HTML")
        return

    user_id, confirmed = parsed
    if not confirmed:
        await message.answer(
            REPLACE_MANAGED_BOT_TOKEN_WARNING,
            parse_mode="HTML",
        )
        return

    try:
        token = await perform_replace_managed_bot_token(
            message.bot,
            user_id=user_id,
        )
    except ReplaceManagedBotTokenError as exc:
        await message.answer(f"Could not replace the managed bot token: {exc}")
        return

    await message.answer(
        format_replaced_managed_bot_token(user_id=user_id, token=token),
        parse_mode="HTML",
    )


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


@router.message(Command("userprofileaudios"))
async def cmd_user_profile_audios(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_user_profile_audios_args(message.text or "")
    if parsed is None:
        await message.answer(USER_PROFILE_AUDIOS_USAGE, parse_mode="HTML")
        return

    user_id, offset, limit = parsed

    if limit is not None and not (
        GET_USER_PROFILE_AUDIOS_MIN_LIMIT <= limit <= GET_USER_PROFILE_AUDIOS_MAX_LIMIT
    ):
        await message.answer(
            f"Limit must be between {GET_USER_PROFILE_AUDIOS_MIN_LIMIT} and "
            f"{GET_USER_PROFILE_AUDIOS_MAX_LIMIT}."
        )
        return

    try:
        result = await fetch_user_profile_audios(
            message.bot,
            user_id=user_id,
            offset=offset,
            limit=limit,
        )
    except TelegramAPIError as exc:
        await message.answer(f"Could not fetch user profile audios: {exc}")
        return

    await message.answer(
        format_user_profile_audios(result, user_id), parse_mode="HTML"
    )


@router.message(Command("banchatmember"))
async def cmd_ban_chat_member(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_ban_chat_member_args(message.text or "")
    if parsed is None:
        await message.answer(BAN_CHAT_MEMBER_USAGE, parse_mode="HTML")
        return

    chat_id, user_id, until_date, revoke_messages = parsed

    try:
        await perform_ban_chat_member(
            message.bot,
            chat_id=chat_id,
            user_id=user_id,
            until_date=until_date,
            revoke_messages=revoke_messages,
        )
    except TelegramAPIError as exc:
        await message.answer(f"Could not ban the user: {exc}")
        return

    await message.answer(
        format_ban_result(chat_id, user_id, until_date, revoke_messages),
        parse_mode="HTML",
    )


@router.message(Command("banchatsenderchat"))
async def cmd_ban_chat_sender_chat(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_ban_chat_sender_chat_args(message.text or "")
    if parsed is None:
        await message.answer(BAN_CHAT_SENDER_CHAT_USAGE, parse_mode="HTML")
        return

    chat_id, sender_chat_id = parsed

    try:
        await perform_ban_chat_sender_chat(
            message.bot,
            chat_id=chat_id,
            sender_chat_id=sender_chat_id,
        )
    except TelegramAPIError as exc:
        await message.answer(f"Could not ban the sender chat: {exc}")
        return

    await message.answer(
        format_ban_sender_chat_result(chat_id, sender_chat_id),
        parse_mode="HTML",
    )


@router.message(Command("unbanchatmember"))
async def cmd_unban_chat_member(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_unban_chat_member_args(message.text or "")
    if parsed is None:
        await message.answer(UNBAN_CHAT_MEMBER_USAGE, parse_mode="HTML")
        return

    chat_id, user_id, only_if_banned = parsed

    try:
        await perform_unban_chat_member(
            message.bot,
            chat_id=chat_id,
            user_id=user_id,
            only_if_banned=only_if_banned,
        )
    except TelegramAPIError as exc:
        await message.answer(f"Could not unban the user: {exc}")
        return

    await message.answer(
        format_unban_result(chat_id, user_id, only_if_banned),
        parse_mode="HTML",
    )


@router.message(Command("unbanchatsenderchat"))
async def cmd_unban_chat_sender_chat(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_unban_chat_sender_chat_args(message.text or "")
    if parsed is None:
        await message.answer(UNBAN_CHAT_SENDER_CHAT_USAGE, parse_mode="HTML")
        return

    chat_id, sender_chat_id = parsed

    try:
        await perform_unban_chat_sender_chat(
            message.bot,
            chat_id=chat_id,
            sender_chat_id=sender_chat_id,
        )
    except TelegramAPIError as exc:
        await message.answer(f"Could not unban the sender chat: {exc}")
        return

    await message.answer(
        format_unban_sender_chat_result(chat_id, sender_chat_id),
        parse_mode="HTML",
    )


@router.message(Command("restrictchatmember"))
async def cmd_restrict_chat_member(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_restrict_chat_member_args(message.text or "")
    if parsed is None:
        await message.answer(RESTRICT_CHAT_MEMBER_USAGE, parse_mode="HTML")
        return

    (
        chat_id,
        user_id,
        preset,
        permissions,
        until_date,
        use_independent_chat_permissions,
    ) = parsed

    try:
        await perform_restrict_chat_member(
            message.bot,
            chat_id=chat_id,
            user_id=user_id,
            permissions=permissions,
            until_date=until_date,
            use_independent_chat_permissions=use_independent_chat_permissions,
        )
    except TelegramAPIError as exc:
        await message.answer(f"Could not restrict the user: {exc}")
        return

    await message.answer(
        format_restrict_result(
            chat_id=chat_id,
            user_id=user_id,
            preset=preset,
            permissions=permissions,
            until_date=until_date,
            use_independent_chat_permissions=use_independent_chat_permissions,
        ),
        parse_mode="HTML",
    )


@router.message(Command("setchatpermissions"))
async def cmd_set_chat_permissions(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_set_chat_permissions_args(message.text or "")
    if parsed is None:
        await message.answer(SET_CHAT_PERMISSIONS_USAGE, parse_mode="HTML")
        return

    chat_id, preset, permissions, use_independent_chat_permissions = parsed

    try:
        await perform_set_chat_permissions(
            message.bot,
            chat_id=chat_id,
            permissions=permissions,
            use_independent_chat_permissions=use_independent_chat_permissions,
        )
    except TelegramAPIError as exc:
        await message.answer(f"Could not set chat permissions: {exc}")
        return

    await message.answer(
        format_set_chat_permissions_result(
            chat_id=chat_id,
            preset=preset,
            permissions=permissions,
            use_independent_chat_permissions=use_independent_chat_permissions,
        ),
        parse_mode="HTML",
    )


@router.message(Command("unpinchatmessage"))
async def cmd_unpin_chat_message(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_unpin_chat_message_args(message.text or "")
    if parsed is None:
        await message.answer(UNPIN_CHAT_MESSAGE_USAGE, parse_mode="HTML")
        return

    chat_id, message_id = parsed

    try:
        await perform_unpin_chat_message(
            message.bot,
            chat_id=chat_id,
            message_id=message_id,
        )
    except TelegramAPIError as exc:
        await message.answer(f"Could not unpin the chat message: {exc}")
        return

    await message.answer(
        format_unpin_chat_message_result(chat_id=chat_id, message_id=message_id),
        parse_mode="HTML",
    )


@router.message(Command("unpinallchatmessages"))
async def cmd_unpin_all_chat_messages(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    chat_id = _parse_unpin_all_chat_messages_args(message.text or "")
    if chat_id is None:
        await message.answer(UNPIN_ALL_CHAT_MESSAGES_USAGE, parse_mode="HTML")
        return

    try:
        await perform_unpin_all_chat_messages(message.bot, chat_id=chat_id)
    except TelegramAPIError as exc:
        await message.answer(f"Could not unpin all chat messages: {exc}")
        return

    await message.answer(
        format_unpin_all_chat_messages_result(chat_id=chat_id),
        parse_mode="HTML",
    )


@router.message(Command("pinchatmessage"))
async def cmd_pin_chat_message(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_pin_chat_message_args(message.text or "")
    if parsed is None:
        await message.answer(PIN_CHAT_MESSAGE_USAGE, parse_mode="HTML")
        return

    chat_id, message_id, disable_notification = parsed

    try:
        await perform_pin_chat_message(
            message.bot,
            chat_id=chat_id,
            message_id=message_id,
            disable_notification=disable_notification,
        )
    except TelegramAPIError as exc:
        await message.answer(f"Could not pin the chat message: {exc}")
        return

    await message.answer(
        format_pin_chat_message_result(
            chat_id=chat_id,
            message_id=message_id,
            disable_notification=disable_notification,
        ),
        parse_mode="HTML",
    )


@router.message(Command("deletechatphoto"))
async def cmd_delete_chat_photo(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    chat_id = _parse_delete_chat_photo_args(message.text or "")
    if chat_id is None:
        await message.answer(DELETE_CHAT_PHOTO_USAGE, parse_mode="HTML")
        return

    try:
        await perform_delete_chat_photo(message.bot, chat_id=chat_id)
    except TelegramAPIError as exc:
        await message.answer(f"Could not delete the chat photo: {exc}")
        return

    await message.answer(
        format_delete_chat_photo_result(chat_id=chat_id),
        parse_mode="HTML",
    )


@router.message(Command("setchatphoto"))
async def cmd_set_chat_photo(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_set_chat_photo_args(message.text or "")
    if parsed is None:
        await message.answer(SET_CHAT_PHOTO_USAGE, parse_mode="HTML")
        return

    chat_id, photo_path = parsed

    try:
        await perform_set_chat_photo(
            message.bot,
            chat_id=chat_id,
            photo_path=photo_path,
        )
    except TelegramAPIError as exc:
        await message.answer(f"Could not set the chat photo: {exc}")
        return

    await message.answer(
        format_set_chat_photo_result(chat_id=chat_id, photo_path=photo_path),
        parse_mode="HTML",
    )


@router.message(Command("setmyprofilephoto"))
async def cmd_set_my_profile_photo(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    photo_path = _parse_set_my_profile_photo_args(message.text or "")
    if photo_path is None:
        await message.answer(SET_MY_PROFILE_PHOTO_USAGE, parse_mode="HTML")
        return

    try:
        await perform_set_my_profile_photo(
            message.bot,
            photo_path=photo_path,
        )
    except SetMyProfilePhotoError as exc:
        await message.answer(f"Could not set the bot profile photo: {exc}")
        return

    await message.answer(
        format_set_my_profile_photo_result(photo_path=photo_path),
        parse_mode="HTML",
    )


@router.message(Command("removemyprofilephoto"))
async def cmd_remove_my_profile_photo(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    if not _parse_remove_my_profile_photo_args(message.text or ""):
        await message.answer(REMOVE_MY_PROFILE_PHOTO_USAGE, parse_mode="HTML")
        return

    try:
        await perform_remove_my_profile_photo(message.bot)
    except RemoveMyProfilePhotoError as exc:
        await message.answer(f"Could not remove the bot profile photo: {exc}")
        return

    await message.answer(
        format_remove_my_profile_photo_result(),
        parse_mode="HTML",
    )


@router.message(Command("setchatdescription"))
async def cmd_set_chat_description(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_set_chat_description_args(message.text or "")
    if parsed is None:
        await message.answer(SET_CHAT_DESCRIPTION_USAGE, parse_mode="HTML")
        return

    chat_id, description = parsed

    try:
        await perform_set_chat_description(
            message.bot,
            chat_id=chat_id,
            description=description,
        )
    except TelegramAPIError as exc:
        await message.answer(f"Could not set the chat description: {exc}")
        return

    await message.answer(
        format_set_chat_description_result(
            chat_id=chat_id,
            description=description,
        ),
        parse_mode="HTML",
    )


@router.message(Command("setchattitle"))
async def cmd_set_chat_title(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_set_chat_title_args(message.text or "")
    if parsed is None:
        await message.answer(SET_CHAT_TITLE_USAGE, parse_mode="HTML")
        return

    chat_id, title = parsed

    try:
        await perform_set_chat_title(
            message.bot,
            chat_id=chat_id,
            title=title,
        )
    except TelegramAPIError as exc:
        await message.answer(f"Could not set the chat title: {exc}")
        return

    await message.answer(
        format_set_chat_title_result(chat_id=chat_id, title=title),
        parse_mode="HTML",
    )


@router.message(Command("setmycommands"))
async def cmd_set_my_commands(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_set_my_commands_args(message.text or "")
    if parsed is None:
        await message.answer(SET_MY_COMMANDS_USAGE, parse_mode="HTML")
        return

    try:
        await perform_set_my_commands(message.bot, commands=parsed)
    except TelegramAPIError as exc:
        await message.answer(f"Could not set bot commands: {exc}")
        return

    await message.answer(
        format_set_my_commands_result(parsed),
        parse_mode="HTML",
    )


@router.message(Command("setchatmenubutton"))
async def cmd_set_chat_menu_button(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_set_chat_menu_button_args(message.text or "")
    if parsed is None:
        await message.answer(SET_CHAT_MENU_BUTTON_USAGE, parse_mode="HTML")
        return

    chat_id, menu_button = parsed

    try:
        await perform_set_chat_menu_button(
            message.bot,
            chat_id=chat_id,
            menu_button=menu_button,
        )
    except TelegramAPIError as exc:
        await message.answer(f"Could not set the chat menu button: {exc}")
        return

    await message.answer(
        format_set_chat_menu_button_result(chat_id=chat_id, menu_button=menu_button),
        parse_mode="HTML",
    )


@router.message(Command("setmyname"))
async def cmd_set_my_name(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_set_my_name_args(message.text or "")
    if parsed is None:
        await message.answer(SET_MY_NAME_USAGE, parse_mode="HTML")
        return

    name, language_code = parsed
    try:
        await perform_set_my_name(
            message.bot,
            name=name,
            language_code=language_code,
        )
    except SetMyNameValidationError as exc:
        await message.answer(f"Could not set bot name: {exc}")
        return
    except TelegramAPIError as exc:
        await message.answer(f"Could not set bot name: {exc}")
        return

    await message.answer(
        format_set_my_name_result(name=name, language_code=language_code),
        parse_mode="HTML",
    )


@router.message(Command("setmydescription"))
async def cmd_set_my_description(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_set_my_description_args(message.text or "")
    if parsed is None:
        await message.answer(SET_MY_DESCRIPTION_USAGE, parse_mode="HTML")
        return

    description, language_code = parsed
    try:
        await perform_set_my_description(
            message.bot,
            description=description,
            language_code=language_code,
        )
    except SetMyDescriptionValidationError as exc:
        await message.answer(f"Could not set bot description: {exc}")
        return
    except TelegramAPIError as exc:
        await message.answer(f"Could not set bot description: {exc}")
        return

    await message.answer(
        format_set_my_description_result(
            description=description,
            language_code=language_code,
        ),
        parse_mode="HTML",
    )


@router.message(Command("setmyshortdescription"))
async def cmd_set_my_short_description(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_set_my_short_description_args(message.text or "")
    if parsed is None:
        await message.answer(SET_MY_SHORT_DESCRIPTION_USAGE, parse_mode="HTML")
        return

    short_description, language_code = parsed
    try:
        await perform_set_my_short_description(
            message.bot,
            short_description=short_description,
            language_code=language_code,
        )
    except SetMyShortDescriptionValidationError as exc:
        await message.answer(f"Could not set bot short description: {exc}")
        return
    except TelegramAPIError as exc:
        await message.answer(f"Could not set bot short description: {exc}")
        return

    await message.answer(
        format_set_my_short_description_result(
            short_description=short_description,
            language_code=language_code,
        ),
        parse_mode="HTML",
    )


@router.message(Command("getmyname"))
async def cmd_get_my_name(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_get_my_name_args(message.text or "")
    if parsed is False:
        await message.answer(GET_MY_NAME_USAGE, parse_mode="HTML")
        return

    try:
        bot_name = await perform_get_my_name(
            message.bot,
            language_code=parsed,
        )
    except TelegramAPIError as exc:
        await message.answer(f"Could not get bot name: {exc}")
        return

    await message.answer(
        format_get_my_name_result(bot_name, language_code=parsed),
        parse_mode="HTML",
    )


@router.message(Command("getmydescription"))
async def cmd_get_my_description(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_get_my_description_args(message.text or "")
    if parsed is False:
        await message.answer(GET_MY_DESCRIPTION_USAGE, parse_mode="HTML")
        return

    try:
        bot_description = await perform_get_my_description(
            message.bot,
            language_code=parsed,
        )
    except TelegramAPIError as exc:
        await message.answer(f"Could not get bot description: {exc}")
        return

    await message.answer(
        format_get_my_description_result(bot_description, language_code=parsed),
        parse_mode="HTML",
    )


@router.message(Command("getmyshortdescription"))
async def cmd_get_my_short_description(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_get_my_short_description_args(message.text or "")
    if parsed is False:
        await message.answer(GET_MY_SHORT_DESCRIPTION_USAGE, parse_mode="HTML")
        return

    try:
        bot_short_description = await perform_get_my_short_description(
            message.bot,
            language_code=parsed,
        )
    except TelegramAPIError as exc:
        await message.answer(f"Could not get bot short description: {exc}")
        return

    await message.answer(
        format_get_my_short_description_result(
            bot_short_description,
            language_code=parsed,
        ),
        parse_mode="HTML",
    )


@router.message(Command("deletemycommands"))
async def cmd_delete_my_commands(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_delete_my_commands_args(message.text or "")
    if parsed is None:
        await message.answer(DELETE_MY_COMMANDS_USAGE, parse_mode="HTML")
        return

    scope, language_code = parsed
    try:
        await perform_delete_my_commands(
            message.bot,
            scope=scope,
            language_code=language_code,
        )
    except TelegramAPIError as exc:
        await message.answer(f"Could not delete bot commands: {exc}")
        return

    await message.answer(
        format_delete_my_commands_result(scope=scope, language_code=language_code),
        parse_mode="HTML",
    )


@router.message(Command("getmycommands"))
async def cmd_get_my_commands(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_get_my_commands_args(message.text or "")
    if parsed is None:
        await message.answer(GET_MY_COMMANDS_USAGE, parse_mode="HTML")
        return

    scope, language_code = parsed
    try:
        actual_commands = await perform_get_my_commands(
            message.bot,
            scope=scope,
            language_code=language_code,
        )
    except TelegramAPIError as exc:
        await message.answer(f"Could not get bot commands: {exc}")
        return

    await message.answer(
        format_get_my_commands_result(
            actual_commands,
            scope=scope,
            language_code=language_code,
        ),
        parse_mode="HTML",
    )


@router.message(Command("setchatstickerset"))
async def cmd_set_chat_sticker_set(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_set_chat_sticker_set_args(message.text or "")
    if parsed is None:
        await message.answer(SET_CHAT_STICKER_SET_USAGE, parse_mode="HTML")
        return

    chat_id, sticker_set_name = parsed

    try:
        await perform_set_chat_sticker_set(
            message.bot,
            chat_id=chat_id,
            sticker_set_name=sticker_set_name,
        )
    except TelegramAPIError as exc:
        await message.answer(f"Could not set the chat sticker set: {exc}")
        return

    await message.answer(
        format_set_chat_sticker_set_result(
            chat_id=chat_id,
            sticker_set_name=sticker_set_name,
        ),
        parse_mode="HTML",
    )


@router.message(Command("deletechatstickerset"))
async def cmd_delete_chat_sticker_set(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    chat_id = _parse_delete_chat_sticker_set_args(message.text or "")
    if chat_id is None:
        await message.answer(DELETE_CHAT_STICKER_SET_USAGE, parse_mode="HTML")
        return

    try:
        await perform_delete_chat_sticker_set(message.bot, chat_id=chat_id)
    except TelegramAPIError as exc:
        await message.answer(f"Could not delete the chat sticker set: {exc}")
        return

    await message.answer(
        format_delete_chat_sticker_set_result(chat_id=chat_id),
        parse_mode="HTML",
    )


@router.message(Command("promotechatmember"))
async def cmd_promote_chat_member(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_promote_chat_member_args(message.text or "")
    if parsed is None:
        await message.answer(PROMOTE_CHAT_MEMBER_USAGE, parse_mode="HTML")
        return

    chat_id, user_id, preset, rights = parsed

    try:
        await perform_promote_chat_member(
            message.bot,
            chat_id=chat_id,
            user_id=user_id,
            rights=rights,
        )
    except TelegramAPIError as exc:
        await message.answer(f"Could not promote the user: {exc}")
        return

    await message.answer(
        format_promote_result(
            chat_id=chat_id,
            user_id=user_id,
            preset=preset,
            rights=rights,
        ),
        parse_mode="HTML",
    )


@router.message(Command("exportchatinvitelink"))
async def cmd_export_chat_invite_link(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    chat_id = _parse_export_chat_invite_link_args(message.text or "")
    if chat_id is None:
        await message.answer(EXPORT_CHAT_INVITE_LINK_USAGE, parse_mode="HTML")
        return

    try:
        invite_link = await perform_export_chat_invite_link(
            message.bot,
            chat_id=chat_id,
        )
    except TelegramAPIError as exc:
        await message.answer(f"Could not export the chat invite link: {exc}")
        return

    await message.answer(
        format_export_chat_invite_link_result(
            chat_id=chat_id,
            invite_link=invite_link,
        ),
        parse_mode="HTML",
    )


@router.message(Command("getchat"))
async def cmd_get_chat(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    chat_id = _parse_get_chat_args(message.text or "")
    if chat_id is None:
        await message.answer(GET_CHAT_USAGE, parse_mode="HTML")
        return

    try:
        chat = await perform_get_chat(
            message.bot,
            chat_id=chat_id,
        )
    except TelegramAPIError as exc:
        await message.answer(f"Could not get chat information: {exc}")
        return

    await message.answer(
        format_get_chat_result(chat),
        parse_mode="HTML",
    )


@router.message(Command("getchatmembercount"))
async def cmd_get_chat_member_count(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    chat_id = _parse_get_chat_member_count_args(message.text or "")
    if chat_id is None:
        await message.answer(GET_CHAT_MEMBER_COUNT_USAGE, parse_mode="HTML")
        return

    try:
        member_count = await perform_get_chat_member_count(
            message.bot,
            chat_id=chat_id,
        )
    except TelegramAPIError as exc:
        await message.answer(f"Could not get chat member count: {exc}")
        return

    await message.answer(
        format_get_chat_member_count_result(chat_id, member_count),
        parse_mode="HTML",
    )


@router.message(Command("getchatmember"))
async def cmd_get_chat_member(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_get_chat_member_args(message.text or "")
    if parsed is None:
        await message.answer(GET_CHAT_MEMBER_USAGE, parse_mode="HTML")
        return

    chat_id, user_id = parsed
    try:
        member = await perform_get_chat_member(
            message.bot,
            chat_id=chat_id,
            user_id=user_id,
        )
    except TelegramAPIError as exc:
        await message.answer(f"Could not get chat member: {exc}")
        return

    await message.answer(
        format_get_chat_member_result(chat_id, user_id, member),
        parse_mode="HTML",
    )


@router.message(Command("getchatadministrators"))
async def cmd_get_chat_administrators(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    chat_id = _parse_get_chat_administrators_args(message.text or "")
    if chat_id is None:
        await message.answer(GET_CHAT_ADMINISTRATORS_USAGE, parse_mode="HTML")
        return

    try:
        administrators = await perform_get_chat_administrators(
            message.bot,
            chat_id=chat_id,
        )
    except TelegramAPIError as exc:
        await message.answer(f"Could not get chat administrators: {exc}")
        return

    await message.answer(
        format_get_chat_administrators_result(chat_id, administrators),
        parse_mode="HTML",
    )


@router.message(Command("forumtopiciconstickers"))
async def cmd_forum_topic_icon_stickers(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    if (message.text or "").split()[1:]:
        await message.answer(FORUM_TOPIC_ICON_STICKERS_USAGE, parse_mode="HTML")
        return

    try:
        stickers = await perform_get_forum_topic_icon_stickers(message.bot)
    except GetForumTopicIconStickersError as exc:
        await message.answer(f"Could not get forum topic icon stickers: {exc}")
        return

    await message.answer(
        format_forum_topic_icon_stickers(stickers),
        parse_mode="HTML",
    )


@router.message(Command("editforumtopic"))
async def cmd_edit_forum_topic(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_edit_forum_topic_args(message.text or "")
    if parsed is None:
        await message.answer(EDIT_FORUM_TOPIC_USAGE, parse_mode="HTML")
        return

    chat_id, message_thread_id, name, icon_custom_emoji_id = parsed

    try:
        await perform_edit_forum_topic(
            message.bot,
            chat_id=chat_id,
            message_thread_id=message_thread_id,
            name=name,
            icon_custom_emoji_id=icon_custom_emoji_id,
        )
    except EditForumTopicError as exc:
        await message.answer(f"Could not edit forum topic: {exc}")
        return

    await message.answer(
        format_edit_forum_topic_result(
            chat_id=chat_id,
            message_thread_id=message_thread_id,
            name=name,
            icon_custom_emoji_id=icon_custom_emoji_id,
        ),
        parse_mode="HTML",
    )


@router.message(Command("editgeneralforumtopic"))
async def cmd_edit_general_forum_topic(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_edit_general_forum_topic_args(message.text or "")
    if parsed is None:
        await message.answer(EDIT_GENERAL_FORUM_TOPIC_USAGE, parse_mode="HTML")
        return

    chat_id, name = parsed

    try:
        await perform_edit_general_forum_topic(
            message.bot,
            chat_id=chat_id,
            name=name,
        )
    except EditGeneralForumTopicError as exc:
        await message.answer(f"Could not edit General forum topic: {exc}")
        return

    await message.answer(
        format_edit_general_forum_topic_result(
            chat_id=chat_id,
            name=name,
        ),
        parse_mode="HTML",
    )


@router.message(Command("createforumtopic"))
async def cmd_create_forum_topic(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_create_forum_topic_args(message.text or "")
    if parsed is None:
        await message.answer(CREATE_FORUM_TOPIC_USAGE, parse_mode="HTML")
        return

    chat_id, name, icon_color, icon_custom_emoji_id = parsed

    try:
        topic = await perform_create_forum_topic(
            message.bot,
            chat_id=chat_id,
            name=name,
            icon_color=icon_color,
            icon_custom_emoji_id=icon_custom_emoji_id,
        )
    except CreateForumTopicError as exc:
        await message.answer(f"Could not create forum topic: {exc}")
        return

    await message.answer(
        format_create_forum_topic_result(
            chat_id=chat_id,
            name=name,
            topic=topic,
            icon_color=icon_color,
            icon_custom_emoji_id=icon_custom_emoji_id,
        ),
        parse_mode="HTML",
    )


@router.message(Command("closeforumtopic"))
async def cmd_close_forum_topic(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_close_forum_topic_args(message.text or "")
    if parsed is None:
        await message.answer(CLOSE_FORUM_TOPIC_USAGE, parse_mode="HTML")
        return

    chat_id, message_thread_id = parsed

    try:
        await perform_close_forum_topic(
            message.bot,
            chat_id=chat_id,
            message_thread_id=message_thread_id,
        )
    except CloseForumTopicError as exc:
        await message.answer(f"Could not close forum topic: {exc}")
        return

    await message.answer(
        format_close_forum_topic_result(
            chat_id=chat_id,
            message_thread_id=message_thread_id,
        ),
        parse_mode="HTML",
    )


@router.message(Command("closegeneralforumtopic"))
async def cmd_close_general_forum_topic(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    chat_id = _parse_close_general_forum_topic_args(message.text or "")
    if chat_id is None:
        await message.answer(CLOSE_GENERAL_FORUM_TOPIC_USAGE, parse_mode="HTML")
        return

    try:
        await perform_close_general_forum_topic(
            message.bot,
            chat_id=chat_id,
        )
    except CloseGeneralForumTopicError as exc:
        await message.answer(f"Could not close General forum topic: {exc}")
        return

    await message.answer(
        format_close_general_forum_topic_result(chat_id=chat_id),
        parse_mode="HTML",
    )


@router.message(Command("reopenforumtopic"))
async def cmd_reopen_forum_topic(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_reopen_forum_topic_args(message.text or "")
    if parsed is None:
        await message.answer(REOPEN_FORUM_TOPIC_USAGE, parse_mode="HTML")
        return

    chat_id, message_thread_id = parsed

    try:
        await perform_reopen_forum_topic(
            message.bot,
            chat_id=chat_id,
            message_thread_id=message_thread_id,
        )
    except ReopenForumTopicError as exc:
        await message.answer(f"Could not reopen forum topic: {exc}")
        return

    await message.answer(
        format_reopen_forum_topic_result(
            chat_id=chat_id,
            message_thread_id=message_thread_id,
        ),
        parse_mode="HTML",
    )


@router.message(Command("reopengeneralforumtopic"))
async def cmd_reopen_general_forum_topic(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    chat_id = _parse_reopen_general_forum_topic_args(message.text or "")
    if chat_id is None:
        await message.answer(REOPEN_GENERAL_FORUM_TOPIC_USAGE, parse_mode="HTML")
        return

    try:
        await perform_reopen_general_forum_topic(
            message.bot,
            chat_id=chat_id,
        )
    except ReopenGeneralForumTopicError as exc:
        await message.answer(f"Could not reopen General forum topic: {exc}")
        return

    await message.answer(
        format_reopen_general_forum_topic_result(chat_id=chat_id),
        parse_mode="HTML",
    )


@router.message(Command("hidegeneralforumtopic"))
async def cmd_hide_general_forum_topic(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    chat_id = _parse_hide_general_forum_topic_args(message.text or "")
    if chat_id is None:
        await message.answer(HIDE_GENERAL_FORUM_TOPIC_USAGE, parse_mode="HTML")
        return

    try:
        await perform_hide_general_forum_topic(
            message.bot,
            chat_id=chat_id,
        )
    except HideGeneralForumTopicError as exc:
        await message.answer(f"Could not hide General forum topic: {exc}")
        return

    await message.answer(
        format_hide_general_forum_topic_result(chat_id=chat_id),
        parse_mode="HTML",
    )


@router.message(Command("unhidegeneralforumtopic"))
async def cmd_unhide_general_forum_topic(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    chat_id = _parse_unhide_general_forum_topic_args(message.text or "")
    if chat_id is None:
        await message.answer(UNHIDE_GENERAL_FORUM_TOPIC_USAGE, parse_mode="HTML")
        return

    try:
        await perform_unhide_general_forum_topic(
            message.bot,
            chat_id=chat_id,
        )
    except UnhideGeneralForumTopicError as exc:
        await message.answer(f"Could not unhide General forum topic: {exc}")
        return

    await message.answer(
        format_unhide_general_forum_topic_result(chat_id=chat_id),
        parse_mode="HTML",
    )


@router.message(Command("deleteforumtopic"))
async def cmd_delete_forum_topic(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_delete_forum_topic_args(message.text or "")
    if parsed is None:
        await message.answer(DELETE_FORUM_TOPIC_USAGE, parse_mode="HTML")
        return

    chat_id, message_thread_id = parsed

    try:
        await perform_delete_forum_topic(
            message.bot,
            chat_id=chat_id,
            message_thread_id=message_thread_id,
        )
    except DeleteForumTopicError as exc:
        await message.answer(f"Could not delete forum topic: {exc}")
        return

    await message.answer(
        format_delete_forum_topic_result(
            chat_id=chat_id,
            message_thread_id=message_thread_id,
        ),
        parse_mode="HTML",
    )


@router.message(Command("unpinallforumtopicmessages"))
async def cmd_unpin_all_forum_topic_messages(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_unpin_all_forum_topic_messages_args(message.text or "")
    if parsed is None:
        await message.answer(UNPIN_ALL_FORUM_TOPIC_MESSAGES_USAGE, parse_mode="HTML")
        return

    chat_id, message_thread_id = parsed

    try:
        await perform_unpin_all_forum_topic_messages(
            message.bot,
            chat_id=chat_id,
            message_thread_id=message_thread_id,
        )
    except UnpinAllForumTopicMessagesError as exc:
        await message.answer(f"Could not unpin all forum topic messages: {exc}")
        return

    await message.answer(
        format_unpin_all_forum_topic_messages_result(
            chat_id=chat_id,
            message_thread_id=message_thread_id,
        ),
        parse_mode="HTML",
    )


@router.message(Command("unpinallgeneralforumtopicmessages"))
async def cmd_unpin_all_general_forum_topic_messages(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    chat_id = _parse_unpin_all_general_forum_topic_messages_args(message.text or "")
    if chat_id is None:
        await message.answer(
            UNPIN_ALL_GENERAL_FORUM_TOPIC_MESSAGES_USAGE,
            parse_mode="HTML",
        )
        return

    try:
        await perform_unpin_all_general_forum_topic_messages(
            message.bot,
            chat_id=chat_id,
        )
    except UnpinAllGeneralForumTopicMessagesError as exc:
        await message.answer(
            f"Could not unpin all General forum topic messages: {exc}"
        )
        return

    await message.answer(
        format_unpin_all_general_forum_topic_messages_result(chat_id=chat_id),
        parse_mode="HTML",
    )


@router.message(Command("userpersonalchatmessages"))
async def cmd_get_user_personal_chat_messages(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_get_user_personal_chat_messages_args(message.text or "")
    if parsed is None:
        await message.answer(
            GET_USER_PERSONAL_CHAT_MESSAGES_USAGE,
            parse_mode="HTML",
        )
        return

    user_id, limit = parsed

    try:
        messages = await perform_get_user_personal_chat_messages(
            message.bot,
            user_id=user_id,
            limit=limit,
        )
    except TelegramAPIError as exc:
        await message.answer(f"Could not get user personal chat messages: {exc}")
        return

    await message.answer(
        format_get_user_personal_chat_messages_result(
            user_id=user_id,
            limit=limit,
            messages=messages,
        ),
        parse_mode="HTML",
    )


@router.message(Command("userchatboosts"))
async def cmd_get_user_chat_boosts(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_get_user_chat_boosts_args(message.text or "")
    if parsed is None:
        await message.answer(
            GET_USER_CHAT_BOOSTS_USAGE,
            parse_mode="HTML",
        )
        return

    chat_id, user_id = parsed

    try:
        boosts = await perform_get_user_chat_boosts(
            message.bot,
            chat_id=chat_id,
            user_id=user_id,
        )
    except TelegramAPIError as exc:
        await message.answer(f"Could not get user chat boosts: {exc}")
        return

    await message.answer(
        format_get_user_chat_boosts_result(
            chat_id=chat_id,
            user_id=user_id,
            boosts=boosts,
        ),
        parse_mode="HTML",
    )


@router.message(Command("leavechat"))
async def cmd_leave_chat(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_leave_chat_args(message.text or "")
    if parsed is None:
        await message.answer(LEAVE_CHAT_USAGE, parse_mode="HTML")
        return

    chat_id, confirmed = parsed
    if not confirmed:
        await message.answer(LEAVE_CHAT_WARNING, parse_mode="HTML")
        return

    try:
        await perform_leave_chat(message.bot, chat_id=chat_id)
    except TelegramAPIError as exc:
        await message.answer(f"Could not leave the chat: {exc}")
        return

    await message.answer(
        format_leave_chat_result(chat_id=chat_id),
        parse_mode="HTML",
    )


@router.message(Command("approvechatjoinrequest"))
async def cmd_approve_chat_join_request(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_approve_chat_join_request_args(message.text or "")
    if parsed is None:
        await message.answer(APPROVE_CHAT_JOIN_REQUEST_USAGE, parse_mode="HTML")
        return

    chat_id, user_id = parsed
    try:
        await perform_approve_chat_join_request(
            message.bot,
            chat_id=chat_id,
            user_id=user_id,
        )
    except (TelegramAPIError, ApproveChatJoinRequestError) as exc:
        await message.answer(f"Could not approve the chat join request: {exc}")
        return

    await message.answer(
        format_approve_chat_join_request_result(chat_id=chat_id, user_id=user_id),
        parse_mode="HTML",
    )


@router.message(Command("declinechatjoinrequest"))
async def cmd_decline_chat_join_request(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_decline_chat_join_request_args(message.text or "")
    if parsed is None:
        await message.answer(DECLINE_CHAT_JOIN_REQUEST_USAGE, parse_mode="HTML")
        return

    chat_id, user_id = parsed
    try:
        await perform_decline_chat_join_request(
            message.bot,
            chat_id=chat_id,
            user_id=user_id,
        )
    except (TelegramAPIError, DeclineChatJoinRequestError) as exc:
        await message.answer(f"Could not decline the chat join request: {exc}")
        return

    await message.answer(
        format_decline_chat_join_request_result(chat_id=chat_id, user_id=user_id),
        parse_mode="HTML",
    )


@router.message(Command("createchatinvitelink"))
async def cmd_create_chat_invite_link(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_create_chat_invite_link_args(message.text or "")
    if parsed is None:
        await message.answer(CREATE_CHAT_INVITE_LINK_USAGE, parse_mode="HTML")
        return

    chat_id, options = parsed
    try:
        link = await perform_create_chat_invite_link(
            message.bot,
            chat_id=chat_id,
            **options,
        )
    except (TelegramAPIError, CreateChatInviteLinkError) as exc:
        await message.answer(f"Could not create the chat invite link: {exc}")
        return

    await message.answer(
        format_create_chat_invite_link_result(chat_id=chat_id, link=link),
        parse_mode="HTML",
    )


@router.message(Command("editchatinvitelink"))
async def cmd_edit_chat_invite_link(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_edit_chat_invite_link_args(message.text or "")
    if parsed is None:
        await message.answer(EDIT_CHAT_INVITE_LINK_USAGE, parse_mode="HTML")
        return

    chat_id, invite_link, options = parsed
    try:
        link = await perform_edit_chat_invite_link(
            message.bot,
            chat_id=chat_id,
            invite_link=invite_link,
            **options,
        )
    except (TelegramAPIError, EditChatInviteLinkError) as exc:
        await message.answer(f"Could not edit the chat invite link: {exc}")
        return

    await message.answer(
        format_edit_chat_invite_link_result(chat_id=chat_id, link=link),
        parse_mode="HTML",
    )


@router.message(Command("revokechatinvitelink"))
async def cmd_revoke_chat_invite_link(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_revoke_chat_invite_link_args(message.text or "")
    if parsed is None:
        await message.answer(REVOKE_CHAT_INVITE_LINK_USAGE, parse_mode="HTML")
        return

    chat_id, invite_link = parsed
    try:
        link = await perform_revoke_chat_invite_link(
            message.bot,
            chat_id=chat_id,
            invite_link=invite_link,
        )
    except (TelegramAPIError, RevokeChatInviteLinkError) as exc:
        await message.answer(f"Could not revoke the chat invite link: {exc}")
        return

    await message.answer(
        format_revoke_chat_invite_link_result(chat_id=chat_id, link=link),
        parse_mode="HTML",
    )


@router.message(Command("createchatsubscriptioninvitelink"))
async def cmd_create_chat_subscription_invite_link(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_create_chat_subscription_invite_link_args(message.text or "")
    if parsed is None:
        await message.answer(
            CREATE_CHAT_SUBSCRIPTION_INVITE_LINK_USAGE,
            parse_mode="HTML",
        )
        return

    chat_id, subscription_price, options = parsed
    try:
        link = await perform_create_chat_subscription_invite_link(
            message.bot,
            chat_id=chat_id,
            subscription_price=subscription_price,
            **options,
        )
    except (TelegramAPIError, CreateChatSubscriptionInviteLinkError) as exc:
        await message.answer(
            f"Could not create the chat subscription invite link: {exc}"
        )
        return

    await message.answer(
        format_create_chat_subscription_invite_link_result(
            chat_id=chat_id,
            link=link,
        ),
        parse_mode="HTML",
    )


@router.message(Command("editchatsubscriptioninvitelink"))
async def cmd_edit_chat_subscription_invite_link(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_edit_chat_subscription_invite_link_args(message.text or "")
    if parsed is None:
        await message.answer(
            EDIT_CHAT_SUBSCRIPTION_INVITE_LINK_USAGE,
            parse_mode="HTML",
        )
        return

    chat_id, invite_link, name = parsed
    try:
        link = await perform_edit_chat_subscription_invite_link(
            message.bot,
            chat_id=chat_id,
            invite_link=invite_link,
            name=name,
        )
    except (TelegramAPIError, EditChatSubscriptionInviteLinkError) as exc:
        await message.answer(f"Could not edit the chat subscription invite link: {exc}")
        return

    await message.answer(
        format_edit_chat_subscription_invite_link_result(chat_id=chat_id, link=link),
        parse_mode="HTML",
    )


@router.message(Command("setchatadministratortitle"))
async def cmd_set_chat_administrator_custom_title(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_set_chat_administrator_custom_title_args(message.text or "")
    if parsed is None:
        await message.answer(
            SET_CHAT_ADMINISTRATOR_CUSTOM_TITLE_USAGE,
            parse_mode="HTML",
        )
        return

    chat_id, user_id, custom_title = parsed

    try:
        await perform_set_chat_administrator_custom_title(
            message.bot,
            chat_id=chat_id,
            user_id=user_id,
            custom_title=custom_title,
        )
    except TelegramAPIError as exc:
        await message.answer(f"Could not set the administrator custom title: {exc}")
        return

    await message.answer(
        format_set_chat_administrator_custom_title_result(
            chat_id=chat_id,
            user_id=user_id,
            custom_title=custom_title,
        ),
        parse_mode="HTML",
    )


@router.message(Command("setchatmembertag"))
async def cmd_set_chat_member_tag(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_set_chat_member_tag_args(message.text or "")
    if parsed is None:
        await message.answer(SET_CHAT_MEMBER_TAG_USAGE, parse_mode="HTML")
        return

    chat_id, user_id, tag = parsed

    try:
        await perform_set_chat_member_tag(
            message.bot,
            chat_id=chat_id,
            user_id=user_id,
            tag=tag,
        )
    except TelegramAPIError as exc:
        await message.answer(f"Could not set the member tag: {exc}")
        return

    await message.answer(
        format_set_chat_member_tag_result(
            chat_id=chat_id,
            user_id=user_id,
            tag=tag,
        ),
        parse_mode="HTML",
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


@router.message(Command("setemojistatus"))
async def cmd_set_emoji_status(message: Message):
    if not _is_admin_action_allowed(message.chat.id):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_set_emoji_status_args(message.text or "")
    if parsed is None:
        await message.answer(SET_EMOJI_STATUS_USAGE, parse_mode="HTML")
        return

    user_id, custom_emoji_id = parsed

    try:
        await perform_set_user_emoji_status(
            message.bot,
            user_id=user_id,
            emoji_status_custom_emoji_id=custom_emoji_id,
        )
    except TelegramAPIError as exc:
        await message.answer(f"Could not set the emoji status: {exc}")
        return

    if custom_emoji_id:
        await message.answer(
            f"Set emoji status {custom_emoji_id!r} for user {user_id}."
        )
    else:
        await message.answer(f"Removed emoji status for user {user_id}.")


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
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Clear again",
                    callback_data=CALLBACK_CLEAR_HISTORY,
                )
            ]
        ]
    )
    await message.answer("Conversation history cleared.", reply_markup=keyboard)


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


def _parse_business_connection_args(text: str) -> str | None:
    """Parse ``/businessconnection`` args into ``business_connection_id``."""
    parts = (text or "").split()
    if len(parts) != 2:
        return None

    business_connection_id = parts[1].strip()
    return business_connection_id or None


def _parse_managed_bot_token_args(text: str) -> int | None:
    """Parse ``/managedbottoken`` args into managed bot ``user_id``."""
    parts = (text or "").split()
    if len(parts) != 2:
        return None

    try:
        user_id = int(parts[1])
    except ValueError:
        return None

    if user_id <= 0:
        return None
    return user_id


def _parse_managed_bot_access_settings_args(text: str) -> int | None:
    """Parse ``/managedbotaccess`` args into managed bot ``user_id``."""
    parts = (text or "").split()
    if len(parts) != 2:
        return None

    try:
        user_id = int(parts[1])
    except ValueError:
        return None

    if user_id <= 0:
        return None
    return user_id


def _parse_set_managed_bot_access_settings_args(
    text: str,
) -> tuple[int, bool, list[int], bool] | None:
    """Parse ``/setmanagedbotaccess`` args into settings and confirmation."""
    parts = (text or "").split()
    if len(parts) < 3:
        return None

    try:
        user_id = int(parts[1])
    except ValueError:
        return None

    if user_id <= 0:
        return None

    mode = parts[2].lower()
    if mode == "restricted":
        is_access_restricted = True
    elif mode == "open":
        is_access_restricted = False
    else:
        return None

    confirmed = bool(
        len(parts) >= 4
        and parts[-1] == SET_MANAGED_BOT_ACCESS_SETTINGS_CONFIRM_KEYWORD
    )
    added_user_parts = parts[3:-1] if confirmed else parts[3:]

    added_user_ids: list[int] = []
    for raw_user_id in added_user_parts:
        try:
            added_user_id = int(raw_user_id)
        except ValueError:
            return None
        if added_user_id <= 0:
            return None
        added_user_ids.append(added_user_id)

    return user_id, is_access_restricted, added_user_ids, confirmed


def _parse_replace_managed_bot_token_args(text: str) -> tuple[int, bool] | None:
    """Parse ``/replacemanagedbottoken`` args into ``(user_id, confirmed)``."""
    parts = (text or "").split()
    if len(parts) not in (2, 3):
        return None

    try:
        user_id = int(parts[1])
    except ValueError:
        return None

    if user_id <= 0:
        return None

    if len(parts) == 2:
        return user_id, False

    if parts[2] != REPLACE_MANAGED_BOT_TOKEN_CONFIRM_KEYWORD:
        return None
    return user_id, True


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


def _parse_user_profile_audios_args(text: str):
    """Parse ``/userprofileaudios`` args into ``(user_id, offset, limit)``.

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


def _parse_set_emoji_status_args(text: str):
    """Parse ``/setemojistatus`` args into ``(user_id, custom_emoji_id)``.

    Splits the raw command text into the command, the required integer
    ``user_id`` and the optional ``custom_emoji_id`` string. Returns ``None``
    when ``user_id`` is missing or not a valid integer so the caller can show
    usage.  ``custom_emoji_id`` defaults to ``None`` (remove status) when not
    provided. The caller does not validate the custom emoji id format — that is
    left to Telegram.
    """
    parts = (text or "").split()
    if len(parts) < 2:
        return None

    try:
        user_id = int(parts[1])
    except ValueError:
        return None

    custom_emoji_id = parts[2] if len(parts) >= 3 else None

    return user_id, custom_emoji_id


def _parse_ban_chat_member_args(text: str):
    """Parse ``/banchatmember`` args into ``(chat_id, user_id, until_date, revoke_messages)``.

    Splits the raw command text into the command, the required integer
    ``chat_id`` and required integer ``user_id``, the optional Unix timestamp
    ``until_date_unix`` (0 or omitted means permanent), and the optional
    ``revoke=true|false`` flag.

    Returns ``None`` when ``chat_id`` or ``user_id`` is missing or not a valid
    integer so the caller can show usage. ``until_date`` is a timezone-aware
    UTC ``datetime`` or ``None`` (permanent ban). ``revoke_messages`` defaults
    to ``None`` so Telegram uses its own default.
    """
    from datetime import datetime, timezone

    parts = (text or "").split()
    if len(parts) < 3:
        return None

    try:
        chat_id = int(parts[1])
    except ValueError:
        return None

    try:
        user_id = int(parts[2])
    except ValueError:
        return None

    until_date = None
    if len(parts) >= 4:
        try:
            ts = int(parts[3])
        except ValueError:
            return None
        if ts > 0:
            until_date = datetime.fromtimestamp(ts, tz=timezone.utc)

    revoke_messages = None
    if len(parts) >= 5:
        flag = parts[4].strip().lower()
        if flag == "revoke=true":
            revoke_messages = True
        elif flag == "revoke=false":
            revoke_messages = False
        else:
            return None

    return chat_id, user_id, until_date, revoke_messages


def _parse_ban_chat_sender_chat_args(text: str):
    """Parse ``/banchatsenderchat`` args into ``(chat_id, sender_chat_id)``."""
    parts = (text or "").split()
    if len(parts) < 3:
        return None

    try:
        chat_id = int(parts[1])
    except ValueError:
        return None

    try:
        sender_chat_id = int(parts[2])
    except ValueError:
        return None

    return chat_id, sender_chat_id


def _parse_unban_chat_sender_chat_args(text: str):
    """Parse ``/unbanchatsenderchat`` args into ``(chat_id, sender_chat_id)``."""
    parts = (text or "").split()
    if len(parts) < 3:
        return None

    try:
        chat_id = int(parts[1])
    except ValueError:
        return None

    try:
        sender_chat_id = int(parts[2])
    except ValueError:
        return None

    return chat_id, sender_chat_id


def _parse_unban_chat_member_args(text: str):
    """Parse ``/unbanchatmember`` args into ``(chat_id, user_id, only_if_banned)``.

    Returns ``None`` when required ids are missing or invalid. The optional
    ``only_if_banned=true|false`` flag defaults to ``None`` so Telegram uses
    its own default.
    """
    parts = (text or "").split()
    if len(parts) < 3:
        return None

    try:
        chat_id = int(parts[1])
    except ValueError:
        return None

    try:
        user_id = int(parts[2])
    except ValueError:
        return None

    only_if_banned = None
    if len(parts) >= 4:
        flag = parts[3].strip().lower()
        if flag == "only_if_banned=true":
            only_if_banned = True
        elif flag == "only_if_banned=false":
            only_if_banned = False
        else:
            return None

    return chat_id, user_id, only_if_banned


def _restrict_permissions_for_preset(preset: str):
    from aiogram.types import ChatPermissions

    if preset == "mute":
        return ChatPermissions(can_send_messages=False)
    if preset == "readonly":
        return ChatPermissions(
            can_send_messages=True,
            can_send_audios=False,
            can_send_documents=False,
            can_send_photos=False,
            can_send_videos=False,
            can_send_video_notes=False,
            can_send_voice_notes=False,
            can_send_polls=False,
            can_send_other_messages=False,
            can_add_web_page_previews=False,
            can_react_to_messages=False,
            can_change_info=False,
            can_invite_users=False,
            can_pin_messages=False,
            can_manage_topics=False,
        )
    if preset == "unrestrict":
        return ChatPermissions(
            can_send_messages=True,
            can_send_audios=True,
            can_send_documents=True,
            can_send_photos=True,
            can_send_videos=True,
            can_send_video_notes=True,
            can_send_voice_notes=True,
            can_send_polls=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True,
            can_react_to_messages=True,
            can_change_info=True,
            can_invite_users=True,
            can_pin_messages=True,
            can_manage_topics=True,
        )
    return None


def _parse_restrict_chat_member_args(text: str):
    """Parse ``/restrictchatmember`` args for admin-only chat restrictions."""
    from datetime import datetime, timezone

    parts = (text or "").split()
    if len(parts) < 4:
        return None

    try:
        chat_id = int(parts[1])
        user_id = int(parts[2])
    except ValueError:
        return None

    preset = parts[3].strip().lower()
    permissions = _restrict_permissions_for_preset(preset)
    if permissions is None:
        return None

    until_date = None
    if len(parts) >= 5:
        try:
            ts = int(parts[4])
        except ValueError:
            return None
        if ts > 0:
            until_date = datetime.fromtimestamp(ts, tz=timezone.utc)

    use_independent_chat_permissions = None
    if len(parts) >= 6:
        flag = parts[5].strip().lower()
        if flag == "independent=true":
            use_independent_chat_permissions = True
        elif flag == "independent=false":
            use_independent_chat_permissions = False
        else:
            return None

    return (
        chat_id,
        user_id,
        preset,
        permissions,
        until_date,
        use_independent_chat_permissions,
    )


def _chat_permissions_for_preset(preset: str):
    if preset == "closed":
        return ChatPermissions(can_send_messages=False)
    if preset == "text":
        return ChatPermissions(
            can_send_messages=True,
            can_send_audios=False,
            can_send_documents=False,
            can_send_photos=False,
            can_send_videos=False,
            can_send_video_notes=False,
            can_send_voice_notes=False,
            can_send_polls=False,
            can_send_other_messages=False,
            can_add_web_page_previews=False,
            can_react_to_messages=False,
            can_change_info=False,
            can_invite_users=False,
            can_pin_messages=False,
            can_manage_topics=False,
        )
    if preset == "media":
        return ChatPermissions(
            can_send_messages=True,
            can_send_audios=True,
            can_send_documents=True,
            can_send_photos=True,
            can_send_videos=True,
            can_send_video_notes=True,
            can_send_voice_notes=True,
            can_send_polls=False,
            can_send_other_messages=False,
            can_add_web_page_previews=False,
            can_react_to_messages=True,
            can_change_info=False,
            can_invite_users=False,
            can_pin_messages=False,
            can_manage_topics=False,
        )
    if preset == "open":
        return ChatPermissions(
            can_send_messages=True,
            can_send_audios=True,
            can_send_documents=True,
            can_send_photos=True,
            can_send_videos=True,
            can_send_video_notes=True,
            can_send_voice_notes=True,
            can_send_polls=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True,
            can_react_to_messages=True,
            can_change_info=True,
            can_invite_users=True,
            can_pin_messages=True,
            can_manage_topics=True,
        )
    return None


def _parse_set_chat_permissions_args(text: str):
    """Parse ``/setchatpermissions`` args for admin-only default permissions."""
    parts = (text or "").split()
    if len(parts) < 3:
        return None

    try:
        chat_id = int(parts[1])
    except ValueError:
        return None

    preset = parts[2].strip().lower()
    permissions = _chat_permissions_for_preset(preset)
    if permissions is None:
        return None

    use_independent_chat_permissions = None
    if len(parts) >= 4:
        flag = parts[3].strip().lower()
        if flag == "independent=true":
            use_independent_chat_permissions = True
        elif flag == "independent=false":
            use_independent_chat_permissions = False
        else:
            return None

    return chat_id, preset, permissions, use_independent_chat_permissions


def _promote_rights_for_preset(preset: str):
    from aiogram.types import ChatAdministratorRights

    if preset == "moderator":
        return ChatAdministratorRights(
            is_anonymous=False,
            can_manage_chat=True,
            can_delete_messages=True,
            can_manage_video_chats=True,
            can_restrict_members=True,
            can_promote_members=False,
            can_change_info=False,
            can_invite_users=False,
            can_post_stories=False,
            can_edit_stories=False,
            can_delete_stories=False,
            can_pin_messages=False,
            can_manage_topics=False,
        )
    if preset == "manager":
        return ChatAdministratorRights(
            is_anonymous=False,
            can_manage_chat=True,
            can_delete_messages=True,
            can_manage_video_chats=True,
            can_restrict_members=True,
            can_promote_members=False,
            can_change_info=True,
            can_invite_users=True,
            can_post_stories=False,
            can_edit_stories=False,
            can_delete_stories=False,
            can_pin_messages=True,
            can_manage_topics=True,
        )
    if preset == "demote":
        return ChatAdministratorRights(
            is_anonymous=False,
            can_manage_chat=False,
            can_delete_messages=False,
            can_manage_video_chats=False,
            can_restrict_members=False,
            can_promote_members=False,
            can_change_info=False,
            can_invite_users=False,
            can_post_stories=False,
            can_edit_stories=False,
            can_delete_stories=False,
            can_pin_messages=False,
            can_manage_topics=False,
        )
    return None


def _parse_promote_chat_member_args(text: str):
    """Parse ``/promotechatmember`` args for admin-only promotions."""
    parts = (text or "").split()
    if len(parts) != 4:
        return None

    try:
        chat_id = int(parts[1])
        user_id = int(parts[2])
    except ValueError:
        return None

    preset = parts[3].strip().lower()
    rights = _promote_rights_for_preset(preset)
    if rights is None:
        return None

    return chat_id, user_id, preset, rights


def _parse_export_chat_invite_link_args(text: str):
    """Parse ``/exportchatinvitelink`` args into ``chat_id``."""
    parts = (text or "").split()
    if len(parts) != 2:
        return None

    try:
        return int(parts[1])
    except ValueError:
        return None


def _parse_get_chat_args(text: str):
    """Parse ``/getchat`` args into ``chat_id``."""
    parts = (text or "").split()
    if len(parts) != 2:
        return None

    try:
        return int(parts[1])
    except ValueError:
        return None


def _parse_get_chat_member_count_args(text: str):
    """Parse ``/getchatmembercount`` args into ``chat_id``."""
    parts = (text or "").split()
    if len(parts) != 2:
        return None

    try:
        return int(parts[1])
    except ValueError:
        return None


def _parse_get_chat_member_args(text: str):
    """Parse ``/getchatmember`` args into ``(chat_id, user_id)``."""
    parts = (text or "").split()
    if len(parts) != 3:
        return None

    try:
        return int(parts[1]), int(parts[2])
    except ValueError:
        return None


def _parse_get_chat_administrators_args(text: str):
    """Parse ``/getchatadministrators`` args into ``chat_id``."""
    parts = (text or "").split()
    if len(parts) != 2:
        return None

    try:
        return int(parts[1])
    except ValueError:
        return None


def _parse_edit_forum_topic_args(text: str):
    """Parse ``/editforumtopic`` args into editForumTopic parameters."""
    parts = (text or "").split()
    if len(parts) < 4:
        return None

    try:
        chat_id = int(parts[1])
        message_thread_id = int(parts[2])
    except ValueError:
        return None

    if message_thread_id <= 0:
        return None

    name = None
    icon_custom_emoji_id = None
    for part in parts[3:]:
        key, sep, value = part.partition("=")
        if not sep or not value:
            return None
        if key == "name":
            name = value
        elif key == "icon_custom_emoji_id":
            icon_custom_emoji_id = value
        else:
            return None

    if name is None and icon_custom_emoji_id is None:
        return None
    if name is not None and len(name) > FORUM_TOPIC_NAME_LIMIT:
        return None

    return chat_id, message_thread_id, name, icon_custom_emoji_id


def _parse_edit_general_forum_topic_args(text: str):
    """Parse ``/editgeneralforumtopic`` args into editGeneralForumTopic parameters."""
    parts = (text or "").split(maxsplit=2)
    if len(parts) != 3:
        return None

    try:
        chat_id = int(parts[1])
    except ValueError:
        return None

    name = parts[2].strip()
    if not name or len(name) > GENERAL_FORUM_TOPIC_NAME_LIMIT:
        return None

    return chat_id, name


def _parse_create_forum_topic_args(text: str):
    """Parse ``/createforumtopic`` args into createForumTopic parameters."""
    parts = (text or "").split()
    if len(parts) < 3:
        return None

    try:
        chat_id = int(parts[1])
    except ValueError:
        return None

    name = parts[2]
    icon_color = None
    icon_custom_emoji_id = None
    for part in parts[3:]:
        key, sep, value = part.partition("=")
        if not sep or not value:
            return None
        if key == "icon_color":
            try:
                icon_color = int(value)
            except ValueError:
                return None
        elif key == "icon_custom_emoji_id":
            icon_custom_emoji_id = value
        else:
            return None

    if not name or len(name) > CREATE_FORUM_TOPIC_NAME_LIMIT:
        return None

    return chat_id, name, icon_color, icon_custom_emoji_id


def _parse_reopen_forum_topic_args(text: str):
    """Parse ``/reopenforumtopic`` args into reopenForumTopic parameters."""
    parts = (text or "").split()
    if len(parts) != 3:
        return None

    try:
        chat_id = int(parts[1])
        message_thread_id = int(parts[2])
    except ValueError:
        return None

    if message_thread_id <= 0:
        return None

    return chat_id, message_thread_id


def _parse_reopen_general_forum_topic_args(text: str):
    """Parse ``/reopengeneralforumtopic`` args into reopenGeneralForumTopic parameters."""
    parts = (text or "").split()
    if len(parts) != 2:
        return None

    try:
        return int(parts[1])
    except ValueError:
        return None


def _parse_close_general_forum_topic_args(text: str):
    """Parse ``/closegeneralforumtopic`` args into closeGeneralForumTopic parameters."""
    parts = (text or "").split()
    if len(parts) != 2:
        return None

    try:
        return int(parts[1])
    except ValueError:
        return None


def _parse_hide_general_forum_topic_args(text: str):
    """Parse ``/hidegeneralforumtopic`` args into hideGeneralForumTopic parameters."""
    parts = (text or "").split()
    if len(parts) != 2:
        return None

    try:
        return int(parts[1])
    except ValueError:
        return None


def _parse_unhide_general_forum_topic_args(text: str):
    """Parse ``/unhidegeneralforumtopic`` args into unhideGeneralForumTopic parameters."""
    parts = (text or "").split()
    if len(parts) != 2:
        return None

    try:
        return int(parts[1])
    except ValueError:
        return None


def _parse_close_forum_topic_args(text: str):
    """Parse ``/closeforumtopic`` args into closeForumTopic parameters."""
    parts = (text or "").split()
    if len(parts) != 3:
        return None

    try:
        chat_id = int(parts[1])
        message_thread_id = int(parts[2])
    except ValueError:
        return None

    if message_thread_id <= 0:
        return None

    return chat_id, message_thread_id


def _parse_delete_forum_topic_args(text: str):
    """Parse ``/deleteforumtopic`` args into deleteForumTopic parameters."""
    parts = (text or "").split()
    if len(parts) != 3:
        return None

    try:
        chat_id = int(parts[1])
        message_thread_id = int(parts[2])
    except ValueError:
        return None

    if message_thread_id <= 0:
        return None

    return chat_id, message_thread_id


def _parse_unpin_all_forum_topic_messages_args(text: str):
    """Parse ``/unpinallforumtopicmessages`` args into method parameters."""
    parts = (text or "").split()
    if len(parts) != 3:
        return None

    try:
        chat_id = int(parts[1])
        message_thread_id = int(parts[2])
    except ValueError:
        return None

    if message_thread_id <= 0:
        return None

    return chat_id, message_thread_id


def _parse_unpin_all_general_forum_topic_messages_args(text: str):
    """Parse ``/unpinallgeneralforumtopicmessages`` args."""
    parts = (text or "").split()
    if len(parts) != 2:
        return None

    try:
        return int(parts[1])
    except ValueError:
        return None


def _parse_get_user_personal_chat_messages_args(text: str):
    """Parse ``/userpersonalchatmessages`` args into ``user_id`` and limit."""
    parts = (text or "").split()
    if len(parts) not in {2, 3}:
        return None

    try:
        user_id = int(parts[1])
        limit = (
            int(parts[2])
            if len(parts) == 3
            else GET_USER_PERSONAL_CHAT_MESSAGES_MAX_LIMIT
        )
    except ValueError:
        return None

    if not (
        GET_USER_PERSONAL_CHAT_MESSAGES_MIN_LIMIT
        <= limit
        <= GET_USER_PERSONAL_CHAT_MESSAGES_MAX_LIMIT
    ):
        return None

    return user_id, limit


def _parse_get_user_chat_boosts_args(text: str):
    """Parse ``/userchatboosts`` args into ``chat_id`` and ``user_id``."""
    parts = (text or "").split()
    if len(parts) != 3:
        return None

    chat_id_text = parts[1]
    chat_id: int | str
    if chat_id_text.startswith("@"):
        chat_id = chat_id_text
    else:
        try:
            chat_id = int(chat_id_text)
        except ValueError:
            return None

    try:
        user_id = int(parts[2])
    except ValueError:
        return None

    return chat_id, user_id


def _parse_delete_chat_photo_args(text: str):
    """Parse ``/deletechatphoto`` args into ``chat_id``."""
    parts = (text or "").split()
    if len(parts) != 2:
        return None

    try:
        return int(parts[1])
    except ValueError:
        return None


def _parse_unpin_chat_message_args(text: str):
    """Parse ``/unpinchatmessage`` args into ``chat_id`` and optional ``message_id``."""
    parts = (text or "").split()
    if len(parts) not in {2, 3}:
        return None

    try:
        chat_id = int(parts[1])
        message_id = int(parts[2]) if len(parts) == 3 else None
    except ValueError:
        return None

    if message_id is not None and message_id <= 0:
        return None

    return chat_id, message_id


def _parse_unpin_all_chat_messages_args(text: str):
    """Parse ``/unpinallchatmessages`` args into ``chat_id``."""
    parts = (text or "").split()
    if len(parts) != 2:
        return None

    try:
        return int(parts[1])
    except ValueError:
        return None


def _parse_pin_chat_message_args(text: str):
    """Parse ``/pinchatmessage`` args into chat/message ids and notification flag."""
    parts = (text or "").split()
    if len(parts) not in {3, 4}:
        return None

    try:
        chat_id = int(parts[1])
        message_id = int(parts[2])
    except ValueError:
        return None

    if message_id <= 0:
        return None

    disable_notification = None
    if len(parts) == 4:
        flag = parts[3].lower()
        if flag in {"silent", "silent=true", "disable_notification=true"}:
            disable_notification = True
        elif flag in {"loud", "silent=false", "disable_notification=false"}:
            disable_notification = False
        else:
            return None

    return chat_id, message_id, disable_notification


def _parse_set_chat_photo_args(text: str):
    """Parse ``/setchatphoto`` args into ``chat_id`` and local ``photo_path``."""
    parts = (text or "").split(maxsplit=2)
    if len(parts) != 3:
        return None

    try:
        chat_id = int(parts[1])
    except ValueError:
        return None

    photo_path = parts[2].strip()
    if not photo_path:
        return None

    return chat_id, photo_path


def _parse_set_my_profile_photo_args(text: str) -> str | None:
    """Parse ``/setmyprofilephoto`` args into a local ``photo_path``."""
    parts = (text or "").split(maxsplit=1)
    if len(parts) != 2:
        return None

    photo_path = parts[1].strip()
    if not photo_path:
        return None

    return photo_path


def _parse_remove_my_profile_photo_args(text: str) -> bool:
    """Parse ``/removemyprofilephoto`` confirmation args."""
    parts = (text or "").split(maxsplit=1)
    if len(parts) != 2:
        return False

    return parts[1].strip().lower() == "confirm"


def _parse_set_chat_description_args(text: str):
    """Parse ``/setchatdescription`` args into ``chat_id`` and ``description``."""
    parts = (text or "").split(maxsplit=2)
    if len(parts) < 2:
        return None

    try:
        chat_id = int(parts[1])
    except ValueError:
        return None

    description = parts[2].strip() if len(parts) == 3 else ""
    if len(description) > SET_CHAT_DESCRIPTION_LIMIT:
        return None

    return chat_id, description


def _parse_set_chat_title_args(text: str):
    """Parse ``/setchattitle`` args into ``chat_id`` and ``title``."""
    parts = (text or "").split(maxsplit=2)
    if len(parts) != 3:
        return None

    try:
        chat_id = int(parts[1])
    except ValueError:
        return None

    title = parts[2].strip()
    if not title or len(title) > SET_CHAT_TITLE_LIMIT:
        return None

    return chat_id, title


def _parse_set_my_commands_args(text: str):
    """Parse ``/setmycommands`` args into a list of ``BotCommand`` objects."""
    parts = (text or "").split(maxsplit=1)
    if len(parts) != 2:
        return None

    raw_items = [item.strip() for item in parts[1].split("|")]
    if not raw_items or len(raw_items) > 100:
        return None

    parsed = []
    for item in raw_items:
        if not item or ":" not in item:
            return None

        command, description = (part.strip() for part in item.split(":", maxsplit=1))
        if not _is_valid_bot_command(command):
            return None
        if not description or len(description) > 256:
            return None

        parsed.append(BotCommand(command=command, description=description))

    return parsed


def _parse_set_chat_menu_button_args(text: str):
    """Parse ``/setchatmenubutton`` args into ``chat_id`` and menu button."""
    parts = (text or "").split()
    if len(parts) < 2:
        return None

    chat_id = None
    index = 1
    if parts[index].startswith("chat_id="):
        raw_chat_id = parts[index].split("=", maxsplit=1)[1]
        try:
            chat_id = int(raw_chat_id)
        except ValueError:
            return None
        index += 1

    if index >= len(parts):
        return None

    button_type = parts[index].lower()
    if button_type == "default" and index == len(parts) - 1:
        return chat_id, MenuButtonDefault()
    if button_type == "commands" and index == len(parts) - 1:
        return chat_id, MenuButtonCommands()
    if button_type != "web_app" or len(parts) != index + 3:
        return None

    text_value = parts[index + 1].strip()
    url = parts[index + 2].strip()
    if not text_value or not url.startswith(("http://", "https://")):
        return None

    return chat_id, MenuButtonWebApp(
        text=text_value,
        web_app=WebAppInfo(url=url),
    )


def _parse_set_my_name_args(text: str):
    """Parse ``/setmyname`` args into name and optional language code."""
    parts = (text or "").split(maxsplit=1)
    if len(parts) != 2:
        return None

    raw = parts[1].strip()
    if not raw:
        return "", None

    language_code = None
    language_match = re.search(r"\s+language=([A-Za-z0-9_-]+)\s*$", raw)
    if language_match:
        language_code = language_match.group(1)
        raw = raw[: language_match.start()].strip()

    if raw == "--clear":
        return "", language_code

    if len(raw) > SET_MY_NAME_LIMIT:
        return None

    return raw, language_code


def _parse_set_my_description_args(text: str):
    """Parse ``/setmydescription`` args into description and optional language code."""
    parts = (text or "").split(maxsplit=1)
    if len(parts) != 2:
        return None

    raw = parts[1].strip()
    if not raw:
        return "", None

    language_code = None
    language_match = re.search(r"\s+language=([A-Za-z0-9_-]+)\s*$", raw)
    if language_match:
        language_code = language_match.group(1)
        raw = raw[: language_match.start()].strip()

    if raw == "--clear":
        return "", language_code

    if len(raw) > SET_MY_DESCRIPTION_LIMIT:
        return None

    return raw, language_code


def _parse_set_my_short_description_args(text: str):
    """Parse ``/setmyshortdescription`` args into short description and language."""
    parts = (text or "").split(maxsplit=1)
    if len(parts) != 2:
        return None

    raw = parts[1].strip()
    if not raw:
        return "", None

    language_code = None
    language_match = re.search(r"\s+language=([A-Za-z0-9_-]+)\s*$", raw)
    if language_match:
        language_code = language_match.group(1)
        raw = raw[: language_match.start()].strip()

    if raw == "--clear":
        return "", language_code

    if len(raw) > SET_MY_SHORT_DESCRIPTION_LIMIT:
        return None

    return raw, language_code


def _parse_get_my_name_args(text: str):
    """Parse ``/getmyname`` args into optional language code."""
    parts = (text or "").split()
    if not parts:
        return False
    if len(parts) == 1:
        return None
    if len(parts) != 2 or not parts[1].startswith("language="):
        return False

    language_code = parts[1].split("=", maxsplit=1)[1].strip()
    if not language_code or not _is_valid_language_code(language_code):
        return False
    return language_code


def _parse_get_my_description_args(text: str):
    """Parse ``/getmydescription`` args into optional language code."""
    parts = (text or "").split()
    if not parts:
        return False
    if len(parts) == 1:
        return None
    if len(parts) != 2 or not parts[1].startswith("language="):
        return False

    language_code = parts[1].split("=", maxsplit=1)[1].strip()
    if not language_code or not _is_valid_language_code(language_code):
        return False
    return language_code


def _parse_get_my_short_description_args(text: str):
    """Parse ``/getmyshortdescription`` args into optional language code."""
    parts = (text or "").split()
    if not parts:
        return False
    if len(parts) == 1:
        return None
    if len(parts) != 2 or not parts[1].startswith("language="):
        return False

    language_code = parts[1].split("=", maxsplit=1)[1].strip()
    if not language_code or not _is_valid_language_code(language_code):
        return False
    return language_code


def _parse_delete_my_commands_args(text: str):
    """Parse ``/deletemycommands`` args into scope and language code."""
    parts = (text or "").split()
    if not parts:
        return None

    values: dict[str, str] = {}
    for token in parts[1:]:
        if "=" not in token:
            return None
        key, value = (part.strip() for part in token.split("=", maxsplit=1))
        if key not in {"scope", "chat_id", "user_id", "language", "language_code"}:
            return None
        if not value or key in values:
            return None
        values[key] = value

    language_code = values.get("language") or values.get("language_code")
    if language_code is not None and not _is_valid_language_code(language_code):
        return None

    scope_name = values.get("scope")
    chat_id = values.get("chat_id")
    user_id = values.get("user_id")
    if scope_name is None:
        if chat_id is not None or user_id is not None:
            return None
        return None, language_code

    scope = _build_bot_command_scope(scope_name, chat_id=chat_id, user_id=user_id)
    if scope is None:
        return None
    return scope, language_code


def _parse_get_my_commands_args(text: str):
    """Parse ``/getmycommands`` args into scope and language code."""
    return _parse_delete_my_commands_args(
        (text or "").replace("/getmycommands", "/deletemycommands", 1)
    )


def _build_bot_command_scope(
    scope_name: str,
    *,
    chat_id: str | None,
    user_id: str | None,
):
    if scope_name == "default":
        if chat_id is not None or user_id is not None:
            return None
        return BotCommandScopeDefault()
    if scope_name == "all_private_chats":
        if chat_id is not None or user_id is not None:
            return None
        return BotCommandScopeAllPrivateChats()
    if scope_name == "all_group_chats":
        if chat_id is not None or user_id is not None:
            return None
        return BotCommandScopeAllGroupChats()
    if scope_name == "all_chat_administrators":
        if chat_id is not None or user_id is not None:
            return None
        return BotCommandScopeAllChatAdministrators()
    if scope_name == "chat":
        parsed_chat_id = _parse_int(chat_id)
        if parsed_chat_id is None or user_id is not None:
            return None
        return BotCommandScopeChat(chat_id=parsed_chat_id)
    if scope_name == "chat_administrators":
        parsed_chat_id = _parse_int(chat_id)
        if parsed_chat_id is None or user_id is not None:
            return None
        return BotCommandScopeChatAdministrators(chat_id=parsed_chat_id)
    if scope_name == "chat_member":
        parsed_chat_id = _parse_int(chat_id)
        parsed_user_id = _parse_int(user_id)
        if parsed_chat_id is None or parsed_user_id is None:
            return None
        return BotCommandScopeChatMember(chat_id=parsed_chat_id, user_id=parsed_user_id)
    return None


def _parse_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _is_valid_language_code(language_code: str) -> bool:
    return 2 <= len(language_code) <= 8 and bool(
        re.fullmatch(r"[a-z]{2,3}(?:-[A-Z]{2})?", language_code)
    )


def _is_valid_bot_command(command: str) -> bool:
    if not 1 <= len(command) <= 32:
        return False
    return all(char.islower() or char.isdigit() or char == "_" for char in command)


def _parse_set_chat_sticker_set_args(text: str):
    """Parse ``/setchatstickerset`` args into ``chat_id`` and sticker set name."""
    parts = (text or "").split(maxsplit=2)
    if len(parts) != 3:
        return None

    try:
        chat_id = int(parts[1])
    except ValueError:
        return None

    sticker_set_name = parts[2].strip()
    if not sticker_set_name or any(char.isspace() for char in sticker_set_name):
        return None

    return chat_id, sticker_set_name


def _parse_delete_chat_sticker_set_args(text: str):
    """Parse ``/deletechatstickerset`` args into ``chat_id``."""
    parts = (text or "").split()
    if len(parts) != 2:
        return None

    try:
        return int(parts[1])
    except ValueError:
        return None


def _parse_approve_chat_join_request_args(text: str):
    """Parse ``/approvechatjoinrequest`` args into ``chat_id`` and ``user_id``."""
    parts = (text or "").split()
    if len(parts) != 3:
        return None

    try:
        chat_id = int(parts[1])
        user_id = int(parts[2])
    except ValueError:
        return None

    if chat_id == 0 or user_id <= 0:
        return None

    return chat_id, user_id


def _parse_decline_chat_join_request_args(text: str):
    """Parse ``/declinechatjoinrequest`` args into ``chat_id`` and ``user_id``."""
    parts = (text or "").split()
    if len(parts) != 3:
        return None

    try:
        chat_id = int(parts[1])
        user_id = int(parts[2])
    except ValueError:
        return None

    if chat_id == 0 or user_id <= 0:
        return None

    return chat_id, user_id


def _parse_leave_chat_args(text: str):
    """Parse ``/leavechat`` args into ``chat_id`` and confirmation state."""
    parts = (text or "").split()
    if len(parts) not in {2, 3}:
        return None

    try:
        chat_id = int(parts[1])
    except ValueError:
        return None

    if chat_id == 0:
        return None

    confirmed = False
    if len(parts) == 3:
        if parts[2].lower() != LEAVE_CHAT_CONFIRM_KEYWORD:
            return None
        confirmed = True

    return chat_id, confirmed


def _parse_create_chat_invite_link_args(text: str):
    """Parse ``/createchatinvitelink`` args into chat id and options."""
    parts = (text or "").split()
    if len(parts) < 2:
        return None

    try:
        chat_id = int(parts[1])
    except ValueError:
        return None

    options = _parse_chat_invite_link_options(parts[2:])
    if options is None:
        return None

    return chat_id, options


def _parse_edit_chat_invite_link_args(text: str):
    """Parse ``/editchatinvitelink`` args into chat id, link and options."""
    parts = (text or "").split()
    if len(parts) < 3:
        return None

    try:
        chat_id = int(parts[1])
    except ValueError:
        return None

    options = _parse_chat_invite_link_options(parts[3:])
    if options is None:
        return None

    return chat_id, parts[2], options


def _parse_revoke_chat_invite_link_args(text: str):
    """Parse ``/revokechatinvitelink`` args into chat id and invite link."""
    parts = (text or "").split()
    if len(parts) != 3:
        return None

    try:
        chat_id = int(parts[1])
    except ValueError:
        return None

    if not parts[2]:
        return None

    return chat_id, parts[2]


def _parse_create_chat_subscription_invite_link_args(text: str):
    """Parse ``/createchatsubscriptioninvitelink`` args."""
    parts = (text or "").split()
    if len(parts) < 3 or len(parts) > 5:
        return None

    try:
        chat_id = int(parts[1])
        subscription_price = int(parts[2])
    except ValueError:
        return None

    if not 1 <= subscription_price <= 10000:
        return None

    options = {
        "name": None,
        "subscription_period": 2592000,
    }
    for token in parts[3:]:
        key, separator, value = token.partition("=")
        if separator != "=":
            return None
        if key == "name":
            if len(value) > 32:
                return None
            options["name"] = value
        elif key == "subscription_period":
            try:
                subscription_period = int(value)
            except ValueError:
                return None
            if subscription_period != 2592000:
                return None
            options["subscription_period"] = subscription_period
        else:
            return None

    return chat_id, subscription_price, options


def _parse_edit_chat_subscription_invite_link_args(text: str):
    """Parse ``/editchatsubscriptioninvitelink`` args into chat id, link and name."""
    parts = (text or "").split()
    if len(parts) < 3 or len(parts) > 4:
        return None

    try:
        chat_id = int(parts[1])
    except ValueError:
        return None

    name = None
    if len(parts) == 4:
        key, separator, value = parts[3].partition("=")
        if key != "name" or separator != "=" or len(value) > 32:
            return None
        name = value

    return chat_id, parts[2], name


def _parse_chat_invite_link_options(tokens):
    options = {
        "name": None,
        "expire_date": None,
        "member_limit": None,
        "creates_join_request": None,
    }
    for token in tokens:
        if "=" not in token:
            return None
        key, value = token.split("=", 1)
        if key == "name":
            options["name"] = value
        elif key == "expire_date":
            try:
                options["expire_date"] = int(value)
            except ValueError:
                return None
        elif key == "member_limit":
            try:
                member_limit = int(value)
            except ValueError:
                return None
            if not 1 <= member_limit <= 99999:
                return None
            options["member_limit"] = member_limit
        elif key == "creates_join_request":
            parsed = _parse_bool_value(value)
            if parsed is None:
                return None
            options["creates_join_request"] = parsed
        else:
            return None

    if options["creates_join_request"] is True and options["member_limit"] is not None:
        return None

    return options


def _parse_bool_value(value: str):
    normalized = value.lower()
    if normalized in {"true", "1", "yes", "on"}:
        return True
    if normalized in {"false", "0", "no", "off"}:
        return False
    return None


def _parse_set_chat_administrator_custom_title_args(text: str):
    """Parse ``/setchatadministratortitle`` args into ``(chat_id, user_id, title)``."""
    parts = (text or "").split(maxsplit=3)
    if len(parts) < 4:
        return None

    try:
        chat_id = int(parts[1])
        user_id = int(parts[2])
    except ValueError:
        return None

    custom_title = parts[3].strip()
    if not custom_title:
        return None

    return chat_id, user_id, custom_title


def _parse_set_chat_member_tag_args(text: str):
    """Parse ``/setchatmembertag`` args into ``(chat_id, user_id, tag)``."""
    parts = (text or "").split(maxsplit=3)
    if len(parts) < 4:
        return None

    try:
        chat_id = int(parts[1])
        user_id = int(parts[2])
    except ValueError:
        return None

    tag = parts[3].strip()
    if not tag:
        return None

    if tag.lower() in {"clear", "none", "-"}:
        tag = None

    return chat_id, user_id, tag
