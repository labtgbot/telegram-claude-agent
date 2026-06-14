import json
import re
from html import escape

import structlog
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
from bot.utils.admin_auth import (
    is_admin_action_allowed as check_admin_action_allowed,
    is_admin_or_allowed_chat as check_admin_or_allowed_chat,
)
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
from bot.services.answer_chat_join_request_query import (
    CHAT_JOIN_REQUEST_QUERY_RESULTS,
    AnswerChatJoinRequestQueryError,
    perform_answer_chat_join_request_query,
)
from bot.services.send_chat_join_request_web_app import (
    SendChatJoinRequestWebAppError,
    perform_send_chat_join_request_web_app,
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
from bot.services.get_chat_menu_button import (
    format_get_chat_menu_button_result,
    perform_get_chat_menu_button,
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
from bot.services.set_my_default_administrator_rights import (
    format_set_my_default_administrator_rights_result,
    perform_set_my_default_administrator_rights,
)
from bot.services.get_my_default_administrator_rights import (
    format_get_my_default_administrator_rights_result,
    perform_get_my_default_administrator_rights,
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
from bot.services.get_sticker_set import (
    GetStickerSetError,
    format_sticker_set,
    perform_get_sticker_set,
)
from bot.services.get_custom_emoji_stickers import (
    GetCustomEmojiStickersError,
    GetCustomEmojiStickersValidationError,
    format_custom_emoji_stickers,
    perform_get_custom_emoji_stickers,
)
from bot.services.upload_sticker_file import (
    UploadStickerFileError,
    format_upload_sticker_file_result,
    perform_upload_sticker_file,
)
from bot.services.create_new_sticker_set import (
    CreateNewStickerSetError,
    format_create_new_sticker_set_result,
    perform_create_new_sticker_set,
)
from bot.services.add_sticker_to_set import (
    AddStickerToSetError,
    format_add_sticker_to_set_result,
    perform_add_sticker_to_set,
)
from bot.services.replace_sticker_in_set import (
    ReplaceStickerInSetError,
    format_replace_sticker_in_set_result,
    perform_replace_sticker_in_set,
)
from bot.services.set_sticker_position_in_set import (
    SetStickerPositionInSetError,
    format_set_sticker_position_in_set_result,
    perform_set_sticker_position_in_set,
)
from bot.services.set_sticker_emoji_list import (
    SetStickerEmojiListError,
    format_set_sticker_emoji_list_result,
    perform_set_sticker_emoji_list,
)
from bot.services.set_sticker_mask_position import (
    SetStickerMaskPositionError,
    format_set_sticker_mask_position_result,
    perform_set_sticker_mask_position,
)
from bot.services.set_sticker_keywords import (
    SetStickerKeywordsError,
    format_set_sticker_keywords_result,
    perform_set_sticker_keywords,
)
from bot.services.set_sticker_set_title import (
    SetStickerSetTitleError,
    format_set_sticker_set_title_result,
    perform_set_sticker_set_title,
)
from bot.services.set_sticker_set_thumbnail import (
    SetStickerSetThumbnailError,
    format_set_sticker_set_thumbnail_result,
    perform_set_sticker_set_thumbnail,
)
from bot.services.set_custom_emoji_sticker_set_thumbnail import (
    SetCustomEmojiStickerSetThumbnailError,
    format_set_custom_emoji_sticker_set_thumbnail_result,
    perform_set_custom_emoji_sticker_set_thumbnail,
)
from bot.services.delete_sticker_from_set import (
    DeleteStickerFromSetError,
    format_delete_sticker_from_set_result,
    perform_delete_sticker_from_set,
)
from bot.services.delete_sticker_set import (
    DeleteStickerSetError,
    format_delete_sticker_set_result,
    perform_delete_sticker_set,
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
from bot.services.send_game import SendGameValidationError, perform_send_game
from bot.services.get_game_high_scores import (
    GetGameHighScoresValidationError,
    perform_get_game_high_scores,
)
from bot.services.set_game_score import (
    SetGameScoreValidationError,
    perform_set_game_score,
)
from bot.services.send_live_photo import SendLivePhotoError, perform_send_live_photo
from bot.services.send_location import perform_send_location
from bot.services.send_media_group import perform_send_media_group
from bot.services.send_message_draft import (
    MESSAGE_DRAFT_TEXT_LIMIT,
    SendMessageDraftError,
    perform_send_message_draft,
)
from bot.services.send_rich_message import (
    SendRichMessageError,
    perform_send_rich_message,
)
from bot.services.send_rich_message_draft import (
    SendRichMessageDraftError,
    perform_send_rich_message_draft,
)
from bot.services.send_sticker import perform_send_sticker
from bot.services.edit_message_caption import (
    EDIT_MESSAGE_CAPTION_LIMIT,
    EditMessageCaptionError,
    perform_edit_message_caption,
)
from bot.services.edit_message_media import (
    EDIT_MESSAGE_MEDIA_CAPTION_LIMIT,
    EDIT_MESSAGE_MEDIA_TYPES,
    EditMessageMediaError,
    perform_edit_message_media,
)
from bot.services.edit_message_reply_markup import (
    EditMessageReplyMarkupError,
    perform_edit_message_reply_markup,
)
from bot.services.edit_message_checklist import (
    EditMessageChecklistError,
    perform_edit_message_checklist,
)
from bot.services.edit_message_live_location import (
    EditMessageLiveLocationError,
    perform_edit_message_live_location,
)
from bot.services.stop_message_live_location import (
    StopMessageLiveLocationError,
    perform_stop_message_live_location,
)
from bot.services.gift_premium_subscription import (
    GiftPremiumSubscriptionError,
    MAX_PREMIUM_MONTHS,
    MIN_PREMIUM_MONTHS,
    perform_gift_premium_subscription,
)
from bot.services.verify_user import (
    VERIFY_USER_DESCRIPTION_LIMIT,
    VerifyUserError,
    perform_verify_user,
)
from bot.services.remove_user_verification import (
    RemoveUserVerificationError,
    perform_remove_user_verification,
)
from bot.services.remove_chat_verification import (
    RemoveChatVerificationError,
    perform_remove_chat_verification,
)
from bot.services.verify_chat import (
    VERIFY_CHAT_DESCRIPTION_LIMIT,
    VerifyChatError,
    perform_verify_chat,
)
from bot.services.send_gift import SendGiftError, perform_send_gift
from bot.services.create_invoice_link import (
    CreateInvoiceLinkError,
    perform_create_invoice_link,
)
from bot.services.send_invoice import SendInvoiceError, perform_send_invoice
from bot.services.send_paid_media import SendPaidMediaError, perform_send_paid_media
from bot.services.answer_web_app_query import (
    AnswerWebAppQueryError,
    perform_answer_web_app_query,
)
from bot.services.save_prepared_inline_message import (
    SavePreparedInlineMessageError,
    perform_save_prepared_inline_message,
)
from bot.services.set_passport_data_errors import (
    SetPassportDataErrorsError,
    perform_set_passport_data_errors,
)
from bot.services.save_prepared_keyboard_button import (
    SavePreparedKeyboardButtonError,
    perform_save_prepared_keyboard_button,
)
from bot.services.post_story import (
    POST_STORY_ACTIVE_PERIODS,
    POST_STORY_CAPTION_LIMIT,
    PostStoryError,
    perform_post_story,
)
from bot.services.edit_story import EditStoryError, perform_edit_story
from bot.services.repost_story import RepostStoryError, perform_repost_story
from bot.services.delete_story import DeleteStoryError, perform_delete_story
from bot.services.send_photo import perform_send_photo
from bot.services.send_poll import SendPollError, perform_send_poll
from bot.services.stop_poll import (
    StopPollValidationError,
    format_stop_poll_result,
    perform_stop_poll,
)
from bot.services.approve_suggested_post import (
    ApproveSuggestedPostError,
    format_approve_suggested_post_result,
    perform_approve_suggested_post,
)
from bot.services.decline_suggested_post import (
    DECLINE_SUGGESTED_POST_COMMENT_LIMIT,
    DeclineSuggestedPostError,
    format_decline_suggested_post_result,
    perform_decline_suggested_post,
)
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
from bot.services.get_business_account_star_balance import (
    GetBusinessAccountStarBalanceError,
    format_business_account_star_balance,
    perform_get_business_account_star_balance,
)
from bot.services.get_my_star_balance import (
    GetMyStarBalanceError,
    format_my_star_balance,
    perform_get_my_star_balance,
)
from bot.services.get_star_transactions import (
    GET_STAR_TRANSACTIONS_MAX_LIMIT,
    GET_STAR_TRANSACTIONS_MIN_LIMIT,
    GetStarTransactionsError,
    format_star_transactions,
    perform_get_star_transactions,
)
from bot.services.refund_star_payment import (
    RefundStarPaymentError,
    format_refund_star_payment_result,
    perform_refund_star_payment,
)
from bot.services.edit_user_star_subscription import (
    EditUserStarSubscriptionError,
    format_edit_user_star_subscription_result,
    perform_edit_user_star_subscription,
)
from bot.services.get_business_account_gifts import (
    GET_BUSINESS_ACCOUNT_GIFTS_MAX_LIMIT,
    GET_BUSINESS_ACCOUNT_GIFTS_MIN_LIMIT,
    GetBusinessAccountGiftsError,
    format_business_account_gifts,
    perform_get_business_account_gifts,
)
from bot.services.get_user_gifts import (
    GET_USER_GIFTS_MAX_LIMIT,
    GET_USER_GIFTS_MIN_LIMIT,
    GetUserGiftsError,
    format_user_gifts,
    perform_get_user_gifts,
)
from bot.services.get_chat_gifts import (
    GET_CHAT_GIFTS_MAX_LIMIT,
    GET_CHAT_GIFTS_MIN_LIMIT,
    GetChatGiftsError,
    format_chat_gifts,
    perform_get_chat_gifts,
)
from bot.services.read_business_message import (
    ReadBusinessMessageError,
    perform_read_business_message,
)
from bot.services.delete_business_messages import (
    DeleteBusinessMessagesError,
    MAX_DELETE_BUSINESS_MESSAGES,
    perform_delete_business_messages,
)
from bot.services.set_business_account_name import (
    MAX_BUSINESS_ACCOUNT_NAME_LENGTH,
    SetBusinessAccountNameError,
    perform_set_business_account_name,
)
from bot.services.set_business_account_bio import (
    MAX_BUSINESS_ACCOUNT_BIO_LENGTH,
    SetBusinessAccountBioError,
    perform_set_business_account_bio,
)
from bot.services.set_business_account_profile_photo import (
    SetBusinessAccountProfilePhotoError,
    format_set_business_account_profile_photo_result,
    perform_set_business_account_profile_photo,
)
from bot.services.remove_business_account_profile_photo import (
    RemoveBusinessAccountProfilePhotoError,
    format_remove_business_account_profile_photo_result,
    perform_remove_business_account_profile_photo,
)
from bot.services.set_business_account_gift_settings import (
    ACCEPTED_GIFT_TYPE_KEYS,
    SetBusinessAccountGiftSettingsError,
    format_set_business_account_gift_settings_result,
    perform_set_business_account_gift_settings,
)
from bot.services.transfer_business_account_stars import (
    TransferBusinessAccountStarsError,
    format_transfer_business_account_stars_result,
    perform_transfer_business_account_stars,
)
from bot.services.convert_gift_to_stars import (
    ConvertGiftToStarsError,
    format_convert_gift_to_stars_result,
    perform_convert_gift_to_stars,
)
from bot.services.upgrade_gift import (
    UpgradeGiftError,
    format_upgrade_gift_result,
    perform_upgrade_gift,
)
from bot.services.transfer_gift import (
    TransferGiftError,
    format_transfer_gift_result,
    perform_transfer_gift,
)
from bot.services.set_business_account_username import (
    MAX_BUSINESS_ACCOUNT_USERNAME_LENGTH,
    MIN_BUSINESS_ACCOUNT_USERNAME_LENGTH,
    SetBusinessAccountUsernameError,
    perform_set_business_account_username,
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
from bot.services.get_available_gifts import (
    GetAvailableGiftsError,
    format_available_gifts,
    perform_get_available_gifts,
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
from bot.services.delete_message_reaction import (
    format_delete_message_reaction_result,
    perform_delete_message_reaction,
)
from bot.services.delete_all_message_reactions import (
    DeleteAllMessageReactionsError,
    format_delete_all_message_reactions_result,
    perform_delete_all_message_reactions,
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
from bot.services.delete_message import (
    format_delete_message_result,
    perform_delete_message,
)
from bot.services.delete_messages import (
    DeleteMessagesError,
    format_delete_messages_result,
    perform_delete_messages,
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
from bot.utils.user_errors import format_user_error, log_user_error_context
from bot.services.claude_proxy import ClaudeProxyClient

router = Router()
logger = structlog.get_logger()
INVALID_COMMAND_ARGS = object()

LOGOUT_CONFIRM_KEYWORD = "confirm"
CALLBACK_SETTINGS_REFRESH = "settings:refresh"
CALLBACK_MODEL_PREFIX = "model:set:"
CALLBACK_CLEAR_HISTORY = "history:clear"
CALLBACK_LOGOUT_CONFIRM = "admin:logout:confirm"
CALLBACK_CLOSE_CONFIRM = "admin:close:confirm"
CALLBACK_CANCEL = "action:cancel"
TELEGRAM_CALLBACK_DATA_LIMIT = 64


def _command_name(message: Message) -> str | None:
    text = getattr(message, "text", None) or ""
    return text.split(maxsplit=1)[0] if text else None


async def _answer_operation_failed(message: Message, summary: str, exc: Exception) -> None:
    log_user_error_context(
        logger,
        "command_handler_failed",
        exc,
        command=_command_name(message),
        chat_id=getattr(message.chat, "id", None),
        operation=summary,
    )
    await message.answer(format_user_error(summary))


async def _answer_validation_failed(
    message: Message, summary: str, exc: Exception
) -> None:
    logger.info(
        "command_validation_failed",
        error_type=type(exc).__name__,
        error=str(exc),
        command=_command_name(message),
        chat_id=getattr(message.chat, "id", None),
        operation=summary,
    )
    await message.answer(summary)


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

STICKER_USAGE = (
    "<b>sticker usage</b>\n"
    "Sends a sticker or custom emoji into this chat instead of plain text. "
    "Pass an HTTP(S) URL Telegram can fetch or a file_id of a sticker already "
    "on Telegram servers.\n"
    "Usage: <code>/sticker &lt;url_or_file_id&gt; [emoji]</code>\n"
    "The optional emoji hint is passed to Telegram. Static and animated "
    "stickers are limited to 512 KB; video stickers are limited to 256 KB and "
    "must fit in a 512x512 square."
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

INVOICE_TITLE_LIMIT = 32
INVOICE_DESCRIPTION_LIMIT = 255
INVOICE_PAYLOAD_LIMIT = 128
INVOICE_MIN_STARS = 1
INVOICE_MAX_STARS = 25000

SEND_INVOICE_USAGE = (
    "<b>sendinvoice usage</b>\n"
    "Sends a Telegram Stars test invoice into this chat through "
    "<code>sendInvoice</code>. This is an admin-only payments probe, not a "
    "full billing flow.\n"
    "Usage: <code>/sendinvoice &lt;star_count&gt; &lt;payload&gt; &lt;title&gt; | "
    "&lt;description&gt;</code>\n"
    "The payload must be unique per invoice and signed by the operator's "
    "billing process before production use. Telegram payment updates "
    "<code>pre_checkout_query</code> and <code>successful_payment</code> are "
    "required to complete real purchases."
)

CREATE_INVOICE_LINK_USAGE = (
    "<b>createinvoicelink usage</b>\n"
    "Creates a Telegram Stars invoice link through "
    "<code>createInvoiceLink</code>. This is an admin-only payments probe, not "
    "a full billing flow.\n"
    "Usage: <code>/createinvoicelink &lt;star_count&gt; &lt;payload&gt; "
    "&lt;title&gt; | &lt;description&gt;</code>\n"
    "The payload must be unique per invoice and signed by the operator's "
    "billing process before production use. Telegram payment updates "
    "<code>pre_checkout_query</code> and <code>successful_payment</code> are "
    "required to complete real purchases."
)

ANSWER_WEB_APP_QUERY_USAGE = (
    "<b>answerwebappquery usage</b>\n"
    "Answers a Telegram Web App query and sends one InlineQueryResult on "
    "behalf of the user to the chat where the Web App was opened.\n"
    "Usage: <code>/answerwebappquery &lt;web_app_query_id&gt; &lt;result_json&gt;</code>\n"
    "The result JSON must be one InlineQueryResult object, for example an "
    "article result with input_message_content."
)

SAVE_PREPARED_INLINE_MESSAGE_USAGE = (
    "<b>savepreparedinline usage</b>\n"
    "Saves one InlineQueryResult as a prepared inline message for a Telegram "
    "user. The user must allow the bot to message them and can later send the "
    "prepared message through Telegram's inline-mode flow.\n"
    "Usage: <code>/savepreparedinline &lt;user_id&gt; &lt;result_json&gt; "
    "[allow_user_chats=true|false] [allow_bot_chats=true|false] "
    "[allow_group_chats=true|false] [allow_channel_chats=true|false]</code>\n"
    "The result JSON must be one InlineQueryResult object. Optional allow_* "
    "flags restrict which chat types Telegram may offer for sending it."
)

SET_PASSPORT_DATA_ERRORS_USAGE = (
    "<b>setpassporterrors usage</b>\n"
    "Reports Telegram Passport validation errors for a user after that user "
    "submitted encrypted Passport data to this bot. This is an admin-only "
    "validation probe and does not call free-claude-code.\n"
    "Usage: <code>/setpassporterrors &lt;user_id&gt; &lt;errors_json_array&gt;</code>\n"
    "The errors JSON must be a non-empty array of PassportElementError "
    "objects from Telegram Bot API documentation. Do not paste decrypted "
    "Passport data into this command."
)

SAVE_PREPARED_KEYBOARD_BUTTON_USAGE = (
    "<b>savepreparedkeyboard usage</b>\n"
    "Saves a prepared keyboard button for a Telegram Mini App user. The button "
    "is tied to a prepared inline message created earlier with "
    "savePreparedInlineMessage and can be shown by the Mini App integration.\n"
    "Usage: <code>/savepreparedkeyboard &lt;user_id&gt; "
    "&lt;prepared_message_id&gt;</code>\n"
    "The user must have opened the Mini App and authorized the bot context; "
    "Telegram validates the prepared message id and user eligibility."
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

POLL_OPTION_LINK_SEPARATOR = "=>"

POLL_MIN_OPTIONS = 1

POLL_MAX_OPTIONS = 12

POLL_QUESTION_MAX_LENGTH = 300

POLL_OPTION_MAX_LENGTH = 100

POLL_USAGE = (
    "<b>poll usage</b>\n"
    "Sends a native poll into this chat as a real Telegram poll (an interactive "
    "question with tappable answer options) instead of plain text. Pass the "
    "question followed by the answer options, all separated by a vertical bar.\n"
    "Usage: <code>/poll &lt;question&gt; | &lt;option&gt; | &lt;option&gt; "
    "[| &lt;option&gt; ...]</code>\n"
    "Use <code>&lt;option&gt; =&gt; https://example.com</code> to attach a "
    "Bot API 10.1 link media object to an option.\n"
    "Provide 1-12 options. The question is limited to 300 characters and each "
    "option text to 100 characters; the question and every option may contain "
    "spaces and must be non-empty."
)

STOP_POLL_USAGE = (
    "<b>stoppoll usage</b>\n"
    "Stops a native Telegram poll that was previously sent by the bot, "
    "returning the final poll state. Pass the chat id and the poll message id.\n"
    "Usage: <code>/stoppoll &lt;chat_id&gt; &lt;message_id&gt;</code>\n"
    "The bot must have sent the poll, and the poll must still be open."
)

APPROVE_SUGGESTED_POST_USAGE = (
    "<b>approvesuggestedpost usage</b>\n"
    "Approves a suggested post in a direct messages chat via "
    "<code>approveSuggestedPost</code>. Pass the direct messages chat id, the "
    "suggested post message id, and optionally a future Unix send date.\n"
    "Usage: <code>/approvesuggestedpost &lt;chat_id&gt; &lt;message_id&gt; "
    "[send_date]</code>\n"
    "The bot must have the required Telegram rights for the direct messages "
    "chat. Without <code>send_date</code>, Telegram publishes the approved post "
    "at the date chosen in the suggestion."
)

DECLINE_SUGGESTED_POST_USAGE = (
    "<b>declinesuggestedpost usage</b>\n"
    "Declines a suggested post in a direct messages chat via "
    "<code>declineSuggestedPost</code>. Pass the direct messages chat id, the "
    "suggested post message id, and optionally a comment for the creator.\n"
    "Usage: <code>/declinesuggestedpost &lt;chat_id&gt; &lt;message_id&gt; "
    "[comment]</code>\n"
    "The bot must have the <code>can_manage_direct_messages</code> Telegram "
    "administrator right for the corresponding channel chat. The optional "
    "comment is limited to 128 characters."
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

GAME_USAGE = (
    "<b>game usage</b>\n"
    "Sends a Telegram game into this chat via <code>sendGame</code>. The game "
    "must already be created for this bot in BotFather, and Telegram identifies "
    "it by its short name.\n"
    "Usage: <code>/game &lt;game_short_name&gt;</code>\n"
    "The short name is required and must be a single non-empty token."
)

SET_GAME_SCORE_USAGE = (
    "<b>setgamescore usage</b>\n"
    "Sets a Telegram game score via <code>setGameScore</code>. Target a normal "
    "game message with <code>chat_id</code> and <code>message_id</code>, or an "
    "inline game message with <code>inline_message_id</code>.\n"
    "Usage: <code>/setgamescore &lt;user_id&gt; &lt;score&gt; "
    "chat_id=&lt;chat_id&gt; message_id=&lt;message_id&gt; "
    "[force=true] [disable_edit_message=true]</code>\n"
    "Usage: <code>/setgamescore &lt;user_id&gt; &lt;score&gt; "
    "inline_message_id=&lt;inline_message_id&gt; "
    "[force=true] [disable_edit_message=true]</code>\n"
    "The score must be a non-negative integer."
)

GET_GAME_HIGH_SCORES_USAGE = (
    "<b>gamehighscores usage</b>\n"
    "Fetches Telegram game high scores via <code>getGameHighScores</code>. "
    "Target a normal game message with <code>chat_id</code> and "
    "<code>message_id</code>, or an inline game message with "
    "<code>inline_message_id</code>.\n"
    "Usage: <code>/gamehighscores &lt;user_id&gt; "
    "chat_id=&lt;chat_id&gt; message_id=&lt;message_id&gt;</code>\n"
    "Usage: <code>/gamehighscores &lt;user_id&gt; "
    "inline_message_id=&lt;inline_message_id&gt;</code>"
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

RICH_MESSAGE_USAGE = (
    "<b>richmessage usage</b>\n"
    "Sends a Bot API 10.1 rich message into this chat via "
    "<code>sendRichMessage</code>. Pass one JSON <code>InputRichMessage</code> "
    "object with exactly one of <code>html</code> or <code>markdown</code>.\n"
    "Usage: <code>/richmessage {\"html\":\"&lt;h1&gt;Status&lt;/h1&gt;\"}</code>\n"
    "Optional JSON fields: <code>is_rtl</code>, "
    "<code>skip_entity_detection</code>."
)

RICH_MESSAGE_DRAFT_USAGE = (
    "<b>richmessagedraft usage</b>\n"
    "Streams an ephemeral Bot API 10.1 rich message draft into this private "
    "chat via <code>sendRichMessageDraft</code>. The draft is temporary and "
    "must be followed by a persisted <code>sendRichMessage</code> call when "
    "the content is final.\n"
    "Usage: <code>/richmessagedraft &lt;draft_id&gt; "
    "{\"html\":\"&lt;tg-thinking&gt;&lt;/tg-thinking&gt;\"}</code>\n"
    "The <code>draft_id</code> must be non-zero."
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

EDIT_MESSAGE_CHECKLIST_USAGE = (
    "<b>editchecklist usage</b>\n"
    "Edits an existing Telegram checklist message on behalf of a connected "
    "business account. Pass the business connection id, target chat id, target "
    "message id, then the replacement checklist title and tasks separated by a "
    "vertical bar.\n"
    "Usage: <code>/editchecklist &lt;business_connection_id&gt; &lt;chat_id&gt; "
    "&lt;message_id&gt; &lt;title&gt; | &lt;task&gt; [| &lt;task&gt; ...]</code>\n"
    "Provide 1-30 tasks. The title is limited to 255 characters and each task "
    "to 100 characters; the title and every task may contain spaces and must be "
    "non-empty."
)

EDIT_MESSAGE_CAPTION_USAGE = (
    "<b>editcaption usage</b>\n"
    "Edits the caption of a media message previously sent by this bot. This is "
    "an admin-only message-management command. Target a regular message with "
    "<code>chat_id</code> and <code>message_id</code>, or target inline mode "
    "with <code>inline=&lt;inline_message_id&gt;</code>.\n"
    "Usage: <code>/editcaption &lt;chat_id&gt; &lt;message_id&gt; [caption]</code>\n"
    "Usage: <code>/editcaption inline=&lt;inline_message_id&gt; [caption]</code>\n"
    f"The caption is optional and limited to {EDIT_MESSAGE_CAPTION_LIMIT} "
    "characters. An omitted caption clears the current caption. Optional "
    "trailing flags: <code>parse_mode=HTML</code>, <code>above=true</code>."
)

EDIT_MESSAGE_MEDIA_USAGE = (
    "<b>editmedia usage</b>\n"
    "Edits the media of a message previously sent by this bot. This is an "
    "admin-only message-management command. Target a regular message with "
    "<code>chat_id</code> and <code>message_id</code>, or target inline mode "
    "with <code>inline=&lt;inline_message_id&gt;</code>.\n"
    "Usage: <code>/editmedia &lt;chat_id&gt; &lt;message_id&gt; &lt;type&gt; "
    "&lt;media&gt; [caption]</code>\n"
    "Usage: <code>/editmedia inline=&lt;inline_message_id&gt; &lt;type&gt; "
    "&lt;media&gt; [caption]</code>\n"
    f"Supported types: {', '.join(sorted(EDIT_MESSAGE_MEDIA_TYPES))}. "
    f"The optional caption is limited to {EDIT_MESSAGE_MEDIA_CAPTION_LIMIT} "
    "characters. Optional trailing flags: <code>parse_mode=HTML</code>, "
    "<code>above=true</code>, <code>spoiler=true</code>."
)

EDIT_MESSAGE_REPLY_MARKUP_USAGE = (
    "<b>editreplymarkup usage</b>\n"
    "Edits only the inline keyboard of a message previously sent by this bot. "
    "This is an admin-only message-management command. Target a regular "
    "message with <code>chat_id</code> and <code>message_id</code>, or target "
    "inline mode with <code>inline=&lt;inline_message_id&gt;</code>.\n"
    "Usage: <code>/editreplymarkup &lt;chat_id&gt; &lt;message_id&gt; "
    "[clear|empty]</code>\n"
    "Usage: <code>/editreplymarkup inline=&lt;inline_message_id&gt; "
    "[clear|empty]</code>\n"
    "Omit the final argument or pass <code>clear</code> to remove the current "
    "inline keyboard. Pass <code>empty</code> to send an empty inline keyboard."
)

EDIT_MESSAGE_LIVE_LOCATION_USAGE = (
    "<b>editlivelocation usage</b>\n"
    "Edits an active live location message previously sent by this bot. This "
    "is an admin-only message-management command. Target a regular message "
    "with <code>chat_id</code> and <code>message_id</code>, or target inline "
    "mode with <code>inline=&lt;inline_message_id&gt;</code>.\n"
    "Usage: <code>/editlivelocation &lt;chat_id&gt; &lt;message_id&gt; "
    "&lt;latitude&gt; &lt;longitude&gt;</code>\n"
    "Usage: <code>/editlivelocation inline=&lt;inline_message_id&gt; "
    "&lt;latitude&gt; &lt;longitude&gt;</code>\n"
    "Coordinates are decimal degrees. Optional trailing flags: "
    "<code>accuracy=&lt;0-1500&gt;</code>, <code>heading=&lt;1-360&gt;</code>, "
    "<code>proximity=&lt;1-100000&gt;</code>."
)

STOP_MESSAGE_LIVE_LOCATION_USAGE = (
    "<b>stoplivelocation usage</b>\n"
    "Stops an active live location message previously sent by this bot. This "
    "is an admin-only message-management command. Target a regular message "
    "with <code>chat_id</code> and <code>message_id</code>, or target inline "
    "mode with <code>inline=&lt;inline_message_id&gt;</code>.\n"
    "Usage: <code>/stoplivelocation &lt;chat_id&gt; &lt;message_id&gt;</code>\n"
    "Usage: <code>/stoplivelocation inline=&lt;inline_message_id&gt;</code>"
)

POST_STORY_USAGE = (
    "<b>poststory usage</b>\n"
    "Posts a photo story on behalf of a connected Telegram business account. "
    "This is an admin-only publishing flow, separate from Claude chat replies. "
    "The bot must have the <code>can_manage_stories</code> business right for "
    "the live business connection id.\n"
    "Usage: <code>/poststory &lt;business_connection_id&gt; &lt;active_period&gt; "
    "&lt;photo_file_id&gt; [caption]</code>\n"
    "The active period must be one of 21600, 43200, 86400 or 172800 seconds. "
    f"The caption is optional and limited to {POST_STORY_CAPTION_LIMIT} "
    "characters. This command accepts a Telegram photo file_id; direct upload "
    "and URL story publishing are intentionally not exposed here."
)

REPOST_STORY_USAGE = (
    "<b>repoststory usage</b>\n"
    "Reposts a story on behalf of a connected Telegram business account from "
    "another business account managed by this bot. This is an admin-only "
    "publishing flow, separate from Claude chat replies. The bot must have the "
    "<code>can_manage_stories</code> business right for both business accounts, "
    "and the source story must have been posted or reposted by this bot.\n"
    "Usage: <code>/repoststory &lt;business_connection_id&gt; "
    "&lt;from_chat_id&gt; &lt;from_story_id&gt; &lt;active_period&gt;</code>\n"
    "The active period must be one of 21600, 43200, 86400 or 172800 seconds."
)

EDIT_STORY_USAGE = (
    "<b>editstory usage</b>\n"
    "Edits a photo story previously posted by this bot on behalf of a "
    "connected Telegram business account. This is an admin-only publishing "
    "flow, separate from Claude chat replies. The bot must have the "
    "<code>can_manage_stories</code> business right for the live business "
    "connection id.\n"
    "Usage: <code>/editstory &lt;business_connection_id&gt; &lt;story_id&gt; "
    "&lt;photo_file_id&gt; [caption]</code>\n"
    f"The caption is optional and limited to {POST_STORY_CAPTION_LIMIT} "
    "characters. This command accepts a Telegram photo file_id; direct upload "
    "and URL story editing are intentionally not exposed here."
)

DELETE_STORY_USAGE = (
    "<b>deletestory usage</b>\n"
    "Deletes a story previously posted by this bot on behalf of a connected "
    "Telegram business account. This is an admin-only publishing flow, "
    "separate from Claude chat replies. The bot must have the "
    "<code>can_manage_stories</code> business right for the live business "
    "connection id.\n"
    "Usage: <code>/deletestory &lt;business_connection_id&gt; "
    "&lt;story_id&gt;</code>"
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

GET_BUSINESS_ACCOUNT_STAR_BALANCE_USAGE = (
    "<b>businessstarbalance usage</b>\n"
    "Fetches Telegram <code>getBusinessAccountStarBalance</code> for a "
    "connected business account. This is an admin-only business-mode "
    "diagnostic because it exposes the account's Telegram Stars balance.\n"
    "Usage: <code>/businessstarbalance &lt;business_connection_id&gt;</code>\n"
    "The id must come from a live business connection update or another "
    "trusted operator source. Telegram requires the bot's current "
    "<code>can_view_gifts_and_stars</code> business right."
)

GET_MY_STAR_BALANCE_USAGE = (
    "<b>mystarbalance usage</b>\n"
    "Fetches Telegram <code>getMyStarBalance</code> for this bot. This is an "
    "admin-only diagnostic because it exposes the bot's Telegram Stars "
    "balance.\n"
    "Usage: <code>/mystarbalance</code>\n"
    "This command is unavailable unless <code>TELEGRAM_ADMIN_CHAT_IDS</code> "
    "contains the current chat."
)

GET_STAR_TRANSACTIONS_USAGE = (
    "<b>startransactions usage</b>\n"
    "Fetches Telegram <code>getStarTransactions</code> for this bot. This is "
    "an admin-only read-only billing audit because transaction ids can be used "
    "for reconciliation and refund workflows.\n"
    "Usage: <code>/startransactions [offset=0] [limit=1..100]</code>\n"
    "Telegram returns transactions in chronological order. This command is "
    "unavailable unless <code>TELEGRAM_ADMIN_CHAT_IDS</code> contains the "
    "current chat."
)

REFUND_STAR_PAYMENT_CONFIRM_KEYWORD = "confirm"

REFUND_STAR_PAYMENT_USAGE = (
    "<b>refundstars usage</b>\n"
    "Refunds one Telegram Stars payment via "
    "<code>refundStarPayment</code>. This is a destructive admin-only billing "
    "operation for charges previously found in payment updates or "
    "<code>/startransactions</code>.\n"
    "Usage: <code>/refundstars &lt;user_id&gt; "
    "&lt;telegram_payment_charge_id&gt; confirm</code>\n"
    "The user id and charge id must come from trusted billing records. The "
    "command is idempotent inside the running bot process and will not call "
    "Telegram twice for the same pair."
)

REFUND_STAR_PAYMENT_WARNING = (
    "<b>refundstars confirmation required</b>\n"
    "This will ask Telegram to refund a Stars payment to the specified user. "
    "Review the user id, charge id and local billing audit log before "
    "confirming.\n"
    "Run <code>/refundstars &lt;user_id&gt; "
    "&lt;telegram_payment_charge_id&gt; confirm</code> to proceed."
)

_REFUNDED_STAR_PAYMENT_KEYS: set[tuple[int, str]] = set()

EDIT_USER_STAR_SUBSCRIPTION_CONFIRM_KEYWORD = "confirm"

EDIT_USER_STAR_SUBSCRIPTION_USAGE = (
    "<b>edituserstarsubscription usage</b>\n"
    "Changes one Telegram Stars subscription via "
    "<code>editUserStarSubscription</code>. This is a destructive admin-only "
    "billing operation for subscriptions previously found in trusted billing "
    "records or payment updates.\n"
    "Usage: <code>/edituserstarsubscription &lt;user_id&gt; "
    "&lt;telegram_payment_charge_id&gt; active|canceled confirm</code>\n"
    "Use <code>canceled</code> to cancel future renewal, or "
    "<code>active</code> to reactivate it. The command is idempotent inside "
    "the running bot process and will not call Telegram twice for the same "
    "user, charge id and target state."
)

EDIT_USER_STAR_SUBSCRIPTION_WARNING = (
    "<b>edituserstarsubscription confirmation required</b>\n"
    "This will ask Telegram to change the renewal state of a Stars "
    "subscription for the specified user. Review the user id, charge id and "
    "local billing audit log before confirming.\n"
    "Run <code>/edituserstarsubscription &lt;user_id&gt; "
    "&lt;telegram_payment_charge_id&gt; active|canceled confirm</code> to proceed."
)

_EDITED_USER_STAR_SUBSCRIPTION_KEYS: set[tuple[int, str, bool]] = set()

GET_BUSINESS_ACCOUNT_GIFTS_USAGE = (
    "<b>businessgifts usage</b>\n"
    "Fetches Telegram <code>getBusinessAccountGifts</code> for a connected "
    "business account. This is an admin-only business-mode diagnostic because "
    "it exposes the account's owned gifts and pagination cursor.\n"
    "Usage: <code>/businessgifts &lt;business_connection_id&gt; "
    "[exclude_unsaved=true|false] [exclude_saved=true|false] "
    "[exclude_unlimited=true|false] [exclude_limited=true|false] "
    "[exclude_unique=true|false] [sort_by_price=true|false] "
    "[offset=&lt;offset&gt;] [limit=1..100]</code>\n"
    "The id must come from a live business connection update or another "
    "trusted operator source. Telegram requires connection ownership and the "
    "current business right to view gifts and Stars."
)

GET_USER_GIFTS_USAGE = (
    "<b>usergifts usage</b>\n"
    "Fetches Telegram <code>getUserGifts</code> for a user. This is an "
    "admin-only diagnostic because it exposes the user's owned gifts and "
    "pagination cursor.\n"
    "Usage: <code>/usergifts &lt;user_id&gt; "
    "[exclude_unsaved=true|false] [exclude_saved=true|false] "
    "[exclude_unlimited=true|false] [exclude_limited=true|false] "
    "[exclude_unique=true|false] [sort_by_price=true|false] "
    "[offset=&lt;offset&gt;] [limit=1..100]</code>\n"
    "The user id must identify a Telegram user whose gifts can be viewed by "
    "this bot account."
)

GET_CHAT_GIFTS_USAGE = (
    "<b>chatgifts usage</b>\n"
    "Fetches Telegram <code>getChatGifts</code> for a channel chat. This is "
    "an admin-only diagnostic because it exposes the channel's owned gifts "
    "and pagination cursor.\n"
    "Usage: <code>/chatgifts &lt;chat_id|@channelusername&gt; "
    "[exclude_unsaved=true|false] [exclude_saved=true|false] "
    "[exclude_unlimited=true|false] "
    "[exclude_limited_upgradable=true|false] "
    "[exclude_limited_non_upgradable=true|false] "
    "[exclude_from_blockchain=true|false] [exclude_unique=true|false] "
    "[sort_by_price=true|false] [offset=&lt;offset&gt;] "
    "[limit=1..100]</code>\n"
    "Telegram supports this method for channel chats. Full visibility can "
    "require the bot's <code>can_post_messages</code> administrator right."
)

TRANSFER_BUSINESS_ACCOUNT_STARS_CONFIRM_KEYWORD = "confirm"

TRANSFER_BUSINESS_ACCOUNT_STARS_USAGE = (
    "<b>transferbusinessstars usage</b>\n"
    "Transfers Telegram Stars from a connected business account to this bot's "
    "balance via <code>transferBusinessAccountStars</code>. This is a "
    "destructive admin-only business-mode operation because it moves Stars out "
    "of the supplied business connection.\n"
    "Usage: <code>/transferbusinessstars &lt;business_connection_id&gt; "
    "&lt;star_count&gt; confirm</code>\n"
    "The business connection id must come from a live business connection "
    "update or another trusted operator source; star_count must be a positive "
    "integer. Telegram requires the bot's current "
    "<code>can_transfer_stars</code> business right."
)

TRANSFER_BUSINESS_ACCOUNT_STARS_WARNING = (
    "<b>transferbusinessstars confirmation required</b>\n"
    "This will move Telegram Stars from the connected business account to this "
    "bot's balance and cannot be rolled back by this bot. Review connection "
    "ownership and the amount before confirming.\n"
    "Run <code>/transferbusinessstars &lt;business_connection_id&gt; "
    "&lt;star_count&gt; confirm</code> to proceed."
)

CONVERT_GIFT_TO_STARS_CONFIRM_KEYWORD = "confirm"

CONVERT_GIFT_TO_STARS_USAGE = (
    "<b>convertgiftstars usage</b>\n"
    "Converts one regular owned gift from a connected business account to "
    "Telegram Stars via <code>convertGiftToStars</code>. This is a destructive "
    "admin-only business-mode operation because the original gift is consumed.\n"
    "Usage: <code>/convertgiftstars &lt;business_connection_id&gt; "
    "&lt;owned_gift_id&gt; confirm</code>\n"
    "The business connection id and owned gift id must come from "
    "<code>/businessgifts</code> or another trusted operator source. Telegram "
    "requires connection ownership and the current business right to convert "
    "gifts to Stars."
)

CONVERT_GIFT_TO_STARS_WARNING = (
    "<b>convertgiftstars confirmation required</b>\n"
    "This will convert the selected owned gift into Telegram Stars and cannot "
    "be rolled back by this bot. Review connection ownership and the owned "
    "gift id before confirming.\n"
    "Run <code>/convertgiftstars &lt;business_connection_id&gt; "
    "&lt;owned_gift_id&gt; confirm</code> to proceed."
)

UPGRADE_GIFT_CONFIRM_KEYWORD = "confirm"

UPGRADE_GIFT_USAGE = (
    "<b>upgradegift usage</b>\n"
    "Upgrades one owned gift from a connected business account via "
    "<code>upgradeGift</code>. This is a destructive admin-only business-mode "
    "operation because it spends Telegram Stars from the business account "
    "balance and changes the selected gift.\n"
    "Usage: <code>/upgradegift &lt;business_connection_id&gt; "
    "&lt;owned_gift_id&gt; [keep_original_details=true|false] confirm</code>\n"
    "The business connection id and owned gift id must come from "
    "<code>/businessgifts</code> or another trusted operator source. Telegram "
    "requires connection ownership, enough Stars and the current business "
    "right to transfer and upgrade gifts."
)

UPGRADE_GIFT_WARNING = (
    "<b>upgradegift confirmation required</b>\n"
    "This will spend Telegram Stars from the connected business account to "
    "upgrade the selected owned gift and cannot be rolled back by this bot. "
    "Review connection ownership, the gift id and Star balance before "
    "confirming.\n"
    "Run <code>/upgradegift &lt;business_connection_id&gt; "
    "&lt;owned_gift_id&gt; [keep_original_details=true|false] confirm</code> "
    "to proceed."
)

TRANSFER_GIFT_CONFIRM_KEYWORD = "confirm"

TRANSFER_GIFT_USAGE = (
    "<b>transfergift usage</b>\n"
    "Transfers one unique owned gift from a connected business account to a "
    "user or channel chat via <code>transferGift</code>. This is a destructive "
    "admin-only business-mode operation because gift ownership changes and "
    "Telegram Stars can be spent for the transfer fee.\n"
    "Usage: <code>/transfergift &lt;business_connection_id&gt; "
    "&lt;owned_gift_id&gt; &lt;new_owner_chat_id&gt; "
    "[star_count=&lt;stars&gt;] confirm</code>\n"
    "The business connection id and owned gift id must come from "
    "<code>/businessgifts</code> or another trusted operator source. Telegram "
    "requires connection ownership and the current business right to transfer "
    "and upgrade gifts; if a transfer fee is required, the business account "
    "must also have enough Stars and the bot must be allowed to use them."
)

TRANSFER_GIFT_WARNING = (
    "<b>transfergift confirmation required</b>\n"
    "This will transfer the selected unique gift to another chat and cannot be "
    "rolled back by this bot. Review connection ownership, the gift id, target "
    "chat and optional Star fee before confirming.\n"
    "Run <code>/transfergift &lt;business_connection_id&gt; "
    "&lt;owned_gift_id&gt; &lt;new_owner_chat_id&gt; "
    "[star_count=&lt;stars&gt;] confirm</code> to proceed."
)

READ_BUSINESS_MESSAGE_USAGE = (
    "<b>readbusinessmessage usage</b>\n"
    "Marks one message from a connected Telegram business account as read via "
    "<code>readBusinessMessage</code>. This is an admin-only business-mode "
    "operation because Telegram accepts only messages that belong to the "
    "supplied business connection.\n"
    "Usage: <code>/readbusinessmessage &lt;business_connection_id&gt; "
    "&lt;message_id&gt;</code>\n"
    "The business connection id must come from a live business connection "
    "update or another trusted operator source; the message id must be a "
    "positive integer."
)

SET_BUSINESS_ACCOUNT_NAME_USAGE = (
    "<b>setbusinessaccountname usage</b>\n"
    "Sets the public first and optional last name of a connected Telegram "
    "business account via <code>setBusinessAccountName</code>. This is an "
    "admin-only business-mode operation because it changes account profile "
    "metadata for the supplied business connection.\n"
    "Usage: <code>/setbusinessaccountname &lt;business_connection_id&gt; "
    "&lt;first_name&gt; [last_name]</code>\n"
    "The business connection id must come from a live business connection "
    "update or another trusted operator source; first_name and last_name are "
    f"single tokens up to {MAX_BUSINESS_ACCOUNT_NAME_LENGTH} characters each."
)

SET_BUSINESS_ACCOUNT_USERNAME_USAGE = (
    "<b>setbusinessaccountusername usage</b>\n"
    "Sets the public username of a connected Telegram business account via "
    "<code>setBusinessAccountUsername</code>. This is an admin-only "
    "business-mode operation because it changes account profile metadata for "
    "the supplied business connection.\n"
    "Usage: <code>/setbusinessaccountusername &lt;business_connection_id&gt; "
    "&lt;username&gt;</code>\n"
    "The business connection id must come from a live business connection "
    "update or another trusted operator source; username may be passed with "
    "or without @ and must be a single token between "
    f"{MIN_BUSINESS_ACCOUNT_USERNAME_LENGTH} and "
    f"{MAX_BUSINESS_ACCOUNT_USERNAME_LENGTH} characters."
)

SET_BUSINESS_ACCOUNT_BIO_CLEAR_KEYWORD = "clear"

SET_BUSINESS_ACCOUNT_BIO_USAGE = (
    "<b>setbusinessaccountbio usage</b>\n"
    "Sets or clears the public bio of a connected Telegram business account "
    "via <code>setBusinessAccountBio</code>. This is an admin-only "
    "business-mode operation because it changes account profile metadata for "
    "the supplied business connection.\n"
    "Usage: <code>/setbusinessaccountbio &lt;business_connection_id&gt; "
    "&lt;bio|clear&gt;</code>\n"
    "The business connection id must come from a live business connection "
    "update or another trusted operator source; bio may contain spaces and "
    f"must be up to {MAX_BUSINESS_ACCOUNT_BIO_LENGTH} characters. Use "
    f"<code>{SET_BUSINESS_ACCOUNT_BIO_CLEAR_KEYWORD}</code> to clear it."
)

SET_BUSINESS_ACCOUNT_PROFILE_PHOTO_USAGE = (
    "<b>setbusinessaccountprofilephoto usage</b>\n"
    "Sets a static JPG profile photo of a connected Telegram business account "
    "via <code>setBusinessAccountProfilePhoto</code>. Telegram requires a "
    "fresh local upload, so pass a file path available to the running bot "
    "process. This is an admin-only business-mode operation because it changes "
    "account profile metadata for the supplied business connection.\n"
    "Usage: <code>/setbusinessaccountprofilephoto &lt;business_connection_id&gt; "
    "&lt;photo_path&gt; [public=true|false]</code>\n"
    "The business connection id must come from a live business connection "
    "update or another trusted operator source. Use "
    "<code>public=true</code> to set the public fallback photo visible when "
    "the main photo is hidden by privacy settings."
)

REMOVE_BUSINESS_ACCOUNT_PROFILE_PHOTO_CONFIRM_KEYWORD = "confirm"

REMOVE_BUSINESS_ACCOUNT_PROFILE_PHOTO_USAGE = (
    "<b>removebusinessaccountprofilephoto usage</b>\n"
    "Removes a profile photo of a connected Telegram business account via "
    "<code>removeBusinessAccountProfilePhoto</code>. This is a destructive "
    "admin-only business-mode operation because it changes account profile "
    "metadata for the supplied business connection.\n"
    "Usage: <code>/removebusinessaccountprofilephoto "
    "&lt;business_connection_id&gt; [public=true|false] confirm</code>\n"
    "The business connection id must come from a live business connection "
    "update or another trusted operator source. Use <code>public=true</code> "
    "to remove the public fallback photo instead of the main profile photo."
)

SET_BUSINESS_ACCOUNT_GIFT_SETTINGS_USAGE = (
    "<b>setbusinessaccountgiftsettings usage</b>\n"
    "Changes incoming gift settings of a connected Telegram business account "
    "via <code>setBusinessAccountGiftSettings</code>. This is an admin-only "
    "business-mode operation because it changes gift privacy settings for the "
    "supplied business connection.\n"
    "Usage: <code>/setbusinessaccountgiftsettings &lt;business_connection_id&gt; "
    "show_gift_button=true|false unlimited_gifts=true|false "
    "limited_gifts=true|false unique_gifts=true|false "
    "premium_subscription=true|false gifts_from_channels=true|false</code>\n"
    "The business connection id must come from a live business connection "
    "update or another trusted operator source."
)

DELETE_BUSINESS_MESSAGES_CONFIRM_KEYWORD = "confirm"

DELETE_BUSINESS_MESSAGES_USAGE = (
    "<b>deletebusinessmessages usage</b>\n"
    "Deletes 1-100 messages from a connected Telegram business account via "
    "<code>deleteBusinessMessages</code>. This is a destructive admin-only "
    "business-mode operation because Telegram accepts only messages that "
    "belong to the supplied business connection.\n"
    "Usage: <code>/deletebusinessmessages &lt;business_connection_id&gt; "
    "&lt;message_id&gt; [message_id ...] confirm</code>\n"
    "Message ids may be separated by spaces or commas. The business connection "
    "id must come from a live business connection update or another trusted "
    "operator source."
)

DELETE_BUSINESS_MESSAGES_WARNING = (
    "<b>deletebusinessmessages confirmation required</b>\n"
    "This will delete Telegram business-account messages and cannot be rolled "
    "back by this bot. Review the business connection ownership and message "
    "ids before confirming.\n"
    "Run <code>/deletebusinessmessages &lt;business_connection_id&gt; "
    "&lt;message_id&gt; [message_id ...] confirm</code> to proceed."
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

GET_AVAILABLE_GIFTS_CONFIRM_KEYWORD = "confirm"

GET_AVAILABLE_GIFTS_USAGE = (
    "<b>availablegifts usage</b>\n"
    "Fetches Telegram <code>getAvailableGifts</code> for the current regular "
    "gift catalog. The call is read-only and takes no Bot API parameters, but "
    "it is kept admin-only because the catalog is used in billing/rewards "
    "flows before Telegram Stars can be spent by separate gift actions.\n"
    "Usage: <code>/availablegifts confirm</code>\n"
    "This command is disabled unless <code>TELEGRAM_ADMIN_CHAT_IDS</code> "
    "contains the current chat. No chat administrator rights or special update "
    "types are required by Telegram."
)

GET_AVAILABLE_GIFTS_WARNING = (
    "<b>availablegifts confirmation required</b>\n"
    "This fetches the current Telegram gift catalog for an admin billing/"
    "rewards review. It does not spend Stars or send gifts, and any future "
    "spending or verification action must stay in a separate confirmed command "
    "with its own audit log.\n"
    "Run <code>/availablegifts confirm</code> to proceed."
)

SEND_GIFT_CONFIRM_KEYWORD = "confirm"
SEND_GIFT_TEXT_LIMIT = 128

SEND_GIFT_USAGE = (
    "<b>sendgift usage</b>\n"
    "Sends Telegram <code>sendGift</code> to a user or channel chat. The gift "
    "id must come from <code>/availablegifts confirm</code> or another trusted "
    "operator-controlled catalog review. This spends Telegram Stars from the "
    "bot balance, so the command is admin-only and requires an explicit "
    "confirmation keyword.\n"
    "Usage: <code>/sendgift &lt;user|chat&gt; &lt;receiver_id&gt; "
    "&lt;gift_id&gt; confirm [text]</code>\n"
    "Telegram requires exactly one receiver: <code>user_id</code> or "
    "<code>chat_id</code>. No special update type is required; channel gifts "
    "depend on Telegram-side bot permissions and Stars balance."
)

SEND_GIFT_WARNING = (
    "<b>sendgift confirmation required</b>\n"
    "This will send a Telegram gift and spend Stars from the bot balance. "
    "Review the gift id, receiver id, product rules and rollback plan before "
    "confirming. Gift delivery itself cannot be rolled back by this bot.\n"
    "Run <code>/sendgift &lt;user|chat&gt; &lt;receiver_id&gt; &lt;gift_id&gt; "
    "confirm [text]</code> to proceed."
)

GIFT_PREMIUM_CONFIRM_KEYWORD = "confirm"
GIFT_PREMIUM_TEXT_LIMIT = 128

GIFT_PREMIUM_USAGE = (
    "<b>giftpremium usage</b>\n"
    "Calls Telegram <code>giftPremiumSubscription</code> for a user. This "
    "spends Telegram Stars from the bot balance, so the command is admin-only, "
    "requires product-rule review and requires an explicit confirmation "
    "keyword in the same command.\n"
    "Usage: <code>/giftpremium &lt;user_id&gt; &lt;month_count&gt; "
    "&lt;star_count&gt; confirm [text]</code>\n"
    f"<code>month_count</code> must be {MIN_PREMIUM_MONTHS}-"
    f"{MAX_PREMIUM_MONTHS}. <code>star_count</code> must match Telegram's "
    "current Premium gift price reviewed by the operator. No special update "
    "type is required."
)

GIFT_PREMIUM_WARNING = (
    "<b>giftpremium confirmation required</b>\n"
    "This will gift Telegram Premium to a user and withdraw the specified "
    "Stars amount from the bot balance. Review the user id, month count, "
    "current Telegram price, available balance, verification action and "
    "rollback plan before confirming.\n"
    "Run <code>/giftpremium &lt;user_id&gt; &lt;month_count&gt; "
    "&lt;star_count&gt; confirm [text]</code> to proceed."
)

VERIFY_USER_CONFIRM_KEYWORD = "confirm"

VERIFY_USER_USAGE = (
    "<b>verifyuser usage</b>\n"
    "Calls Telegram <code>verifyUser</code> for a user. This changes a "
    "visible Telegram verification state, so the command is admin-only, "
    "requires product-rule review and requires an explicit confirmation "
    "keyword in the same command.\n"
    "Usage: <code>/verifyuser &lt;user_id&gt; confirm [custom_description]</code>\n"
    f"The optional <code>custom_description</code> is capped at "
    f"{VERIFY_USER_DESCRIPTION_LIMIT} characters. Telegram requires the bot to "
    "be able to verify users and validates the target user."
)

VERIFY_USER_WARNING = (
    "<b>verifyuser confirmation required</b>\n"
    "This will verify a Telegram user with the bot's verification authority. "
    "Review the user id, product rules, audit trail and rollback plan before "
    "confirming. Run a separate remove verification action if a mistake must "
    "be undone later.\n"
    "Run <code>/verifyuser &lt;user_id&gt; confirm [custom_description]</code> "
    "to proceed."
)

REMOVE_USER_VERIFICATION_CONFIRM_KEYWORD = "confirm"

REMOVE_USER_VERIFICATION_USAGE = (
    "<b>removeuserverification usage</b>\n"
    "Calls Telegram <code>removeUserVerification</code> for a user. This "
    "removes a visible Telegram verification state, so the command is "
    "admin-only, requires product-rule review and requires an explicit "
    "confirmation keyword in the same command.\n"
    "Usage: <code>/removeuserverification &lt;user_id&gt; confirm</code>\n"
    "Telegram requires the bot to be able to remove user verification and "
    "validates the target user."
)

REMOVE_USER_VERIFICATION_WARNING = (
    "<b>removeuserverification confirmation required</b>\n"
    "This will remove a Telegram user's verification with the bot's "
    "verification authority. Review the user id, product rules, audit trail "
    "and rollback plan before confirming. Re-applying verification later is a "
    "separate confirmed <code>/verifyuser</code> action.\n"
    "Run <code>/removeuserverification &lt;user_id&gt; confirm</code> to proceed."
)

REMOVE_CHAT_VERIFICATION_CONFIRM_KEYWORD = "confirm"

REMOVE_CHAT_VERIFICATION_USAGE = (
    "<b>removechatverification usage</b>\n"
    "Calls Telegram <code>removeChatVerification</code> for a chat. This "
    "removes a visible Telegram verification state, so the command is "
    "admin-only, requires product-rule review and requires an explicit "
    "confirmation keyword in the same command.\n"
    "Usage: <code>/removechatverification &lt;chat_id|@username&gt; confirm</code>\n"
    "Telegram requires the bot to be able to remove chat verification and "
    "validates the target chat."
)

REMOVE_CHAT_VERIFICATION_WARNING = (
    "<b>removechatverification confirmation required</b>\n"
    "This will remove a Telegram chat's verification with the bot's "
    "verification authority. Review the chat identity, product rules, audit "
    "trail and rollback plan before confirming. Re-applying verification later "
    "is a separate confirmed <code>/verifychat</code> action.\n"
    "Run <code>/removechatverification &lt;chat_id|@username&gt; confirm</code> "
    "to proceed."
)

VERIFY_CHAT_CONFIRM_KEYWORD = "confirm"

VERIFY_CHAT_USAGE = (
    "<b>verifychat usage</b>\n"
    "Calls Telegram <code>verifyChat</code> for a chat. This changes a "
    "visible Telegram verification state, so the command is admin-only, "
    "requires product-rule review and requires an explicit confirmation "
    "keyword in the same command.\n"
    "Usage: <code>/verifychat &lt;chat_id|@username&gt; confirm "
    "[custom_description]</code>\n"
    f"The optional <code>custom_description</code> is capped at "
    f"{VERIFY_CHAT_DESCRIPTION_LIMIT} characters. Telegram requires the bot to "
    "be able to verify chats and validates the target chat."
)

VERIFY_CHAT_WARNING = (
    "<b>verifychat confirmation required</b>\n"
    "This will verify a Telegram chat with the bot's verification authority. "
    "Review the chat identity, product rules, audit trail and rollback plan "
    "before confirming. Run a separate remove verification action if a mistake "
    "must be undone later.\n"
    "Run <code>/verifychat &lt;chat_id|@username&gt; confirm "
    "[custom_description]</code> to proceed."
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

DELETE_MESSAGE_REACTION_USAGE = (
    "<b>deletereaction usage</b>\n"
    "Deletes one user's reaction from a message via the Telegram "
    "<code>deleteMessageReaction</code> method. The bot must be able to access "
    "the target chat and message, and Telegram may reject the request when the "
    "reaction is already absent or the bot does not have enough rights.\n"
    "Usage: <code>/deletereaction &lt;chat_id&gt; &lt;message_id&gt; "
    "&lt;user_id&gt;</code>"
)

DELETE_ALL_MESSAGE_REACTIONS_USAGE = (
    "<b>deleteallreactions usage</b>\n"
    "Deletes all reactions from a message via the Telegram "
    "<code>deleteAllMessageReactions</code> method. The bot must be able to "
    "access the target chat and message, and Telegram may reject the request "
    "when the bot does not have enough rights.\n"
    "Usage: <code>/deleteallreactions &lt;chat_id&gt; &lt;message_id&gt;</code>"
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

DELETE_MESSAGE_CONFIRM_KEYWORD = "confirm"

DELETE_MESSAGE_USAGE = (
    "<b>deletemessage usage</b>\n"
    "Deletes one message from the specified chat via "
    "<code>deleteMessage</code>. This is a destructive moderation operation: "
    "the bot must be allowed to delete the target message, and Telegram may "
    "reject old messages, recent private-chat dice messages, or messages "
    "outside the bot's rights. This command is deny-by-default and only works "
    "from <code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/deletemessage &lt;chat_id&gt; &lt;message_id&gt; "
    "confirm</code>\n"
    "Rollback is not available through Telegram Bot API; restore the content "
    "manually if needed."
)

DELETE_MESSAGE_WARNING = (
    "<b>deletemessage confirmation required</b>\n"
    "This will delete one Telegram message and cannot be rolled back by this "
    "bot. Review the target chat id and message id before confirming.\n"
    "Run <code>/deletemessage &lt;chat_id&gt; &lt;message_id&gt; confirm</code> "
    "to proceed."
)

DELETE_MESSAGES_CONFIRM_KEYWORD = "confirm"

DELETE_MESSAGES_USAGE = (
    "<b>deletemessages usage</b>\n"
    "Deletes messages from the specified chat via <code>deleteMessages</code>. "
    "Telegram accepts up to 100 ids per Bot API request; this command chunks "
    "larger cleanups and reports partial chunk errors. This is a destructive "
    "moderation operation: the bot must be allowed to delete the target "
    "messages, and Telegram may reject old messages, recent private-chat dice "
    "messages, or messages outside the bot's rights. This command is "
    "deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/deletemessages &lt;chat_id&gt; &lt;message_id&gt; "
    "[message_id ...] confirm</code>\n"
    "Message ids may be separated by spaces or commas. Rollback is not "
    "available through Telegram Bot API; restore the content manually if "
    "needed."
)

DELETE_MESSAGES_WARNING = (
    "<b>deletemessages confirmation required</b>\n"
    "This will delete Telegram messages and cannot be rolled back by this bot. "
    "Review the target chat id and message ids before confirming.\n"
    "Run <code>/deletemessages &lt;chat_id&gt; &lt;message_id&gt; "
    "[message_id ...] confirm</code> to proceed."
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

GET_CHAT_MENU_BUTTON_USAGE = (
    "<b>getchatmenubutton usage</b>\n"
    "Fetches the menu button for a specific chat or the default menu button via "
    "<code>getChatMenuButton</code>. Use this read-only check to verify actual "
    "Telegram client state after <code>/setchatmenubutton</code>, startup sync "
    "or BotFather changes. The method does not require chat administrator "
    "rights or specific update subscriptions, but this command is "
    "deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/getchatmenubutton [chat_id=&lt;id&gt;]</code>\n"
    "Examples: <code>/getchatmenubutton</code>, "
    "<code>/getchatmenubutton chat_id=-100123</code>"
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

SET_MY_DEFAULT_ADMINISTRATOR_RIGHTS_USAGE = (
    "<b>setmydefaultrights usage</b>\n"
    "Sets the default administrator rights requested when this bot is added as "
    "an administrator via <code>setMyDefaultAdministratorRights</code>. Use "
    "configuration <code>TELEGRAM_BOT_DEFAULT_ADMINISTRATOR_RIGHTS</code> and "
    "optional <code>TELEGRAM_BOT_DEFAULT_ADMINISTRATOR_RIGHTS_FOR_CHANNELS</code> "
    "for startup sync. This command changes the bot's public add-to-chat "
    "defaults, is deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/setmydefaultrights &lt;moderator|manager|channel|clear&gt; "
    "[for_channels=true|false]</code>\n"
    "Use <code>clear</code> to reset Telegram defaults."
)

GET_MY_DEFAULT_ADMINISTRATOR_RIGHTS_USAGE = (
    "<b>getmydefaultrights usage</b>\n"
    "Fetches the default administrator rights requested when this bot is added "
    "as an administrator via <code>getMyDefaultAdministratorRights</code>. Use "
    "this after startup sync, <code>/setmydefaultrights</code> or BotFather "
    "changes to verify the actual Telegram state. The method is read-only and "
    "does not require chat administrator rights or update subscriptions, but "
    "this command is deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/getmydefaultrights [for_channels=true|false]</code>"
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

ANSWER_CHAT_JOIN_REQUEST_QUERY_USAGE = (
    "<b>answerjoinrequestquery usage</b>\n"
    "Processes a Bot API 10.1 chat join request query by approving it, "
    "declining it, or leaving it queued for another administrator. The query id "
    "comes from <code>ChatJoinRequest.query_id</code> and must be handled "
    "quickly after the update arrives.\n"
    "Usage: <code>/answerjoinrequestquery &lt;query_id&gt; "
    "&lt;approve|decline|queue&gt;</code>"
)

SEND_CHAT_JOIN_REQUEST_WEB_APP_USAGE = (
    "<b>joinrequestwebapp usage</b>\n"
    "Processes a Bot API 10.1 chat join request query by opening a Mini App "
    "for the user before a final decision is made.\n"
    "Usage: <code>/joinrequestwebapp &lt;query_id&gt; "
    "&lt;https://mini-app.example/path&gt;</code>"
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

GET_STICKER_SET_USAGE = (
    "<b>getstickerset usage</b>\n"
    "Fetches sticker set metadata and sticker file ids through "
    "<code>getStickerSet</code>. This is an admin triage helper for "
    "sticker/custom emoji lifecycle work and does not change Telegram state. "
    "Pass the sticker set name, not a title, URL or sticker file id. This "
    "command is deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/getstickerset &lt;sticker_set_name&gt;</code>"
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

CUSTOM_EMOJI_STICKERS_USAGE = (
    "<b>customemojistickers usage</b>\n"
    "Fetches full sticker metadata for custom emoji ids through "
    "<code>getCustomEmojiStickers</code>. This read-only admin triage helper "
    "accepts 1-200 ids, needs no chat permissions or special update "
    "subscription, and does not change Telegram state. This command is "
    "deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/customemojistickers &lt;custom_emoji_id&gt; "
    "[custom_emoji_id...]</code>"
)

UPLOAD_STICKER_FILE_USAGE = (
    "<b>uploadstickerfile usage</b>\n"
    "Uploads a local sticker file through <code>uploadStickerFile</code> and "
    "returns a reusable Telegram file id for sticker set lifecycle operations. "
    "The file must be accessible on the bot host and match the selected "
    "<code>sticker_format</code>: <code>static</code>, <code>animated</code> "
    "or <code>video</code>. This command is deny-by-default and only works "
    "from <code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/uploadstickerfile &lt;user_id&gt; "
    "&lt;sticker_format&gt; &lt;sticker_path&gt;</code>"
)

CREATE_NEW_STICKER_SET_USAGE = (
    "<b>createnewstickerset usage</b>\n"
    "Creates a sticker set through <code>createNewStickerSet</code> with one "
    "pre-uploaded sticker file id and an emoji list. Use "
    "<code>/uploadstickerfile</code> first when you need to upload a local "
    "asset. The target user must be the sticker set owner, and the sticker set "
    "name must be unique and end with <code>_by_&lt;bot_username&gt;</code>. "
    "Supported <code>sticker_type</code> values are <code>regular</code>, "
    "<code>mask</code> and <code>custom_emoji</code>; supported "
    "<code>sticker_format</code> values are <code>static</code>, "
    "<code>animated</code> and <code>video</code>. This command is "
    "deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/createnewstickerset &lt;user_id&gt; &lt;name&gt; "
    "&lt;sticker_type&gt; &lt;sticker_format&gt; &lt;sticker_file_id&gt; "
    "&lt;emoji[,emoji...]&gt; &lt;title&gt;</code>"
)

ADD_STICKER_TO_SET_USAGE = (
    "<b>addstickertoset usage</b>\n"
    "Adds one pre-uploaded sticker file id to an existing sticker set through "
    "<code>addStickerToSet</code>. Use <code>/uploadstickerfile</code> first "
    "when you need to upload a local asset. The target user must be the "
    "sticker set owner. Supported <code>sticker_format</code> values are "
    "<code>static</code>, <code>animated</code> and <code>video</code>. This "
    "command is deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/addstickertoset &lt;user_id&gt; &lt;name&gt; "
    "&lt;sticker_format&gt; &lt;sticker_file_id&gt; "
    "&lt;emoji[,emoji...]&gt;</code>"
)

REPLACE_STICKER_IN_SET_USAGE = (
    "<b>replacestickerinset usage</b>\n"
    "Replaces one existing sticker in a sticker set through "
    "<code>replaceStickerInSet</code> using a new pre-uploaded sticker file id. "
    "Use <code>/getstickerset</code> first to inspect current file ids and "
    "<code>/uploadstickerfile</code> first when you need to upload a local "
    "asset. The target user must be the sticker set owner, and the bot can "
    "only replace stickers in sets created by the bot. Supported "
    "<code>sticker_format</code> values are <code>static</code>, "
    "<code>animated</code> and <code>video</code>. This command is "
    "deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/replacestickerinset &lt;user_id&gt; &lt;name&gt; "
    "&lt;old_sticker_file_id&gt; &lt;sticker_format&gt; "
    "&lt;new_sticker_file_id&gt; &lt;emoji[,emoji...]&gt;</code>"
)

SET_STICKER_POSITION_IN_SET_USAGE = (
    "<b>setstickerposition usage</b>\n"
    "Moves one sticker to a zero-based position inside its current sticker set "
    "through <code>setStickerPositionInSet</code>. Use "
    "<code>/getstickerset</code> first when you need to inspect current "
    "file ids and ordering. The bot can only move stickers in sets created by "
    "the bot. This command is deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/setstickerposition &lt;sticker_file_id&gt; "
    "&lt;position&gt;</code>"
)

SET_STICKER_EMOJI_LIST_USAGE = (
    "<b>setstickeremojis usage</b>\n"
    "Replaces the emoji list for one sticker in its current sticker set "
    "through <code>setStickerEmojiList</code>. Use "
    "<code>/getstickerset</code> first when you need to inspect current "
    "file ids and emoji metadata. The bot can only update stickers in sets "
    "created by the bot. This command is deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/setstickeremojis &lt;sticker_file_id&gt; "
    "&lt;emoji[,emoji...]&gt;</code>"
)

SET_STICKER_MASK_POSITION_USAGE = (
    "<b>setstickermaskposition usage</b>\n"
    "Changes or clears the mask position for one mask sticker through "
    "<code>setStickerMaskPosition</code>. Use <code>/getstickerset</code> "
    "first when you need to inspect current file ids and mask metadata. The "
    "bot can only update mask stickers in sets created by the bot. Pass "
    "<code>-</code> instead of mask coordinates to clear the current mask "
    "position. Supported <code>point</code> values are <code>forehead</code>, "
    "<code>eyes</code>, <code>mouth</code> and <code>chin</code>. This command "
    "is deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/setstickermaskposition &lt;sticker_file_id&gt; "
    "&lt;point&gt; &lt;x_shift&gt; &lt;y_shift&gt; &lt;scale&gt;</code>\n"
    "Clear: <code>/setstickermaskposition &lt;sticker_file_id&gt; -</code>"
)

SET_STICKER_KEYWORDS_USAGE = (
    "<b>setstickerkeywords usage</b>\n"
    "Replaces search keywords for one sticker in its current sticker set "
    "through <code>setStickerKeywords</code>. Use "
    "<code>/getstickerset</code> first when you need to inspect current "
    "file ids. The bot can only update stickers in sets created by the bot. "
    "Pass <code>-</code> to clear keywords. This command is deny-by-default "
    "and only works from <code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/setstickerkeywords &lt;sticker_file_id&gt; "
    "&lt;keyword[,keyword...]|-&gt;</code>"
)

SET_STICKER_SET_TITLE_USAGE = (
    "<b>setstickersettitle usage</b>\n"
    "Changes the title of a sticker set through "
    "<code>setStickerSetTitle</code>. Use <code>/getstickerset</code> first "
    "when you need to inspect the current name and title. The bot can only "
    "update sticker sets created by the bot. This command is deny-by-default "
    "and only works from <code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/setstickersettitle &lt;sticker_set_name&gt; "
    "&lt;title&gt;</code>"
)

SET_STICKER_SET_THUMBNAIL_USAGE = (
    "<b>setstickersetthumbnail usage</b>\n"
    "Sets or clears the thumbnail of a sticker set through "
    "<code>setStickerSetThumbnail</code>. Use <code>/getstickerset</code> "
    "first when you need to inspect the current name and thumbnail. The bot "
    "can only update sticker sets created by the bot. Pass <code>-</code> as "
    "thumbnail to clear the current thumbnail. This command is deny-by-default "
    "and only works from <code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/setstickersetthumbnail &lt;user_id&gt; "
    "&lt;sticker_set_name&gt; &lt;format&gt; &lt;thumbnail_file_id|-&gt;</code>"
)

SET_CUSTOM_EMOJI_STICKER_SET_THUMBNAIL_USAGE = (
    "<b>setcustomemojithumbnail usage</b>\n"
    "Sets or clears the thumbnail of a custom emoji sticker set through "
    "<code>setCustomEmojiStickerSetThumbnail</code>. Use "
    "<code>/getstickerset</code> first when you need to inspect the current "
    "name and custom emoji ids. The bot can only update custom emoji sticker "
    "sets created by the bot. Pass <code>-</code> as custom emoji id to clear "
    "the current thumbnail. This command is deny-by-default and only works "
    "from <code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/setcustomemojithumbnail &lt;sticker_set_name&gt; "
    "&lt;custom_emoji_id|-&gt;</code>"
)

DELETE_STICKER_FROM_SET_USAGE = (
    "<b>deletestickerfromset usage</b>\n"
    "Deletes one sticker from its current sticker set through "
    "<code>deleteStickerFromSet</code>. Use <code>/getstickerset</code> first "
    "when you need to inspect current file ids. The bot can only delete "
    "stickers from sets created by the bot. This command is deny-by-default "
    "and only works from <code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/deletestickerfromset &lt;sticker_file_id&gt;</code>"
)

DELETE_STICKER_SET_USAGE = (
    "<b>deletestickerset usage</b>\n"
    "Deletes a sticker set through <code>deleteStickerSet</code>. Use "
    "<code>/getstickerset</code> first when you need to inspect the target "
    "set name. Telegram only allows deleting sticker sets created by the bot. "
    "This command is deny-by-default and only works from "
    "<code>TELEGRAM_ADMIN_CHAT_IDS</code>.\n"
    "Usage: <code>/deletestickerset &lt;sticker_set_name&gt;</code>"
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
        "/sticker - Send a sticker or custom emoji into this chat (admin only)\n"
        "/voice - Send a voice message into this chat as a playable audio clip (admin only)\n"
        "/paidmedia - Send a paid photo into this chat priced in Telegram Stars (admin only)\n"
        "/sendinvoice - Send a Telegram Stars test invoice (admin only)\n"
        "/createinvoicelink - Create a Telegram Stars invoice link (admin only)\n"
        "/mystarbalance - Fetch this bot's Telegram Stars balance (admin only)\n"
        "/startransactions - Fetch this bot's Telegram Stars transaction history (admin only)\n"
        "/refundstars - Refund a Telegram Stars payment by charge id (admin only)\n"
        "/answerwebappquery - Answer a Web App query with an inline result (admin only)\n"
        "/savepreparedinline - Save a prepared inline message for a user (admin only)\n"
        "/setpassporterrors - Report Telegram Passport validation errors (admin only)\n"
        "/savepreparedkeyboard - Save a prepared keyboard button for a Mini App user (admin only)\n"
        "/location - Send a point on the map into this chat as a location (admin only)\n"
        "/venue - Send a venue (named place with title and address) into this chat (admin only)\n"
        "/poll - Send a native poll (question with answer options) into this chat (admin only)\n"
        "/approvesuggestedpost - Approve a direct messages suggested post (admin only)\n"
        "/declinesuggestedpost - Decline a direct messages suggested post (admin only)\n"
        "/contact - Send a phone contact (name and phone number) into this chat (admin only)\n"
        "/dice - Send an animated dice (random value) into this chat (admin only)\n"
        "/game - Send a Telegram game by BotFather short name into this chat (admin only)\n"
        "/setgamescore - Set a Telegram game score for a user (admin only)\n"
        "/gamehighscores - Fetch Telegram game high scores for a user (admin only)\n"
        "/chataction - Show a chat action (e.g. typing…) in this chat (admin only)\n"
        "/messagedraft - Stream an ephemeral message draft into this private chat (admin only)\n"
        "/richmessage - Send a Bot API 10.1 rich message into this chat (admin only)\n"
        "/richmessagedraft - Stream a Bot API 10.1 rich message draft (admin only)\n"
        "/editcaption - Edit or clear a media message caption (admin only)\n"
        "/editmedia - Replace media in a previously sent media message (admin only)\n"
        "/editlivelocation - Move an active live location message (admin only)\n"
        "/stoplivelocation - Stop an active live location message (admin only)\n"
        "/checklist - Send a checklist (titled list of tasks) into this chat via a business connection (admin only)\n"
        "/editchecklist - Edit a business checklist message (admin only)\n"
        "/poststory - Post a photo story via a business connection (admin only)\n"
        "/repoststory - Repost a story between managed business accounts (admin only)\n"
        "/deletestory - Delete a story via a business connection (admin only)\n"
        "/businessstarbalance - Fetch a connected business account Telegram Stars balance by business connection id (admin only)\n"
        "/businessgifts - Fetch connected business account gifts by business connection id (admin only)\n"
        "/transferbusinessstars - Transfer connected business account Stars to the bot balance (admin only)\n"
        "/convertgiftstars - Convert a connected business account owned gift to Telegram Stars (admin only)\n"
        "/upgradegift - Upgrade a connected business account owned gift with Telegram Stars (admin only)\n"
        "/transfergift - Transfer a connected business account unique gift to another chat (admin only)\n"
        "/readbusinessmessage - Mark a business message as read by business connection id and message id (admin only)\n"
        "/setbusinessaccountname - Set a connected business account name by business connection id (admin only)\n"
        "/setbusinessaccountusername - Set a connected business account username by business connection id (admin only)\n"
        "/setbusinessaccountbio - Set or clear a connected business account bio by business connection id (admin only)\n"
        "/setbusinessaccountprofilephoto - Set a connected business account profile photo by business connection id (admin only)\n"
        "/removebusinessaccountprofilephoto - Remove a connected business account profile photo by business connection id (admin only)\n"
        "/setbusinessaccountgiftsettings - Set connected business account gift settings by business connection id (admin only)\n"
        "/deletebusinessmessages - Delete business messages by business connection id and message ids (admin only)\n"
        "/deletemessage - Delete one message by chat id and message id (admin only)\n"
        "/managedbottoken - Fetch a managed bot token by user id (admin only)\n"
        "/managedbotaccess - Fetch managed bot access settings by user id (admin only)\n"
        "/setmanagedbotaccess - Update managed bot access settings by user id (admin only)\n"
        "/replacemanagedbottoken - Rotate a managed bot token by user id (admin only)\n"
        "/availablegifts - Fetch the current Telegram gift catalog (admin only)\n"
        "/usergifts - Fetch Telegram gifts owned by a user (admin only)\n"
        "/chatgifts - Fetch Telegram gifts owned by a channel chat (admin only)\n"
        "/sendgift - Send a Telegram gift with explicit confirmation (admin only)\n"
        "/giftpremium - Gift Telegram Premium with explicit Stars confirmation (admin only)\n"
        "/verifyuser - Verify a Telegram user with explicit confirmation (admin only)\n"
        "/removeuserverification - Remove user verification with explicit confirmation (admin only)\n"
        "/verifychat - Verify a Telegram chat with explicit confirmation (admin only)\n"
        "/removechatverification - Remove chat verification with explicit confirmation (admin only)\n"
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
        "/customemojistickers - Fetch custom emoji sticker metadata by id (admin only)\n"
        "/getstickerset - Fetch sticker set metadata by name (admin only)\n"
        "/uploadstickerfile - Upload a sticker file and return its file id (admin only)\n"
        "/createnewstickerset - Create a sticker set with one sticker file id (admin only)\n"
        "/addstickertoset - Add one sticker file id to a sticker set (admin only)\n"
        "/replacestickerinset - Replace one sticker file id in a sticker set (admin only)\n"
        "/setstickerposition - Move a sticker inside its sticker set (admin only)\n"
        "/setstickeremojis - Replace a sticker emoji list (admin only)\n"
        "/setstickermaskposition - Change or clear a mask sticker position (admin only)\n"
        "/setstickersettitle - Change a sticker set title (admin only)\n"
        "/setstickersetthumbnail - Set or clear a sticker set thumbnail (admin only)\n"
        "/setcustomemojithumbnail - Set or clear a custom emoji sticker set thumbnail (admin only)\n"
        "/deletestickerfromset - Delete a sticker from its sticker set (admin only)\n"
        "/deletestickerset - Delete a bot-created sticker set (admin only)\n"
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
        "/setmydefaultrights - Set default administrator rights requested by the bot (admin only)\n"
        "/getmydefaultrights - Fetch default administrator rights requested by the bot (admin only)\n"
        "/getmyshortdescription - Fetch the bot short description (admin only)\n"
        "/setmycommands - Set the bot command list shown in Telegram clients (admin only)\n"
        "/getmycommands - Fetch and diagnose the bot command list (admin only)\n"
        "/deletemycommands - Delete bot commands by scope/language (admin only)\n"
        "/setchatstickerset - Set a supergroup sticker set (admin only)\n"
        "/deletechatstickerset - Delete a supergroup sticker set (admin only)\n"
        "/promotechatmember - Promote or demote a user in a chat (admin only)\n"
        "/approvechatjoinrequest - Approve a pending chat join request (admin only)\n"
        "/declinechatjoinrequest - Decline a pending chat join request (admin only)\n"
        "/answerjoinrequestquery - Answer a guard-bot join request query (admin only)\n"
        "/joinrequestwebapp - Open a Mini App for a join request query (admin only)\n"
        "/exportchatinvitelink - Export a new primary chat invite link (admin only)\n"
        "/leavechat - Make the bot leave a chat (admin only)\n"
        "/editchatinvitelink - Edit a non-primary chat invite link (admin only)\n"
        "/revokechatinvitelink - Revoke a chat invite link (admin only)\n"
        "/editchatsubscriptioninvitelink - Edit a subscription invite link (admin only)\n"
        "/edituserstarsubscription - Edit a user Stars subscription (admin only)\n"
        "/setchatadministratortitle - Set a chat administrator custom title (admin only)\n"
        "/setchatmembertag - Set or clear a chat member tag (admin only)\n"
        "/react - Set or remove a reaction on a message in this chat (admin only)\n"
        "/deletereaction - Delete a user's reaction from a message (admin only)\n"
        "/deleteallreactions - Delete all reactions from a message (admin only)\n"
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
        escaped_current = escape(current)
        client = ClaudeProxyClient(
            settings.free_claude_base_url,
            settings.free_claude_auth_token,
            settings.free_claude_timeout_seconds,
        )
        try:
            models = await client.list_models()
            models_list = "\n".join(f"- {escape(m)}" for m in models)
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
                f"Current model: {escaped_current}\nAvailable models:\n{models_list}",
                **kwargs,
            )
        except Exception as e:
            await _answer_operation_failed(
                message,
                f"Current model: {escaped_current}\nCould not fetch model list",
                e,
            )
        finally:
            await client.close()
    else:
        new_model = args[1].strip()
        storage.set_setting(user_id, "model", new_model)
        await message.answer(f"Model set to: {escape(new_model)}")

@router.message(Command("settings"))
async def cmd_settings(message: Message):
    user_id = message.from_user.id
    current_model = storage.get_setting(user_id, "model", settings.free_claude_default_model)
    streaming = settings.free_claude_streaming_enabled
    guest_mode = settings.telegram_guest_mode_enabled
    rate_limit = settings.rate_limit_requests_per_minute
    settings_text = (
        f"<b>Your settings:</b>\n"
        f"Model: {escape(current_model)}\n"
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
    if not _is_admin_or_allowed_chat(message.chat.id, _message_user_id(message)):
        await message.answer("Webhook diagnostics are restricted.")
        return

    try:
        info = await fetch_webhook_info(message.bot)
    except TelegramAPIError as exc:
        await _answer_operation_failed(message, "Could not fetch webhook diagnostics", exc)
        return

    await message.answer(format_webhook_info(info), parse_mode="HTML")


@router.message(Command("deletewebhook"))
async def cmd_delete_webhook(message: Message):
    if not _is_admin_or_allowed_chat(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not delete webhook", exc)
        return

    pending_updates_status = "dropped" if drop_pending_updates else "kept"
    await message.answer(f"Webhook deleted. Pending updates were {pending_updates_status}.")


@router.message(Command("logout"))
async def cmd_log_out(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not log out from the cloud Bot API", exc)
        return

    await message.answer(
        "Logged out from the cloud Bot API server. The bot will not receive "
        "updates until it logs in again, and cloud login is blocked for 10 "
        "minutes."
    )

@router.message(Command("close"))
async def cmd_close(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not close the bot instance", exc)
        return

    await message.answer(
        "Closed the bot instance on the current Bot API server. Move the bot "
        "to its new Bot API server and start it again to resume processing "
        "updates."
    )

@router.message(Command("forward"))
async def cmd_forward(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not forward the message", exc)
        return

    protection = "protected" if protect_content else "shareable"
    await message.answer(
        f"Forwarded message {message_id} from chat {from_chat_id} "
        f"({protection} copy)."
    )

@router.message(Command("forwards"))
async def cmd_forwards(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not forward the messages", exc)
        return

    forwarded_count = len(result) if hasattr(result, "__len__") else len(message_ids)
    protection = "protected" if protect_content else "shareable"
    await message.answer(
        f"Forwarded {forwarded_count} of {len(message_ids)} messages from chat "
        f"{from_chat_id} ({protection} copy)."
    )

@router.message(Command("copy"))
async def cmd_copy(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not copy the message", exc)
        return

    protection = "protected" if protect_content else "shareable"
    await message.answer(
        f"Copied message {message_id} from chat {from_chat_id} "
        f"({protection} copy)."
    )

@router.message(Command("copies"))
async def cmd_copies(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not copy the messages", exc)
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
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not send the photo", exc)
        return

    await message.answer(
        "Sent photo with caption." if caption else "Sent photo."
    )

@router.message(Command("audio"))
async def cmd_audio(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not send the audio", exc)
        return

    await message.answer(
        "Sent audio with caption." if caption else "Sent audio."
    )

@router.message(Command("livephoto"))
async def cmd_live_photo(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not send the live photo", exc)
        return

    await message.answer(
        "Sent live photo with caption." if caption else "Sent live photo."
    )

@router.message(Command("document"))
async def cmd_document(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not send the document", exc)
        return

    await message.answer(
        "Sent document with caption." if caption else "Sent document."
    )

@router.message(Command("video"))
async def cmd_video(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not send the video", exc)
        return

    await message.answer(
        "Sent video with caption." if caption else "Sent video."
    )

@router.message(Command("videonote"))
async def cmd_video_note(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not send the video note", exc)
        return

    await message.answer("Sent video note.")

@router.message(Command("animation"))
async def cmd_animation(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not send the animation", exc)
        return

    await message.answer(
        "Sent animation with caption." if caption else "Sent animation."
    )


@router.message(Command("sticker"))
async def cmd_sticker(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_sticker_args(message.text or "")
    if parsed is None:
        await message.answer(STICKER_USAGE, parse_mode="HTML")
        return

    sticker, emoji = parsed

    try:
        await perform_send_sticker(
            message.bot,
            chat_id=message.chat.id,
            sticker=sticker,
            emoji=emoji,
        )
    except TelegramAPIError as exc:
        await _answer_operation_failed(message, "Could not send the sticker", exc)
        return

    await message.answer(
        "Sent sticker with emoji hint." if emoji else "Sent sticker."
    )


@router.message(Command("voice"))
async def cmd_voice(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not send the voice message", exc)
        return

    await message.answer(
        "Sent voice message with caption." if caption else "Sent voice message."
    )

@router.message(Command("paidmedia"))
async def cmd_paid_media(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not send the paid media", exc)
        return

    await message.answer(
        "Sent paid media with caption." if caption else "Sent paid media."
    )


@router.message(Command("sendinvoice"))
async def cmd_send_invoice(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_send_invoice_args(message.text or "")
    if parsed is None:
        await message.answer(SEND_INVOICE_USAGE, parse_mode="HTML")
        return

    star_count, payload, title, description = parsed
    validation_error = _validate_send_invoice_args(
        star_count=star_count,
        payload=payload,
        title=title,
        description=description,
    )
    if validation_error is not None:
        await message.answer(validation_error)
        return

    try:
        await perform_send_invoice(
            message.bot,
            chat_id=message.chat.id,
            title=title,
            description=description,
            payload=payload,
            provider_token="",
            currency="XTR",
            prices=[{"label": title, "amount": star_count}],
        )
    except SendInvoiceError as exc:
        await _answer_operation_failed(message, "Could not send the invoice", exc)
        return

    await message.answer("Sent Telegram Stars invoice.")


@router.message(Command("createinvoicelink"))
async def cmd_create_invoice_link(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_create_invoice_link_args(message.text or "")
    if parsed is None:
        await message.answer(CREATE_INVOICE_LINK_USAGE, parse_mode="HTML")
        return

    star_count, payload, title, description = parsed
    validation_error = _validate_create_invoice_link_args(
        star_count=star_count,
        payload=payload,
        title=title,
        description=description,
    )
    if validation_error is not None:
        await message.answer(validation_error)
        return

    try:
        invoice_link = await perform_create_invoice_link(
            message.bot,
            title=title,
            description=description,
            payload=payload,
            provider_token="",
            currency="XTR",
            prices=[{"label": title, "amount": star_count}],
        )
    except CreateInvoiceLinkError as exc:
        await _answer_operation_failed(message, "Could not create the invoice link", exc)
        return

    await message.answer(f"Created Telegram Stars invoice link:\n{invoice_link}")


@router.message(Command("answerwebappquery"))
async def cmd_answer_web_app_query(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_answer_web_app_query_args(message.text or "")
    if parsed is None:
        await message.answer(ANSWER_WEB_APP_QUERY_USAGE, parse_mode="HTML")
        return

    web_app_query_id, result = parsed
    try:
        sent_message = await perform_answer_web_app_query(
            message.bot,
            web_app_query_id=web_app_query_id,
            result=result,
        )
    except AnswerWebAppQueryError as exc:
        await _answer_operation_failed(message, "Could not answer the Web App query", exc)
        return

    inline_message_id = sent_message.get("inline_message_id")
    if inline_message_id:
        await message.answer(
            f"Answered Web App query: inline message {inline_message_id}."
        )
    else:
        await message.answer("Answered Web App query.")


@router.message(Command("savepreparedinline"))
async def cmd_save_prepared_inline_message(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_save_prepared_inline_message_args(message.text or "")
    if parsed is None:
        await message.answer(SAVE_PREPARED_INLINE_MESSAGE_USAGE, parse_mode="HTML")
        return

    user_id, result, options = parsed
    try:
        prepared_message = await perform_save_prepared_inline_message(
            message.bot,
            user_id=user_id,
            result=result,
            **options,
        )
    except SavePreparedInlineMessageError as exc:
        await _answer_operation_failed(message, "Could not save the prepared inline message", exc)
        return

    prepared_message_id = prepared_message.get("id")
    if prepared_message_id:
        await message.answer(
            f"Saved prepared inline message: {prepared_message_id}."
        )
    else:
        await message.answer("Saved prepared inline message.")


@router.message(Command("setpassporterrors"))
async def cmd_set_passport_data_errors(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_set_passport_data_errors_args(message.text or "")
    if parsed is None:
        await message.answer(SET_PASSPORT_DATA_ERRORS_USAGE, parse_mode="HTML")
        return

    user_id, errors = parsed
    try:
        await perform_set_passport_data_errors(
            message.bot,
            user_id=user_id,
            errors=errors,
        )
    except SetPassportDataErrorsError as exc:
        await _answer_operation_failed(message, "Could not set Passport data errors", exc)
        return

    await message.answer(
        f"Set {len(errors)} Passport data error(s) for user {user_id}."
    )


@router.message(Command("savepreparedkeyboard"))
async def cmd_save_prepared_keyboard_button(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_save_prepared_keyboard_button_args(message.text or "")
    if parsed is None:
        await message.answer(SAVE_PREPARED_KEYBOARD_BUTTON_USAGE, parse_mode="HTML")
        return

    user_id, prepared_message_id = parsed
    try:
        await perform_save_prepared_keyboard_button(
            message.bot,
            user_id=user_id,
            prepared_message_id=prepared_message_id,
        )
    except SavePreparedKeyboardButtonError as exc:
        await _answer_operation_failed(message, "Could not save the prepared keyboard button", exc)
        return

    await message.answer("Saved prepared keyboard button.")


@router.message(Command("location"))
async def cmd_location(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not send the location", exc)
        return

    await message.answer("Sent location.")

@router.message(Command("venue"))
async def cmd_venue(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not send the venue", exc)
        return

    await message.answer("Sent venue.")

@router.message(Command("poll"))
async def cmd_poll(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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

    option_texts = [
        option["text"] if isinstance(option, dict) else option for option in options
    ]
    too_long = next(
        (opt for opt in option_texts if len(opt) > POLL_OPTION_MAX_LENGTH),
        None,
    )
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
    except (TelegramAPIError, SendPollError) as exc:
        await _answer_operation_failed(message, "Could not send the poll", exc)
        return

    await message.answer(f"Sent poll with {len(options)} options.")

@router.message(Command("stoppoll"))
async def cmd_stop_poll(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_stop_poll_args(message.text or "")
    if parsed is None:
        await message.answer(STOP_POLL_USAGE, parse_mode="HTML")
        return

    chat_id, message_id = parsed
    try:
        poll = await perform_stop_poll(
            message.bot,
            chat_id=chat_id,
            message_id=message_id,
        )
    except StopPollValidationError as exc:
        await _answer_validation_failed(
            message,
            "Invalid stopPoll request. Check the command usage and try again.",
            exc,
        )
        return
    except TelegramAPIError as exc:
        await _answer_operation_failed(message, "Could not stop the poll", exc)
        return

    await message.answer(
        format_stop_poll_result(poll, chat_id=chat_id, message_id=message_id),
        parse_mode="HTML",
    )

@router.message(Command("approvesuggestedpost"))
async def cmd_approve_suggested_post(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_approve_suggested_post_args(message.text or "")
    if parsed is None:
        await message.answer(APPROVE_SUGGESTED_POST_USAGE, parse_mode="HTML")
        return

    chat_id, message_id, send_date = parsed
    try:
        await perform_approve_suggested_post(
            message.bot,
            chat_id=chat_id,
            message_id=message_id,
            send_date=send_date,
        )
    except ApproveSuggestedPostError as exc:
        await _answer_operation_failed(message, "Could not approve the suggested post", exc)
        return

    await message.answer(
        format_approve_suggested_post_result(
            chat_id=chat_id,
            message_id=message_id,
            send_date=send_date,
        ),
        parse_mode="HTML",
    )


@router.message(Command("declinesuggestedpost"))
async def cmd_decline_suggested_post(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_decline_suggested_post_args(message.text or "")
    if parsed is None:
        await message.answer(DECLINE_SUGGESTED_POST_USAGE, parse_mode="HTML")
        return

    chat_id, message_id, comment = parsed
    try:
        await perform_decline_suggested_post(
            message.bot,
            chat_id=chat_id,
            message_id=message_id,
            comment=comment,
        )
    except DeclineSuggestedPostError as exc:
        await _answer_operation_failed(message, "Could not decline the suggested post", exc)
        return

    await message.answer(
        format_decline_suggested_post_result(
            chat_id=chat_id,
            message_id=message_id,
            comment=comment,
        ),
        parse_mode="HTML",
    )


@router.message(Command("contact"))
async def cmd_contact(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not send the contact", exc)
        return

    await message.answer("Sent contact.")

@router.message(Command("dice"))
async def cmd_dice(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not send the dice", exc)
        return

    await message.answer("Sent dice.")


@router.message(Command("game"))
async def cmd_game(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_game_args(message.text or "")
    if parsed is None:
        await message.answer(GAME_USAGE, parse_mode="HTML")
        return

    (game_short_name,) = parsed
    try:
        await perform_send_game(
            message.bot,
            chat_id=message.chat.id,
            game_short_name=game_short_name,
        )
    except (SendGameValidationError, TelegramAPIError) as exc:
        await _answer_operation_failed(message, "Could not send the game", exc)
        return

    await message.answer("Sent game.")


@router.message(Command("setgamescore"))
async def cmd_set_game_score(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_set_game_score_args(message.text or "")
    if parsed is None:
        await message.answer(SET_GAME_SCORE_USAGE, parse_mode="HTML")
        return

    try:
        await perform_set_game_score(message.bot, **parsed)
    except (SetGameScoreValidationError, TelegramAPIError) as exc:
        await _answer_operation_failed(message, "Could not set the game score", exc)
        return

    await message.answer("Set game score.")


@router.message(Command("gamehighscores"))
async def cmd_get_game_high_scores(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_get_game_high_scores_args(message.text or "")
    if parsed is None:
        await message.answer(GET_GAME_HIGH_SCORES_USAGE, parse_mode="HTML")
        return

    try:
        scores = await perform_get_game_high_scores(message.bot, **parsed)
    except (GetGameHighScoresValidationError, TelegramAPIError) as exc:
        await _answer_operation_failed(message, "Could not fetch game high scores", exc)
        return

    await message.answer(_format_game_high_scores(scores))


@router.message(Command("chataction"))
async def cmd_chat_action(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not show the chat action", exc)
        return

    await message.answer(f"Showed the {action} chat action.")

@router.message(Command("messagedraft"))
async def cmd_message_draft(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not send the message draft", exc)
        return

    await message.answer(
        "Sent message draft." if text else "Sent message draft (Thinking… placeholder)."
    )


@router.message(Command("richmessage"))
async def cmd_send_rich_message(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    rich_message = _parse_rich_message_args(message.text or "")
    if rich_message is None:
        await message.answer(RICH_MESSAGE_USAGE, parse_mode="HTML")
        return

    try:
        sent_message = await perform_send_rich_message(
            message.bot,
            chat_id=message.chat.id,
            rich_message=rich_message,
        )
    except SendRichMessageError as exc:
        await _answer_operation_failed(message, "Could not send the rich message", exc)
        return

    message_id = sent_message.get("message_id") if isinstance(sent_message, dict) else None
    if message_id is not None:
        await message.answer(f"Sent rich message {message_id}.")
    else:
        await message.answer("Sent rich message.")


@router.message(Command("richmessagedraft"))
async def cmd_send_rich_message_draft(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_rich_message_draft_args(message.text or "")
    if parsed is None:
        await message.answer(RICH_MESSAGE_DRAFT_USAGE, parse_mode="HTML")
        return

    draft_id, rich_message = parsed
    try:
        await perform_send_rich_message_draft(
            message.bot,
            chat_id=message.chat.id,
            draft_id=draft_id,
            rich_message=rich_message,
        )
    except SendRichMessageDraftError as exc:
        await _answer_operation_failed(
            message,
            "Could not send the rich message draft",
            exc,
        )
        return

    await message.answer(f"Streamed rich message draft {draft_id}.")


@router.message(Command("checklist"))
async def cmd_checklist(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not send the checklist", exc)
        return

    await message.answer(f"Sent checklist with {len(tasks)} tasks.")


@router.message(Command("editchecklist"))
async def cmd_edit_message_checklist(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_edit_checklist_args(message.text or "")
    if parsed is None:
        await message.answer(EDIT_MESSAGE_CHECKLIST_USAGE, parse_mode="HTML")
        return

    business_connection_id, chat_id, message_id, title, tasks = parsed
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
        result = await perform_edit_message_checklist(
            message.bot,
            business_connection_id=business_connection_id,
            chat_id=chat_id,
            message_id=message_id,
            checklist=checklist,
        )
    except EditMessageChecklistError as exc:
        await _answer_operation_failed(message, "Could not edit the checklist", exc)
        return

    result_message_id = result.get("message_id")
    await message.answer(
        f"Edited checklist message {result_message_id} with {len(tasks)} tasks."
        if result_message_id is not None
        else f"Edited checklist with {len(tasks)} tasks."
    )


@router.message(Command("editcaption"))
async def cmd_edit_message_caption(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_edit_message_caption_args(message.text or "")
    if parsed is None:
        await message.answer(EDIT_MESSAGE_CAPTION_USAGE, parse_mode="HTML")
        return

    target, caption, options = parsed
    if caption is not None and len(caption) > EDIT_MESSAGE_CAPTION_LIMIT:
        await message.answer(
            f"Caption is too long: {len(caption)} characters "
            f"(max {EDIT_MESSAGE_CAPTION_LIMIT})."
        )
        return

    try:
        result = await perform_edit_message_caption(
            message.bot,
            caption=caption,
            **target,
            **options,
        )
    except EditMessageCaptionError as exc:
        await _answer_operation_failed(message, "Could not edit the message caption", exc)
        return

    if isinstance(result, dict):
        result_message_id = result.get("message_id")
        await message.answer(
            f"Edited caption for message {result_message_id}."
            if result_message_id is not None
            else "Edited message caption."
        )
        return

    await message.answer("Edited inline message caption.")


@router.message(Command("editmedia"))
async def cmd_edit_message_media(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_edit_message_media_args(message.text or "")
    if parsed is None:
        await message.answer(EDIT_MESSAGE_MEDIA_USAGE, parse_mode="HTML")
        return

    target, media_type, media, caption, options = parsed
    if caption is not None and len(caption) > EDIT_MESSAGE_MEDIA_CAPTION_LIMIT:
        await message.answer(
            f"Caption is too long: {len(caption)} characters "
            f"(max {EDIT_MESSAGE_MEDIA_CAPTION_LIMIT})."
        )
        return

    try:
        result = await perform_edit_message_media(
            message.bot,
            media_type=media_type,
            media=media,
            caption=caption,
            **target,
            **options,
        )
    except EditMessageMediaError as exc:
        await _answer_operation_failed(message, "Could not edit the message media", exc)
        return

    if isinstance(result, dict):
        result_message_id = result.get("message_id")
        await message.answer(
            f"Edited media for message {result_message_id}."
            if result_message_id is not None
            else "Edited message media."
        )
        return

    await message.answer("Edited inline message media.")


@router.message(Command("editreplymarkup"))
async def cmd_edit_message_reply_markup(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_edit_message_reply_markup_args(message.text or "")
    if parsed is None:
        await message.answer(EDIT_MESSAGE_REPLY_MARKUP_USAGE, parse_mode="HTML")
        return

    target, reply_markup = parsed

    try:
        result = await perform_edit_message_reply_markup(
            message.bot,
            reply_markup=reply_markup,
            **target,
        )
    except EditMessageReplyMarkupError as exc:
        await _answer_operation_failed(message, "Could not edit the message reply markup", exc)
        return

    if isinstance(result, dict):
        result_message_id = result.get("message_id")
        await message.answer(
            f"Edited reply markup for message {result_message_id}."
            if result_message_id is not None
            else "Edited message reply markup."
        )
        return

    await message.answer("Edited inline message reply markup.")


@router.message(Command("editlivelocation"))
async def cmd_edit_message_live_location(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_edit_message_live_location_args(message.text or "")
    if parsed is None:
        await message.answer(EDIT_MESSAGE_LIVE_LOCATION_USAGE, parse_mode="HTML")
        return

    target, latitude, longitude, options = parsed

    try:
        result = await perform_edit_message_live_location(
            message.bot,
            latitude=latitude,
            longitude=longitude,
            **target,
            **options,
        )
    except EditMessageLiveLocationError as exc:
        await _answer_operation_failed(message, "Could not edit the live location", exc)
        return

    if isinstance(result, dict):
        result_message_id = result.get("message_id")
        await message.answer(
            f"Edited live location for message {result_message_id}."
            if result_message_id is not None
            else "Edited message live location."
        )
        return

    await message.answer("Edited inline live location.")


@router.message(Command("stoplivelocation"))
async def cmd_stop_message_live_location(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    target = _parse_message_management_target_args(message.text or "")
    if target is None:
        await message.answer(STOP_MESSAGE_LIVE_LOCATION_USAGE, parse_mode="HTML")
        return

    try:
        result = await perform_stop_message_live_location(message.bot, **target)
    except StopMessageLiveLocationError as exc:
        await _answer_operation_failed(message, "Could not stop the live location", exc)
        return

    if isinstance(result, dict):
        result_message_id = result.get("message_id")
        await message.answer(
            f"Stopped live location for message {result_message_id}."
            if result_message_id is not None
            else "Stopped message live location."
        )
        return

    await message.answer("Stopped inline live location.")


@router.message(Command("poststory"))
async def cmd_post_story(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_post_story_args(message.text or "")
    if parsed is None:
        await message.answer(POST_STORY_USAGE, parse_mode="HTML")
        return

    business_connection_id, active_period, photo, caption = parsed
    if active_period not in POST_STORY_ACTIVE_PERIODS:
        allowed = ", ".join(str(value) for value in POST_STORY_ACTIVE_PERIODS)
        await message.answer(f"Active period must be one of: {allowed}.")
        return

    if caption is not None and len(caption) > POST_STORY_CAPTION_LIMIT:
        await message.answer(
            f"Caption is too long: {len(caption)} characters "
            f"(max {POST_STORY_CAPTION_LIMIT})."
        )
        return

    try:
        story = await perform_post_story(
            message.bot,
            business_connection_id=business_connection_id,
            content={"type": "photo", "photo": photo},
            active_period=active_period,
            caption=caption,
        )
    except PostStoryError as exc:
        await _answer_operation_failed(message, "Could not post the story", exc)
        return

    story_id = story.get("id")
    await message.answer(
        f"Posted story {story_id}." if story_id is not None else "Posted story."
    )


@router.message(Command("repoststory"))
async def cmd_repost_story(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_repost_story_args(message.text or "")
    if parsed is None:
        await message.answer(REPOST_STORY_USAGE, parse_mode="HTML")
        return

    business_connection_id, from_chat_id, from_story_id, active_period = parsed
    if active_period not in POST_STORY_ACTIVE_PERIODS:
        allowed = ", ".join(str(value) for value in POST_STORY_ACTIVE_PERIODS)
        await message.answer(f"Active period must be one of: {allowed}.")
        return

    try:
        story = await perform_repost_story(
            message.bot,
            business_connection_id=business_connection_id,
            from_chat_id=from_chat_id,
            from_story_id=from_story_id,
            active_period=active_period,
        )
    except RepostStoryError as exc:
        await _answer_operation_failed(message, "Could not repost the story", exc)
        return

    story_id = story.get("id")
    await message.answer(
        f"Reposted story {story_id}."
        if story_id is not None
        else "Reposted story."
    )


@router.message(Command("editstory"))
async def cmd_edit_story(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_edit_story_args(message.text or "")
    if parsed is None:
        await message.answer(EDIT_STORY_USAGE, parse_mode="HTML")
        return

    business_connection_id, story_id, photo, caption = parsed
    if caption is not None and len(caption) > POST_STORY_CAPTION_LIMIT:
        await message.answer(
            f"Caption is too long: {len(caption)} characters "
            f"(max {POST_STORY_CAPTION_LIMIT})."
        )
        return

    try:
        story = await perform_edit_story(
            message.bot,
            business_connection_id=business_connection_id,
            story_id=story_id,
            content={"type": "photo", "photo": photo},
            caption=caption,
        )
    except EditStoryError as exc:
        await _answer_operation_failed(message, "Could not edit the story", exc)
        return

    result_story_id = story.get("id")
    await message.answer(
        f"Edited story {result_story_id}."
        if result_story_id is not None
        else "Edited story."
    )


@router.message(Command("deletestory"))
async def cmd_delete_story(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_delete_story_args(message.text or "")
    if parsed is None:
        await message.answer(DELETE_STORY_USAGE, parse_mode="HTML")
        return

    business_connection_id, story_id = parsed

    try:
        await perform_delete_story(
            message.bot,
            business_connection_id=business_connection_id,
            story_id=story_id,
        )
    except DeleteStoryError as exc:
        await _answer_operation_failed(message, "Could not delete the story", exc)
        return

    await message.answer(f"Deleted story {story_id}.")


@router.message(Command("businessconnection"))
async def cmd_business_connection(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not fetch the business connection", exc)
        return

    await message.answer(format_business_connection(connection), parse_mode="HTML")


@router.message(Command("businessstarbalance"))
async def cmd_business_star_balance(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    business_connection_id = _parse_get_business_account_star_balance_args(
        message.text or ""
    )
    if business_connection_id is None:
        await message.answer(
            GET_BUSINESS_ACCOUNT_STAR_BALANCE_USAGE,
            parse_mode="HTML",
        )
        return

    try:
        balance = await perform_get_business_account_star_balance(
            message.bot,
            business_connection_id=business_connection_id,
        )
    except GetBusinessAccountStarBalanceError as exc:
        await _answer_operation_failed(
            message,
            "Could not fetch the business account Star balance",
            exc,
        )
        return

    await message.answer(
        format_business_account_star_balance(
            balance,
            business_connection_id=business_connection_id,
        ),
        parse_mode="HTML",
    )


@router.message(Command("mystarbalance"))
async def cmd_my_star_balance(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    if not _parse_get_my_star_balance_args(message.text or ""):
        await message.answer(
            GET_MY_STAR_BALANCE_USAGE,
            parse_mode="HTML",
        )
        return

    try:
        balance = await perform_get_my_star_balance(message.bot)
    except GetMyStarBalanceError as exc:
        await _answer_operation_failed(message, "Could not fetch the bot Star balance", exc)
        return

    await message.answer(format_my_star_balance(balance), parse_mode="HTML")


@router.message(Command("startransactions"))
async def cmd_star_transactions(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_get_star_transactions_args(message.text or "")
    if parsed is None:
        await message.answer(GET_STAR_TRANSACTIONS_USAGE, parse_mode="HTML")
        return

    try:
        transactions = await perform_get_star_transactions(message.bot, **parsed)
    except GetStarTransactionsError as exc:
        await _answer_operation_failed(message, "Could not fetch the bot Star transactions", exc)
        return

    await message.answer(
        format_star_transactions(transactions, **parsed),
        parse_mode="HTML",
    )


@router.message(Command("refundstars"))
async def cmd_refund_stars(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_refund_star_payment_args(message.text or "")
    if parsed is None:
        await message.answer(REFUND_STAR_PAYMENT_USAGE, parse_mode="HTML")
        return

    user_id, telegram_payment_charge_id, confirmed = parsed
    if not confirmed:
        await message.answer(REFUND_STAR_PAYMENT_WARNING, parse_mode="HTML")
        return

    idempotency_key = (user_id, telegram_payment_charge_id)
    if idempotency_key in _REFUNDED_STAR_PAYMENT_KEYS:
        await message.answer(
            format_refund_star_payment_result(
                user_id=user_id,
                telegram_payment_charge_id=telegram_payment_charge_id,
                duplicate=True,
            ),
            parse_mode="HTML",
        )
        return

    try:
        await perform_refund_star_payment(
            message.bot,
            user_id=user_id,
            telegram_payment_charge_id=telegram_payment_charge_id,
        )
    except RefundStarPaymentError as exc:
        await _answer_operation_failed(message, "Could not refund the Stars payment", exc)
        return

    _REFUNDED_STAR_PAYMENT_KEYS.add(idempotency_key)
    await message.answer(
        format_refund_star_payment_result(
            user_id=user_id,
            telegram_payment_charge_id=telegram_payment_charge_id,
        ),
        parse_mode="HTML",
    )


@router.message(Command("edituserstarsubscription"))
async def cmd_edit_user_star_subscription(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_edit_user_star_subscription_args(message.text or "")
    if parsed is None:
        await message.answer(EDIT_USER_STAR_SUBSCRIPTION_USAGE, parse_mode="HTML")
        return

    user_id, telegram_payment_charge_id, is_canceled, confirmed = parsed
    if not confirmed:
        await message.answer(
            EDIT_USER_STAR_SUBSCRIPTION_WARNING,
            parse_mode="HTML",
        )
        return

    idempotency_key = (user_id, telegram_payment_charge_id, is_canceled)
    if idempotency_key in _EDITED_USER_STAR_SUBSCRIPTION_KEYS:
        await message.answer(
            format_edit_user_star_subscription_result(
                user_id=user_id,
                telegram_payment_charge_id=telegram_payment_charge_id,
                is_canceled=is_canceled,
                duplicate=True,
            ),
            parse_mode="HTML",
        )
        return

    try:
        await perform_edit_user_star_subscription(
            message.bot,
            user_id=user_id,
            telegram_payment_charge_id=telegram_payment_charge_id,
            is_canceled=is_canceled,
        )
    except EditUserStarSubscriptionError as exc:
        await _answer_operation_failed(message, "Could not edit the Stars subscription", exc)
        return

    _EDITED_USER_STAR_SUBSCRIPTION_KEYS.add(idempotency_key)
    await message.answer(
        format_edit_user_star_subscription_result(
            user_id=user_id,
            telegram_payment_charge_id=telegram_payment_charge_id,
            is_canceled=is_canceled,
        ),
        parse_mode="HTML",
    )


@router.message(Command("businessgifts"))
async def cmd_business_gifts(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_get_business_account_gifts_args(message.text or "")
    if parsed is None:
        await message.answer(GET_BUSINESS_ACCOUNT_GIFTS_USAGE, parse_mode="HTML")
        return

    business_connection_id, options = parsed
    try:
        gifts = await perform_get_business_account_gifts(
            message.bot,
            business_connection_id=business_connection_id,
            **options,
        )
    except GetBusinessAccountGiftsError as exc:
        await _answer_operation_failed(message, "Could not fetch the business account gifts", exc)
        return

    await message.answer(
        format_business_account_gifts(
            gifts,
            business_connection_id=business_connection_id,
        ),
        parse_mode="HTML",
    )


@router.message(Command("usergifts"))
async def cmd_user_gifts(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_get_user_gifts_args(message.text or "")
    if parsed is None:
        await message.answer(GET_USER_GIFTS_USAGE, parse_mode="HTML")
        return

    user_id, options = parsed
    try:
        gifts = await perform_get_user_gifts(
            message.bot,
            user_id=user_id,
            **options,
        )
    except GetUserGiftsError as exc:
        await _answer_operation_failed(message, "Could not fetch the user gifts", exc)
        return

    await message.answer(
        format_user_gifts(gifts, user_id=user_id),
        parse_mode="HTML",
    )


@router.message(Command("chatgifts"))
async def cmd_chat_gifts(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_get_chat_gifts_args(message.text or "")
    if parsed is None:
        await message.answer(GET_CHAT_GIFTS_USAGE, parse_mode="HTML")
        return

    chat_id, options = parsed
    try:
        gifts = await perform_get_chat_gifts(
            message.bot,
            chat_id=chat_id,
            **options,
        )
    except GetChatGiftsError as exc:
        await _answer_operation_failed(message, "Could not fetch the chat gifts", exc)
        return

    await message.answer(
        format_chat_gifts(gifts, chat_id=chat_id),
        parse_mode="HTML",
    )


@router.message(Command("transferbusinessstars"))
async def cmd_transfer_business_stars(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_transfer_business_account_stars_args(message.text or "")
    if parsed is None:
        await message.answer(
            TRANSFER_BUSINESS_ACCOUNT_STARS_USAGE,
            parse_mode="HTML",
        )
        return

    business_connection_id, star_count, confirmed = parsed
    if not confirmed:
        await message.answer(
            TRANSFER_BUSINESS_ACCOUNT_STARS_WARNING,
            parse_mode="HTML",
        )
        return

    try:
        await perform_transfer_business_account_stars(
            message.bot,
            business_connection_id=business_connection_id,
            star_count=star_count,
        )
    except TransferBusinessAccountStarsError as exc:
        await _answer_operation_failed(
            message,
            "Could not transfer the business account Stars",
            exc,
        )
        return

    await message.answer(
        format_transfer_business_account_stars_result(
            business_connection_id=business_connection_id,
            star_count=star_count,
        ),
        parse_mode="HTML",
    )


@router.message(Command("convertgiftstars"))
async def cmd_convert_gift_stars(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_convert_gift_to_stars_args(message.text or "")
    if parsed is None:
        await message.answer(CONVERT_GIFT_TO_STARS_USAGE, parse_mode="HTML")
        return

    business_connection_id, owned_gift_id, confirmed = parsed
    if not confirmed:
        await message.answer(
            CONVERT_GIFT_TO_STARS_WARNING,
            parse_mode="HTML",
        )
        return

    try:
        await perform_convert_gift_to_stars(
            message.bot,
            business_connection_id=business_connection_id,
            owned_gift_id=owned_gift_id,
        )
    except ConvertGiftToStarsError as exc:
        await _answer_operation_failed(message, "Could not convert the gift to Stars", exc)
        return

    await message.answer(
        format_convert_gift_to_stars_result(
            business_connection_id=business_connection_id,
            owned_gift_id=owned_gift_id,
        ),
        parse_mode="HTML",
    )


@router.message(Command("upgradegift"))
async def cmd_upgrade_gift(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_upgrade_gift_args(message.text or "")
    if parsed is None:
        await message.answer(UPGRADE_GIFT_USAGE, parse_mode="HTML")
        return

    business_connection_id, owned_gift_id, keep_original_details, confirmed = parsed
    if not confirmed:
        await message.answer(UPGRADE_GIFT_WARNING, parse_mode="HTML")
        return

    try:
        await perform_upgrade_gift(
            message.bot,
            business_connection_id=business_connection_id,
            owned_gift_id=owned_gift_id,
            keep_original_details=keep_original_details,
        )
    except UpgradeGiftError as exc:
        await _answer_operation_failed(message, "Could not upgrade the gift", exc)
        return

    await message.answer(
        format_upgrade_gift_result(
            business_connection_id=business_connection_id,
            owned_gift_id=owned_gift_id,
            keep_original_details=keep_original_details,
        ),
        parse_mode="HTML",
    )


@router.message(Command("transfergift"))
async def cmd_transfer_gift(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_transfer_gift_args(message.text or "")
    if parsed is None:
        await message.answer(TRANSFER_GIFT_USAGE, parse_mode="HTML")
        return

    business_connection_id, owned_gift_id, new_owner_chat_id, star_count, confirmed = (
        parsed
    )
    if not confirmed:
        await message.answer(TRANSFER_GIFT_WARNING, parse_mode="HTML")
        return

    try:
        await perform_transfer_gift(
            message.bot,
            business_connection_id=business_connection_id,
            owned_gift_id=owned_gift_id,
            new_owner_chat_id=new_owner_chat_id,
            star_count=star_count,
        )
    except TransferGiftError as exc:
        await _answer_operation_failed(message, "Could not transfer the gift", exc)
        return

    await message.answer(
        format_transfer_gift_result(
            business_connection_id=business_connection_id,
            owned_gift_id=owned_gift_id,
            new_owner_chat_id=new_owner_chat_id,
            star_count=star_count,
        ),
        parse_mode="HTML",
    )


@router.message(Command("readbusinessmessage"))
async def cmd_read_business_message(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_read_business_message_args(message.text or "")
    if parsed is None:
        await message.answer(READ_BUSINESS_MESSAGE_USAGE, parse_mode="HTML")
        return

    business_connection_id, message_id = parsed
    try:
        await perform_read_business_message(
            message.bot,
            business_connection_id=business_connection_id,
            message_id=message_id,
        )
    except ReadBusinessMessageError as exc:
        await _answer_operation_failed(message, "Could not mark the business message as read", exc)
        return

    await message.answer(
        f"Marked business message {message_id} as read for {business_connection_id}."
    )


@router.message(Command("setbusinessaccountname"))
async def cmd_set_business_account_name(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_set_business_account_name_args(message.text or "")
    if parsed is None:
        await message.answer(SET_BUSINESS_ACCOUNT_NAME_USAGE, parse_mode="HTML")
        return

    business_connection_id, first_name, last_name = parsed
    try:
        await perform_set_business_account_name(
            message.bot,
            business_connection_id=business_connection_id,
            first_name=first_name,
            last_name=last_name,
        )
    except SetBusinessAccountNameError as exc:
        await _answer_operation_failed(message, "Could not set the business account name", exc)
        return

    await message.answer(f"Set business account name for {business_connection_id}.")


@router.message(Command("setbusinessaccountusername"))
async def cmd_set_business_account_username(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_set_business_account_username_args(message.text or "")
    if parsed is None:
        await message.answer(SET_BUSINESS_ACCOUNT_USERNAME_USAGE, parse_mode="HTML")
        return

    business_connection_id, username = parsed
    try:
        await perform_set_business_account_username(
            message.bot,
            business_connection_id=business_connection_id,
            username=username,
        )
    except SetBusinessAccountUsernameError as exc:
        await _answer_operation_failed(message, "Could not set the business account username", exc)
        return

    await message.answer(f"Set business account username for {business_connection_id}.")


@router.message(Command("setbusinessaccountbio"))
async def cmd_set_business_account_bio(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_set_business_account_bio_args(message.text or "")
    if parsed is None:
        await message.answer(SET_BUSINESS_ACCOUNT_BIO_USAGE, parse_mode="HTML")
        return

    business_connection_id, bio = parsed
    try:
        await perform_set_business_account_bio(
            message.bot,
            business_connection_id=business_connection_id,
            bio=bio,
        )
    except SetBusinessAccountBioError as exc:
        await _answer_operation_failed(message, "Could not set the business account bio", exc)
        return

    action = "Cleared" if bio == "" else "Set"
    await message.answer(f"{action} business account bio for {business_connection_id}.")


@router.message(Command("setbusinessaccountprofilephoto"))
async def cmd_set_business_account_profile_photo(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_set_business_account_profile_photo_args(message.text or "")
    if parsed is None:
        await message.answer(
            SET_BUSINESS_ACCOUNT_PROFILE_PHOTO_USAGE,
            parse_mode="HTML",
        )
        return

    business_connection_id, photo_path, is_public = parsed
    try:
        await perform_set_business_account_profile_photo(
            message.bot,
            business_connection_id=business_connection_id,
            photo_path=photo_path,
            is_public=is_public,
        )
    except SetBusinessAccountProfilePhotoError as exc:
        await _answer_operation_failed(
            message,
            "Could not set the business account profile photo",
            exc,
        )
        return

    await message.answer(
        format_set_business_account_profile_photo_result(
            business_connection_id=business_connection_id,
            photo_path=photo_path,
            is_public=is_public,
        ),
        parse_mode="HTML",
    )


@router.message(Command("removebusinessaccountprofilephoto"))
async def cmd_remove_business_account_profile_photo(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_remove_business_account_profile_photo_args(message.text or "")
    if parsed is None:
        await message.answer(
            REMOVE_BUSINESS_ACCOUNT_PROFILE_PHOTO_USAGE,
            parse_mode="HTML",
        )
        return

    business_connection_id, is_public = parsed
    try:
        await perform_remove_business_account_profile_photo(
            message.bot,
            business_connection_id=business_connection_id,
            is_public=is_public,
        )
    except RemoveBusinessAccountProfilePhotoError as exc:
        await _answer_operation_failed(
            message,
            "Could not remove the business account profile photo",
            exc,
        )
        return

    await message.answer(
        format_remove_business_account_profile_photo_result(
            business_connection_id=business_connection_id,
            is_public=is_public,
        ),
        parse_mode="HTML",
    )


@router.message(Command("setbusinessaccountgiftsettings"))
async def cmd_set_business_account_gift_settings(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_set_business_account_gift_settings_args(message.text or "")
    if parsed is None:
        await message.answer(
            SET_BUSINESS_ACCOUNT_GIFT_SETTINGS_USAGE,
            parse_mode="HTML",
        )
        return

    business_connection_id, show_gift_button, accepted_gift_types = parsed
    try:
        await perform_set_business_account_gift_settings(
            message.bot,
            business_connection_id=business_connection_id,
            show_gift_button=show_gift_button,
            accepted_gift_types=accepted_gift_types,
        )
    except SetBusinessAccountGiftSettingsError as exc:
        await _answer_operation_failed(
            message,
            "Could not set the business account gift settings",
            exc,
        )
        return

    await message.answer(
        format_set_business_account_gift_settings_result(
            business_connection_id=business_connection_id,
            show_gift_button=show_gift_button,
            accepted_gift_types=accepted_gift_types,
        ),
        parse_mode="HTML",
    )


@router.message(Command("deletebusinessmessages"))
async def cmd_delete_business_messages(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_delete_business_messages_args(message.text or "")
    if parsed is None:
        await message.answer(DELETE_BUSINESS_MESSAGES_USAGE, parse_mode="HTML")
        return

    business_connection_id, message_ids, confirmed = parsed
    if not confirmed:
        await message.answer(DELETE_BUSINESS_MESSAGES_WARNING, parse_mode="HTML")
        return

    try:
        await perform_delete_business_messages(
            message.bot,
            business_connection_id=business_connection_id,
            message_ids=message_ids,
        )
    except DeleteBusinessMessagesError as exc:
        await _answer_operation_failed(message, "Could not delete the business messages", exc)
        return

    await message.answer(
        f"Deleted {len(message_ids)} business messages for {business_connection_id}."
    )


@router.message(Command("managedbottoken"))
async def cmd_managed_bot_token(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not fetch the managed bot token", exc)
        return

    await message.answer(
        format_managed_bot_token(user_id=user_id, token=token),
        parse_mode="HTML",
    )


@router.message(Command("managedbotaccess"))
async def cmd_managed_bot_access_settings(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(
            message,
            "Could not fetch the managed bot access settings",
            exc,
        )
        return

    await message.answer(
        format_managed_bot_access_settings(user_id=user_id, settings=settings),
        parse_mode="HTML",
    )


@router.message(Command("setmanagedbotaccess"))
async def cmd_set_managed_bot_access_settings(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(
            message,
            "Could not set the managed bot access settings",
            exc,
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
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not replace the managed bot token", exc)
        return

    await message.answer(
        format_replaced_managed_bot_token(user_id=user_id, token=token),
        parse_mode="HTML",
    )


@router.message(Command("availablegifts"))
async def cmd_available_gifts(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    confirmed = _parse_available_gifts_args(message.text or "")
    if confirmed is None:
        await message.answer(GET_AVAILABLE_GIFTS_USAGE, parse_mode="HTML")
        return

    if not confirmed:
        await message.answer(GET_AVAILABLE_GIFTS_WARNING, parse_mode="HTML")
        return

    try:
        gifts = await perform_get_available_gifts(message.bot)
    except GetAvailableGiftsError as exc:
        await _answer_operation_failed(message, "Could not fetch available gifts", exc)
        return

    await message.answer(format_available_gifts(gifts), parse_mode="HTML")


@router.message(Command("sendgift"))
async def cmd_send_gift(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_send_gift_args(message.text or "")
    if parsed is None:
        await message.answer(SEND_GIFT_USAGE, parse_mode="HTML")
        return

    receiver_type, receiver_id, gift_id, confirmed, text = parsed
    if not confirmed:
        await message.answer(SEND_GIFT_WARNING, parse_mode="HTML")
        return

    if text is not None and len(text) > SEND_GIFT_TEXT_LIMIT:
        await message.answer(
            f"Gift text is too long: {len(text)} characters "
            f"(max {SEND_GIFT_TEXT_LIMIT})."
        )
        return

    kwargs = {
        "gift_id": gift_id,
        "text": text,
        "text_parse_mode": "HTML" if text else None,
    }
    if receiver_type == "user":
        kwargs["user_id"] = receiver_id
    else:
        kwargs["chat_id"] = receiver_id

    try:
        await perform_send_gift(message.bot, **kwargs)
    except SendGiftError as exc:
        await _answer_operation_failed(message, "Could not send gift", exc)
        return

    await message.answer("Sent gift.")


@router.message(Command("giftpremium"))
async def cmd_gift_premium(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_gift_premium_args(message.text or "")
    if parsed is None:
        await message.answer(GIFT_PREMIUM_USAGE, parse_mode="HTML")
        return

    user_id, month_count, star_count, confirmed, text = parsed
    if not confirmed:
        await message.answer(GIFT_PREMIUM_WARNING, parse_mode="HTML")
        return

    if text is not None and len(text) > GIFT_PREMIUM_TEXT_LIMIT:
        await message.answer(
            f"Premium gift text is too long: {len(text)} characters "
            f"(max {GIFT_PREMIUM_TEXT_LIMIT})."
        )
        return

    try:
        await perform_gift_premium_subscription(
            message.bot,
            user_id=user_id,
            month_count=month_count,
            star_count=star_count,
            text=text,
            text_parse_mode="HTML" if text else None,
        )
    except GiftPremiumSubscriptionError as exc:
        await _answer_operation_failed(message, "Could not gift Premium subscription", exc)
        return

    await message.answer("Gifted Premium subscription.")


@router.message(Command("verifyuser"))
async def cmd_verify_user(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_verify_user_args(message.text or "")
    if parsed is None:
        await message.answer(VERIFY_USER_USAGE, parse_mode="HTML")
        return

    user_id, confirmed, custom_description = parsed
    if not confirmed:
        await message.answer(VERIFY_USER_WARNING, parse_mode="HTML")
        return

    if (
        custom_description is not None
        and len(custom_description) > VERIFY_USER_DESCRIPTION_LIMIT
    ):
        await message.answer(
            f"Verification description is too long: {len(custom_description)} "
            f"characters (max {VERIFY_USER_DESCRIPTION_LIMIT})."
        )
        return

    try:
        await perform_verify_user(
            message.bot,
            user_id=user_id,
            custom_description=custom_description,
        )
    except VerifyUserError as exc:
        await _answer_operation_failed(message, "Could not verify user", exc)
        return

    await message.answer(f"Verified user {user_id}.")


@router.message(Command("removeuserverification"))
async def cmd_remove_user_verification(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_remove_user_verification_args(message.text or "")
    if parsed is None:
        await message.answer(REMOVE_USER_VERIFICATION_USAGE, parse_mode="HTML")
        return

    user_id, confirmed = parsed
    if not confirmed:
        await message.answer(REMOVE_USER_VERIFICATION_WARNING, parse_mode="HTML")
        return

    try:
        await perform_remove_user_verification(
            message.bot,
            user_id=user_id,
        )
    except RemoveUserVerificationError as exc:
        await _answer_operation_failed(message, "Could not remove user verification", exc)
        return

    await message.answer(f"Removed verification from user {user_id}.")


@router.message(Command("verifychat"))
async def cmd_verify_chat(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_verify_chat_args(message.text or "")
    if parsed is None:
        await message.answer(VERIFY_CHAT_USAGE, parse_mode="HTML")
        return

    chat_id, confirmed, custom_description = parsed
    if not confirmed:
        await message.answer(VERIFY_CHAT_WARNING, parse_mode="HTML")
        return

    if (
        custom_description is not None
        and len(custom_description) > VERIFY_CHAT_DESCRIPTION_LIMIT
    ):
        await message.answer(
            f"Verification description is too long: {len(custom_description)} "
            f"characters (max {VERIFY_CHAT_DESCRIPTION_LIMIT})."
        )
        return

    try:
        await perform_verify_chat(
            message.bot,
            chat_id=chat_id,
            custom_description=custom_description,
        )
    except VerifyChatError as exc:
        await _answer_operation_failed(message, "Could not verify chat", exc)
        return

    await message.answer(f"Verified chat {chat_id}.")


@router.message(Command("removechatverification"))
async def cmd_remove_chat_verification(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_remove_chat_verification_args(message.text or "")
    if parsed is None:
        await message.answer(REMOVE_CHAT_VERIFICATION_USAGE, parse_mode="HTML")
        return

    chat_id, confirmed = parsed
    if not confirmed:
        await message.answer(REMOVE_CHAT_VERIFICATION_WARNING, parse_mode="HTML")
        return

    try:
        await perform_remove_chat_verification(
            message.bot,
            chat_id=chat_id,
        )
    except RemoveChatVerificationError as exc:
        await _answer_operation_failed(message, "Could not remove chat verification", exc)
        return

    await message.answer(f"Removed verification from chat {chat_id}.")


@router.message(Command("userprofilephotos"))
async def cmd_user_profile_photos(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not fetch user profile photos", exc)
        return

    await message.answer(
        format_user_profile_photos(result, user_id), parse_mode="HTML"
    )


@router.message(Command("userprofileaudios"))
async def cmd_user_profile_audios(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not fetch user profile audios", exc)
        return

    await message.answer(
        format_user_profile_audios(result, user_id), parse_mode="HTML"
    )


@router.message(Command("banchatmember"))
async def cmd_ban_chat_member(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not ban the user", exc)
        return

    await message.answer(
        format_ban_result(chat_id, user_id, until_date, revoke_messages),
        parse_mode="HTML",
    )


@router.message(Command("banchatsenderchat"))
async def cmd_ban_chat_sender_chat(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not ban the sender chat", exc)
        return

    await message.answer(
        format_ban_sender_chat_result(chat_id, sender_chat_id),
        parse_mode="HTML",
    )


@router.message(Command("unbanchatmember"))
async def cmd_unban_chat_member(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not unban the user", exc)
        return

    await message.answer(
        format_unban_result(chat_id, user_id, only_if_banned),
        parse_mode="HTML",
    )


@router.message(Command("unbanchatsenderchat"))
async def cmd_unban_chat_sender_chat(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not unban the sender chat", exc)
        return

    await message.answer(
        format_unban_sender_chat_result(chat_id, sender_chat_id),
        parse_mode="HTML",
    )


@router.message(Command("restrictchatmember"))
async def cmd_restrict_chat_member(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not restrict the user", exc)
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
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not set chat permissions", exc)
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
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not unpin the chat message", exc)
        return

    await message.answer(
        format_unpin_chat_message_result(chat_id=chat_id, message_id=message_id),
        parse_mode="HTML",
    )


@router.message(Command("deletemessage"))
async def cmd_delete_message(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_delete_message_args(message.text or "")
    if parsed is None:
        await message.answer(DELETE_MESSAGE_USAGE, parse_mode="HTML")
        return

    chat_id, message_id, confirmed = parsed
    if not confirmed:
        await message.answer(DELETE_MESSAGE_WARNING, parse_mode="HTML")
        return

    try:
        await perform_delete_message(
            message.bot,
            chat_id=chat_id,
            message_id=message_id,
        )
    except TelegramAPIError as exc:
        await _answer_operation_failed(message, "Could not delete the message", exc)
        return

    await message.answer(
        format_delete_message_result(chat_id=chat_id, message_id=message_id),
        parse_mode="HTML",
    )


@router.message(Command("deletemessages"))
async def cmd_delete_messages(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_delete_messages_args(message.text or "")
    if parsed is None:
        await message.answer(DELETE_MESSAGES_USAGE, parse_mode="HTML")
        return

    chat_id, message_ids, confirmed = parsed
    if not confirmed:
        await message.answer(DELETE_MESSAGES_WARNING, parse_mode="HTML")
        return

    try:
        result = await perform_delete_messages(
            message.bot,
            chat_id=chat_id,
            message_ids=message_ids,
        )
    except DeleteMessagesError as exc:
        await _answer_operation_failed(message, "Could not delete the messages", exc)
        return

    await message.answer(
        format_delete_messages_result(result),
        parse_mode="HTML",
    )


@router.message(Command("unpinallchatmessages"))
async def cmd_unpin_all_chat_messages(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    chat_id = _parse_unpin_all_chat_messages_args(message.text or "")
    if chat_id is None:
        await message.answer(UNPIN_ALL_CHAT_MESSAGES_USAGE, parse_mode="HTML")
        return

    try:
        await perform_unpin_all_chat_messages(message.bot, chat_id=chat_id)
    except TelegramAPIError as exc:
        await _answer_operation_failed(message, "Could not unpin all chat messages", exc)
        return

    await message.answer(
        format_unpin_all_chat_messages_result(chat_id=chat_id),
        parse_mode="HTML",
    )


@router.message(Command("pinchatmessage"))
async def cmd_pin_chat_message(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not pin the chat message", exc)
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
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    chat_id = _parse_delete_chat_photo_args(message.text or "")
    if chat_id is None:
        await message.answer(DELETE_CHAT_PHOTO_USAGE, parse_mode="HTML")
        return

    try:
        await perform_delete_chat_photo(message.bot, chat_id=chat_id)
    except TelegramAPIError as exc:
        await _answer_operation_failed(message, "Could not delete the chat photo", exc)
        return

    await message.answer(
        format_delete_chat_photo_result(chat_id=chat_id),
        parse_mode="HTML",
    )


@router.message(Command("setchatphoto"))
async def cmd_set_chat_photo(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not set the chat photo", exc)
        return

    await message.answer(
        format_set_chat_photo_result(chat_id=chat_id, photo_path=photo_path),
        parse_mode="HTML",
    )


@router.message(Command("setmyprofilephoto"))
async def cmd_set_my_profile_photo(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not set the bot profile photo", exc)
        return

    await message.answer(
        format_set_my_profile_photo_result(photo_path=photo_path),
        parse_mode="HTML",
    )


@router.message(Command("removemyprofilephoto"))
async def cmd_remove_my_profile_photo(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    if not _parse_remove_my_profile_photo_args(message.text or ""):
        await message.answer(REMOVE_MY_PROFILE_PHOTO_USAGE, parse_mode="HTML")
        return

    try:
        await perform_remove_my_profile_photo(message.bot)
    except RemoveMyProfilePhotoError as exc:
        await _answer_operation_failed(message, "Could not remove the bot profile photo", exc)
        return

    await message.answer(
        format_remove_my_profile_photo_result(),
        parse_mode="HTML",
    )


@router.message(Command("setchatdescription"))
async def cmd_set_chat_description(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not set the chat description", exc)
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
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not set the chat title", exc)
        return

    await message.answer(
        format_set_chat_title_result(chat_id=chat_id, title=title),
        parse_mode="HTML",
    )


@router.message(Command("setmycommands"))
async def cmd_set_my_commands(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_set_my_commands_args(message.text or "")
    if parsed is None:
        await message.answer(SET_MY_COMMANDS_USAGE, parse_mode="HTML")
        return

    try:
        await perform_set_my_commands(message.bot, commands=parsed)
    except TelegramAPIError as exc:
        await _answer_operation_failed(message, "Could not set bot commands", exc)
        return

    await message.answer(
        format_set_my_commands_result(parsed),
        parse_mode="HTML",
    )


@router.message(Command("setchatmenubutton"))
async def cmd_set_chat_menu_button(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not set the chat menu button", exc)
        return

    await message.answer(
        format_set_chat_menu_button_result(chat_id=chat_id, menu_button=menu_button),
        parse_mode="HTML",
    )


@router.message(Command("getchatmenubutton"))
async def cmd_get_chat_menu_button(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_get_chat_menu_button_args(message.text or "")
    if parsed is False:
        await message.answer(GET_CHAT_MENU_BUTTON_USAGE, parse_mode="HTML")
        return

    try:
        menu_button = await perform_get_chat_menu_button(
            message.bot,
            chat_id=parsed,
        )
    except TelegramAPIError as exc:
        await _answer_operation_failed(message, "Could not get the chat menu button", exc)
        return

    await message.answer(
        format_get_chat_menu_button_result(menu_button, chat_id=parsed),
        parse_mode="HTML",
    )


@router.message(Command("setmyname"))
async def cmd_set_my_name(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not set bot name", exc)
        return
    except TelegramAPIError as exc:
        await _answer_operation_failed(message, "Could not set bot name", exc)
        return

    await message.answer(
        format_set_my_name_result(name=name, language_code=language_code),
        parse_mode="HTML",
    )


@router.message(Command("setmydescription"))
async def cmd_set_my_description(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not set bot description", exc)
        return
    except TelegramAPIError as exc:
        await _answer_operation_failed(message, "Could not set bot description", exc)
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
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not set bot short description", exc)
        return
    except TelegramAPIError as exc:
        await _answer_operation_failed(message, "Could not set bot short description", exc)
        return

    await message.answer(
        format_set_my_short_description_result(
            short_description=short_description,
            language_code=language_code,
        ),
        parse_mode="HTML",
    )


@router.message(Command("setmydefaultrights"))
async def cmd_set_my_default_administrator_rights(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_set_my_default_administrator_rights_args(message.text or "")
    if parsed is None:
        await message.answer(
            SET_MY_DEFAULT_ADMINISTRATOR_RIGHTS_USAGE,
            parse_mode="HTML",
        )
        return

    preset, rights, for_channels = parsed
    try:
        await perform_set_my_default_administrator_rights(
            message.bot,
            rights=rights,
            for_channels=for_channels,
        )
    except TelegramAPIError as exc:
        await _answer_operation_failed(message, "Could not set default administrator rights", exc)
        return

    await message.answer(
        format_set_my_default_administrator_rights_result(
            preset=preset,
            rights=rights,
            for_channels=for_channels,
        ),
        parse_mode="HTML",
    )


@router.message(Command("getmyname"))
async def cmd_get_my_name(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not get bot name", exc)
        return

    await message.answer(
        format_get_my_name_result(bot_name, language_code=parsed),
        parse_mode="HTML",
    )


@router.message(Command("getmydefaultrights"))
async def cmd_get_my_default_administrator_rights(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_get_my_default_administrator_rights_args(message.text or "")
    if parsed is INVALID_COMMAND_ARGS:
        await message.answer(GET_MY_DEFAULT_ADMINISTRATOR_RIGHTS_USAGE, parse_mode="HTML")
        return

    try:
        rights = await perform_get_my_default_administrator_rights(
            message.bot,
            for_channels=parsed,
        )
    except TelegramAPIError as exc:
        await _answer_operation_failed(message, "Could not get default administrator rights", exc)
        return

    await message.answer(
        format_get_my_default_administrator_rights_result(
            rights,
            for_channels=parsed,
        ),
        parse_mode="HTML",
    )


@router.message(Command("getmydescription"))
async def cmd_get_my_description(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not get bot description", exc)
        return

    await message.answer(
        format_get_my_description_result(bot_description, language_code=parsed),
        parse_mode="HTML",
    )


@router.message(Command("getmyshortdescription"))
async def cmd_get_my_short_description(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not get bot short description", exc)
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
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not delete bot commands", exc)
        return

    await message.answer(
        format_delete_my_commands_result(scope=scope, language_code=language_code),
        parse_mode="HTML",
    )


@router.message(Command("getmycommands"))
async def cmd_get_my_commands(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not get bot commands", exc)
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
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not set the chat sticker set", exc)
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
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    chat_id = _parse_delete_chat_sticker_set_args(message.text or "")
    if chat_id is None:
        await message.answer(DELETE_CHAT_STICKER_SET_USAGE, parse_mode="HTML")
        return

    try:
        await perform_delete_chat_sticker_set(message.bot, chat_id=chat_id)
    except TelegramAPIError as exc:
        await _answer_operation_failed(message, "Could not delete the chat sticker set", exc)
        return

    await message.answer(
        format_delete_chat_sticker_set_result(chat_id=chat_id),
        parse_mode="HTML",
    )


@router.message(Command("promotechatmember"))
async def cmd_promote_chat_member(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not promote the user", exc)
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
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not export the chat invite link", exc)
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
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not get chat information", exc)
        return

    await message.answer(
        format_get_chat_result(chat),
        parse_mode="HTML",
    )


@router.message(Command("getchatmembercount"))
async def cmd_get_chat_member_count(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not get chat member count", exc)
        return

    await message.answer(
        format_get_chat_member_count_result(chat_id, member_count),
        parse_mode="HTML",
    )


@router.message(Command("getchatmember"))
async def cmd_get_chat_member(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not get chat member", exc)
        return

    await message.answer(
        format_get_chat_member_result(chat_id, user_id, member),
        parse_mode="HTML",
    )


@router.message(Command("getchatadministrators"))
async def cmd_get_chat_administrators(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not get chat administrators", exc)
        return

    await message.answer(
        format_get_chat_administrators_result(chat_id, administrators),
        parse_mode="HTML",
    )


@router.message(Command("forumtopiciconstickers"))
async def cmd_forum_topic_icon_stickers(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    if (message.text or "").split()[1:]:
        await message.answer(FORUM_TOPIC_ICON_STICKERS_USAGE, parse_mode="HTML")
        return

    try:
        stickers = await perform_get_forum_topic_icon_stickers(message.bot)
    except GetForumTopicIconStickersError as exc:
        await _answer_operation_failed(message, "Could not get forum topic icon stickers", exc)
        return

    await message.answer(
        format_forum_topic_icon_stickers(stickers),
        parse_mode="HTML",
    )


@router.message(Command("getstickerset"))
async def cmd_get_sticker_set(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    name = _parse_get_sticker_set_args(message.text or "")
    if name is None:
        await message.answer(GET_STICKER_SET_USAGE, parse_mode="HTML")
        return

    try:
        sticker_set = await perform_get_sticker_set(message.bot, name=name)
    except GetStickerSetError as exc:
        await _answer_operation_failed(message, "Could not get the sticker set", exc)
        return

    await message.answer(format_sticker_set(sticker_set), parse_mode="HTML")


@router.message(Command("customemojistickers"))
async def cmd_custom_emoji_stickers(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    custom_emoji_ids = _parse_custom_emoji_stickers_args(message.text or "")
    if custom_emoji_ids is None:
        await message.answer(CUSTOM_EMOJI_STICKERS_USAGE, parse_mode="HTML")
        return

    try:
        stickers = await perform_get_custom_emoji_stickers(
            message.bot,
            custom_emoji_ids=custom_emoji_ids,
        )
    except GetCustomEmojiStickersValidationError as exc:
        await _answer_validation_failed(
            message,
            "Custom emoji sticker requests must include 1 to 200 non-empty ids.",
            exc,
        )
        return
    except GetCustomEmojiStickersError as exc:
        await _answer_operation_failed(message, "Could not get custom emoji stickers", exc)
        return

    await message.answer(format_custom_emoji_stickers(stickers), parse_mode="HTML")


@router.message(Command("uploadstickerfile"))
async def cmd_upload_sticker_file(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_upload_sticker_file_args(message.text or "")
    if parsed is None:
        await message.answer(UPLOAD_STICKER_FILE_USAGE, parse_mode="HTML")
        return

    user_id, sticker_format, sticker_path = parsed
    try:
        file = await perform_upload_sticker_file(
            message.bot,
            user_id=user_id,
            sticker_format=sticker_format,
            sticker_path=sticker_path,
        )
    except UploadStickerFileError as exc:
        await _answer_operation_failed(message, "Could not upload the sticker file", exc)
        return

    await message.answer(
        format_upload_sticker_file_result(
            user_id=user_id,
            sticker_path=sticker_path,
            sticker_format=sticker_format,
            file=file,
        ),
        parse_mode="HTML",
    )


@router.message(Command("createnewstickerset"))
async def cmd_create_new_sticker_set(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_create_new_sticker_set_args(message.text or "")
    if parsed is None:
        await message.answer(CREATE_NEW_STICKER_SET_USAGE, parse_mode="HTML")
        return

    user_id, name, sticker_type, sticker_format, sticker, emoji_list, title = parsed
    try:
        await perform_create_new_sticker_set(
            message.bot,
            user_id=user_id,
            name=name,
            title=title,
            sticker_type=sticker_type,
            sticker_format=sticker_format,
            sticker=sticker,
            emoji_list=emoji_list,
        )
    except CreateNewStickerSetError as exc:
        await _answer_operation_failed(message, "Could not create the sticker set", exc)
        return

    await message.answer(
        format_create_new_sticker_set_result(
            user_id=user_id,
            name=name,
            title=title,
            sticker_type=sticker_type,
            sticker_format=sticker_format,
            sticker=sticker,
            emoji_list=emoji_list,
        ),
        parse_mode="HTML",
    )


@router.message(Command("addstickertoset"))
async def cmd_add_sticker_to_set(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_add_sticker_to_set_args(message.text or "")
    if parsed is None:
        await message.answer(ADD_STICKER_TO_SET_USAGE, parse_mode="HTML")
        return

    user_id, name, sticker_format, sticker, emoji_list = parsed
    try:
        await perform_add_sticker_to_set(
            message.bot,
            user_id=user_id,
            name=name,
            sticker_format=sticker_format,
            sticker=sticker,
            emoji_list=emoji_list,
        )
    except AddStickerToSetError as exc:
        await _answer_operation_failed(message, "Could not add the sticker to the set", exc)
        return

    await message.answer(
        format_add_sticker_to_set_result(
            user_id=user_id,
            name=name,
            sticker_format=sticker_format,
            sticker=sticker,
            emoji_list=emoji_list,
        ),
        parse_mode="HTML",
    )


@router.message(Command("replacestickerinset"))
async def cmd_replace_sticker_in_set(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_replace_sticker_in_set_args(message.text or "")
    if parsed is None:
        await message.answer(REPLACE_STICKER_IN_SET_USAGE, parse_mode="HTML")
        return

    user_id, name, old_sticker, sticker_format, sticker, emoji_list = parsed
    try:
        await perform_replace_sticker_in_set(
            message.bot,
            user_id=user_id,
            name=name,
            old_sticker=old_sticker,
            sticker_format=sticker_format,
            sticker=sticker,
            emoji_list=emoji_list,
        )
    except ReplaceStickerInSetError as exc:
        await _answer_operation_failed(message, "Could not replace the sticker in the set", exc)
        return

    await message.answer(
        format_replace_sticker_in_set_result(
            user_id=user_id,
            name=name,
            old_sticker=old_sticker,
            sticker_format=sticker_format,
            sticker=sticker,
            emoji_list=emoji_list,
        ),
        parse_mode="HTML",
    )


@router.message(Command("setstickerposition"))
async def cmd_set_sticker_position_in_set(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_set_sticker_position_in_set_args(message.text or "")
    if parsed is None:
        await message.answer(SET_STICKER_POSITION_IN_SET_USAGE, parse_mode="HTML")
        return

    sticker, position = parsed
    try:
        await perform_set_sticker_position_in_set(
            message.bot,
            sticker=sticker,
            position=position,
        )
    except SetStickerPositionInSetError as exc:
        await _answer_operation_failed(message, "Could not set the sticker position", exc)
        return

    await message.answer(
        format_set_sticker_position_in_set_result(
            sticker=sticker,
            position=position,
        ),
        parse_mode="HTML",
    )


@router.message(Command("setstickeremojis"))
async def cmd_set_sticker_emoji_list(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_set_sticker_emoji_list_args(message.text or "")
    if parsed is None:
        await message.answer(SET_STICKER_EMOJI_LIST_USAGE, parse_mode="HTML")
        return

    sticker, emoji_list = parsed
    try:
        await perform_set_sticker_emoji_list(
            message.bot,
            sticker=sticker,
            emoji_list=emoji_list,
        )
    except SetStickerEmojiListError as exc:
        await _answer_operation_failed(message, "Could not set the sticker emoji list", exc)
        return

    await message.answer(
        format_set_sticker_emoji_list_result(
            sticker=sticker,
            emoji_list=emoji_list,
        ),
        parse_mode="HTML",
    )


@router.message(Command("setstickermaskposition"))
async def cmd_set_sticker_mask_position(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_set_sticker_mask_position_args(message.text or "")
    if parsed is None:
        await message.answer(SET_STICKER_MASK_POSITION_USAGE, parse_mode="HTML")
        return

    sticker, mask_position = parsed
    try:
        await perform_set_sticker_mask_position(
            message.bot,
            sticker=sticker,
            mask_position=mask_position,
        )
    except SetStickerMaskPositionError as exc:
        await _answer_operation_failed(message, "Could not set the sticker mask position", exc)
        return

    await message.answer(
        format_set_sticker_mask_position_result(
            sticker=sticker,
            mask_position=mask_position,
        ),
        parse_mode="HTML",
    )


@router.message(Command("setstickerkeywords"))
async def cmd_set_sticker_keywords(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_set_sticker_keywords_args(message.text or "")
    if parsed is None:
        await message.answer(SET_STICKER_KEYWORDS_USAGE, parse_mode="HTML")
        return

    sticker, keywords = parsed
    try:
        await perform_set_sticker_keywords(
            message.bot,
            sticker=sticker,
            keywords=keywords,
        )
    except SetStickerKeywordsError as exc:
        await _answer_operation_failed(message, "Could not set the sticker keywords", exc)
        return

    await message.answer(
        format_set_sticker_keywords_result(
            sticker=sticker,
            keywords=keywords,
        ),
        parse_mode="HTML",
    )


@router.message(Command("setstickersettitle"))
async def cmd_set_sticker_set_title(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_set_sticker_set_title_args(message.text or "")
    if parsed is None:
        await message.answer(SET_STICKER_SET_TITLE_USAGE, parse_mode="HTML")
        return

    name, title = parsed
    try:
        await perform_set_sticker_set_title(
            message.bot,
            name=name,
            title=title,
        )
    except SetStickerSetTitleError as exc:
        await _answer_operation_failed(message, "Could not set the sticker set title", exc)
        return

    await message.answer(
        format_set_sticker_set_title_result(
            name=name,
            title=title,
        ),
        parse_mode="HTML",
    )


@router.message(Command("setstickersetthumbnail"))
async def cmd_set_sticker_set_thumbnail(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_set_sticker_set_thumbnail_args(message.text or "")
    if parsed is None:
        await message.answer(SET_STICKER_SET_THUMBNAIL_USAGE, parse_mode="HTML")
        return

    user_id, name, sticker_format, thumbnail = parsed
    try:
        await perform_set_sticker_set_thumbnail(
            message.bot,
            user_id=user_id,
            name=name,
            sticker_format=sticker_format,
            thumbnail=thumbnail,
        )
    except SetStickerSetThumbnailError as exc:
        await _answer_operation_failed(message, "Could not set the sticker set thumbnail", exc)
        return

    await message.answer(
        format_set_sticker_set_thumbnail_result(
            user_id=user_id,
            name=name,
            sticker_format=sticker_format,
            thumbnail=thumbnail,
        ),
        parse_mode="HTML",
    )


@router.message(Command("setcustomemojithumbnail"))
async def cmd_set_custom_emoji_sticker_set_thumbnail(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_set_custom_emoji_sticker_set_thumbnail_args(message.text or "")
    if parsed is None:
        await message.answer(
            SET_CUSTOM_EMOJI_STICKER_SET_THUMBNAIL_USAGE,
            parse_mode="HTML",
        )
        return

    name, custom_emoji_id = parsed
    try:
        await perform_set_custom_emoji_sticker_set_thumbnail(
            message.bot,
            name=name,
            custom_emoji_id=custom_emoji_id,
        )
    except SetCustomEmojiStickerSetThumbnailError as exc:
        await _answer_operation_failed(
            message,
            "Could not set the custom emoji sticker set thumbnail",
            exc,
        )
        return

    await message.answer(
        format_set_custom_emoji_sticker_set_thumbnail_result(
            name=name,
            custom_emoji_id=custom_emoji_id,
        ),
        parse_mode="HTML",
    )


@router.message(Command("deletestickerfromset"))
async def cmd_delete_sticker_from_set(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    sticker = _parse_delete_sticker_from_set_args(message.text or "")
    if sticker is None:
        await message.answer(DELETE_STICKER_FROM_SET_USAGE, parse_mode="HTML")
        return

    try:
        await perform_delete_sticker_from_set(message.bot, sticker=sticker)
    except DeleteStickerFromSetError as exc:
        await _answer_operation_failed(message, "Could not delete the sticker from its set", exc)
        return

    await message.answer(
        format_delete_sticker_from_set_result(sticker=sticker),
        parse_mode="HTML",
    )


@router.message(Command("deletestickerset"))
async def cmd_delete_sticker_set(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    name = _parse_delete_sticker_set_args(message.text or "")
    if name is None:
        await message.answer(DELETE_STICKER_SET_USAGE, parse_mode="HTML")
        return

    try:
        await perform_delete_sticker_set(message.bot, name=name)
    except DeleteStickerSetError as exc:
        await _answer_operation_failed(message, "Could not delete the sticker set", exc)
        return

    await message.answer(
        format_delete_sticker_set_result(name=name),
        parse_mode="HTML",
    )


@router.message(Command("editforumtopic"))
async def cmd_edit_forum_topic(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not edit forum topic", exc)
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
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not edit General forum topic", exc)
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
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not create forum topic", exc)
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
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not close forum topic", exc)
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
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not close General forum topic", exc)
        return

    await message.answer(
        format_close_general_forum_topic_result(chat_id=chat_id),
        parse_mode="HTML",
    )


@router.message(Command("reopenforumtopic"))
async def cmd_reopen_forum_topic(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not reopen forum topic", exc)
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
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not reopen General forum topic", exc)
        return

    await message.answer(
        format_reopen_general_forum_topic_result(chat_id=chat_id),
        parse_mode="HTML",
    )


@router.message(Command("hidegeneralforumtopic"))
async def cmd_hide_general_forum_topic(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not hide General forum topic", exc)
        return

    await message.answer(
        format_hide_general_forum_topic_result(chat_id=chat_id),
        parse_mode="HTML",
    )


@router.message(Command("unhidegeneralforumtopic"))
async def cmd_unhide_general_forum_topic(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not unhide General forum topic", exc)
        return

    await message.answer(
        format_unhide_general_forum_topic_result(chat_id=chat_id),
        parse_mode="HTML",
    )


@router.message(Command("deleteforumtopic"))
async def cmd_delete_forum_topic(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not delete forum topic", exc)
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
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not unpin all forum topic messages", exc)
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
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(
            message,
            "Could not unpin all General forum topic messages",
            exc,
        )
        return

    await message.answer(
        format_unpin_all_general_forum_topic_messages_result(chat_id=chat_id),
        parse_mode="HTML",
    )


@router.message(Command("userpersonalchatmessages"))
async def cmd_get_user_personal_chat_messages(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not get user personal chat messages", exc)
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
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not get user chat boosts", exc)
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
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not leave the chat", exc)
        return

    await message.answer(
        format_leave_chat_result(chat_id=chat_id),
        parse_mode="HTML",
    )


@router.message(Command("answerjoinrequestquery"))
async def cmd_answer_chat_join_request_query(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_answer_chat_join_request_query_args(message.text or "")
    if parsed is None:
        await message.answer(ANSWER_CHAT_JOIN_REQUEST_QUERY_USAGE, parse_mode="HTML")
        return

    chat_join_request_query_id, result = parsed
    try:
        await perform_answer_chat_join_request_query(
            message.bot,
            chat_join_request_query_id=chat_join_request_query_id,
            result=result,
        )
    except AnswerChatJoinRequestQueryError as exc:
        await _answer_operation_failed(
            message,
            "Could not answer the chat join request query",
            exc,
        )
        return

    await message.answer(f"Answered chat join request query with {result}.")


@router.message(Command("joinrequestwebapp"))
async def cmd_send_chat_join_request_web_app(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_send_chat_join_request_web_app_args(message.text or "")
    if parsed is None:
        await message.answer(SEND_CHAT_JOIN_REQUEST_WEB_APP_USAGE, parse_mode="HTML")
        return

    chat_join_request_query_id, web_app_url = parsed
    try:
        await perform_send_chat_join_request_web_app(
            message.bot,
            chat_join_request_query_id=chat_join_request_query_id,
            web_app_url=web_app_url,
        )
    except SendChatJoinRequestWebAppError as exc:
        await _answer_operation_failed(
            message,
            "Could not send the chat join request Mini App",
            exc,
        )
        return

    await message.answer("Sent chat join request Mini App.")


@router.message(Command("approvechatjoinrequest"))
async def cmd_approve_chat_join_request(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not approve the chat join request", exc)
        return

    await message.answer(
        format_approve_chat_join_request_result(chat_id=chat_id, user_id=user_id),
        parse_mode="HTML",
    )


@router.message(Command("declinechatjoinrequest"))
async def cmd_decline_chat_join_request(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not decline the chat join request", exc)
        return

    await message.answer(
        format_decline_chat_join_request_result(chat_id=chat_id, user_id=user_id),
        parse_mode="HTML",
    )


@router.message(Command("createchatinvitelink"))
async def cmd_create_chat_invite_link(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not create the chat invite link", exc)
        return

    await message.answer(
        format_create_chat_invite_link_result(chat_id=chat_id, link=link),
        parse_mode="HTML",
    )


@router.message(Command("editchatinvitelink"))
async def cmd_edit_chat_invite_link(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not edit the chat invite link", exc)
        return

    await message.answer(
        format_edit_chat_invite_link_result(chat_id=chat_id, link=link),
        parse_mode="HTML",
    )


@router.message(Command("revokechatinvitelink"))
async def cmd_revoke_chat_invite_link(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not revoke the chat invite link", exc)
        return

    await message.answer(
        format_revoke_chat_invite_link_result(chat_id=chat_id, link=link),
        parse_mode="HTML",
    )


@router.message(Command("createchatsubscriptioninvitelink"))
async def cmd_create_chat_subscription_invite_link(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(
            message,
            "Could not create the chat subscription invite link",
            exc,
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
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(
            message,
            "Could not edit the chat subscription invite link",
            exc,
        )
        return

    await message.answer(
        format_edit_chat_subscription_invite_link_result(chat_id=chat_id, link=link),
        parse_mode="HTML",
    )


@router.message(Command("setchatadministratortitle"))
async def cmd_set_chat_administrator_custom_title(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not set the administrator custom title", exc)
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
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not set the member tag", exc)
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
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not set the reaction", exc)
        return

    if emoji is not None:
        await message.answer(f"Set reaction {emoji} on message {message_id}.")
    else:
        await message.answer(f"Removed reactions from message {message_id}.")


@router.message(Command("deletereaction"))
async def cmd_delete_message_reaction(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_delete_message_reaction_args(message.text or "")
    if parsed is None:
        await message.answer(DELETE_MESSAGE_REACTION_USAGE, parse_mode="HTML")
        return

    chat_id, message_id, user_id = parsed

    try:
        await perform_delete_message_reaction(
            message.bot,
            chat_id=chat_id,
            message_id=message_id,
            user_id=user_id,
        )
    except TelegramAPIError as exc:
        await _answer_operation_failed(message, "Could not delete the message reaction", exc)
        return

    await message.answer(
        format_delete_message_reaction_result(
            chat_id=chat_id,
            message_id=message_id,
            user_id=user_id,
        ),
        parse_mode="HTML",
    )


@router.message(Command("deleteallreactions"))
async def cmd_delete_all_message_reactions(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
        await message.answer("This command is restricted to admin chats.")
        return

    parsed = _parse_delete_all_message_reactions_args(message.text or "")
    if parsed is None:
        await message.answer(DELETE_ALL_MESSAGE_REACTIONS_USAGE, parse_mode="HTML")
        return

    chat_id, message_id = parsed

    try:
        await perform_delete_all_message_reactions(
            message.bot,
            chat_id=chat_id,
            message_id=message_id,
        )
    except DeleteAllMessageReactionsError as exc:
        await _answer_operation_failed(message, "Could not delete all message reactions", exc)
        return

    await message.answer(
        format_delete_all_message_reactions_result(
            chat_id=chat_id,
            message_id=message_id,
        ),
        parse_mode="HTML",
    )


@router.message(Command("setemojistatus"))
async def cmd_set_emoji_status(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not set the emoji status", exc)
        return

    if custom_emoji_id:
        await message.answer(
            f"Set emoji status {custom_emoji_id!r} for user {user_id}."
        )
    else:
        await message.answer(f"Removed emoji status for user {user_id}.")


@router.message(Command("mediagroup"))
async def cmd_media_group(message: Message):
    if not _is_admin_action_allowed(message.chat.id, _message_user_id(message)):
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
        await _answer_operation_failed(message, "Could not send the media group", exc)
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


def _message_user_id(message: Message) -> int | None:
    from_user = getattr(message, "from_user", None)
    return getattr(from_user, "id", None)


def _is_admin_or_allowed_chat(chat_id: int, user_id: int | None = None) -> bool:
    return check_admin_or_allowed_chat(
        chat_id=chat_id,
        user_id=user_id,
        admin_chat_ids=settings.admin_chat_ids,
        allowed_chat_ids=settings.allowed_chat_ids,
        admin_user_ids=settings.admin_user_ids,
    )


def _is_admin_action_allowed(chat_id: int, user_id: int | None = None) -> bool:
    return check_admin_action_allowed(
        chat_id=chat_id,
        user_id=user_id,
        admin_chat_ids=settings.admin_chat_ids,
        admin_user_ids=settings.admin_user_ids,
    )


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


def _parse_sticker_args(text: str):
    """Parse ``/sticker`` arguments into ``(sticker, emoji)``.

    Splits the raw command text into the command, the sticker reference (URL or
    ``file_id``) and an optional emoji hint passed through to Telegram. Returns
    ``None`` when no sticker reference is provided so the caller can show usage.
    """
    parts = (text or "").split(maxsplit=2)
    if len(parts) < 2:
        return None

    sticker = parts[1].strip()
    if not sticker:
        return None

    emoji = parts[2].strip() if len(parts) >= 3 else None
    if emoji == "":
        emoji = None

    return sticker, emoji


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


def _parse_send_invoice_args(text: str):
    """Parse ``/sendinvoice`` args into star count, payload, title, description."""
    parts = (text or "").split(maxsplit=3)
    if len(parts) < 4:
        return None

    try:
        star_count = int(parts[1].strip())
    except ValueError:
        return None

    payload = parts[2].strip()
    invoice_text = parts[3].strip()
    if not payload or " | " not in invoice_text:
        return None

    title, description = [part.strip() for part in invoice_text.split(" | ", 1)]
    if not title or not description:
        return None

    return star_count, payload, title, description


def _parse_create_invoice_link_args(text: str):
    """Parse ``/createinvoicelink`` args."""
    return _parse_send_invoice_args(text)


def _validate_send_invoice_args(
    *, star_count: int, payload: str, title: str, description: str
) -> str | None:
    if not INVOICE_MIN_STARS <= star_count <= INVOICE_MAX_STARS:
        return (
            f"Star count must be between {INVOICE_MIN_STARS} and "
            f"{INVOICE_MAX_STARS}."
        )
    if len(payload.encode("utf-8")) > INVOICE_PAYLOAD_LIMIT:
        return f"Payload is too long: max {INVOICE_PAYLOAD_LIMIT} bytes."
    if len(title) > INVOICE_TITLE_LIMIT:
        return f"Title is too long: {len(title)} characters (max {INVOICE_TITLE_LIMIT})."
    if len(description) > INVOICE_DESCRIPTION_LIMIT:
        return (
            f"Description is too long: {len(description)} characters "
            f"(max {INVOICE_DESCRIPTION_LIMIT})."
        )
    return None


def _validate_create_invoice_link_args(
    *, star_count: int, payload: str, title: str, description: str
) -> str | None:
    return _validate_send_invoice_args(
        star_count=star_count,
        payload=payload,
        title=title,
        description=description,
    )


def _parse_answer_web_app_query_args(text: str):
    """Parse ``/answerwebappquery`` args into query id and result JSON."""
    parts = (text or "").split(maxsplit=2)
    if len(parts) != 3:
        return None

    web_app_query_id = parts[1].strip()
    if not web_app_query_id:
        return None

    try:
        result = json.loads(parts[2])
    except json.JSONDecodeError:
        return None

    if not isinstance(result, dict) or not result:
        return None

    return web_app_query_id, result


def _parse_save_prepared_inline_message_args(text: str):
    """Parse ``/savepreparedinline`` args into user id, result JSON and flags."""
    parts = (text or "").split(maxsplit=3)
    if len(parts) < 3:
        return None

    try:
        user_id = int(parts[1])
    except ValueError:
        return None
    if user_id <= 0:
        return None

    json_and_flags = parts[2] if len(parts) == 3 else f"{parts[2]} {parts[3]}"
    decoder = json.JSONDecoder()
    try:
        result, end_index = decoder.raw_decode(json_and_flags)
    except json.JSONDecodeError:
        return None

    if not isinstance(result, dict) or not result:
        return None

    options = {}
    flags_text = json_and_flags[end_index:].strip()
    allowed_flags = {
        "allow_user_chats",
        "allow_bot_chats",
        "allow_group_chats",
        "allow_channel_chats",
    }
    for token in flags_text.split():
        if "=" not in token:
            return None
        name, value = token.split("=", 1)
        if name not in allowed_flags:
            return None
        normalized_value = value.lower()
        if normalized_value not in {"true", "false"}:
            return None
        options[name] = normalized_value == "true"

    return user_id, result, options


def _parse_set_passport_data_errors_args(text: str):
    """Parse ``/setpassporterrors`` args into user id and errors JSON array."""
    parts = (text or "").split(maxsplit=2)
    if len(parts) != 3:
        return None

    try:
        user_id = int(parts[1])
    except ValueError:
        return None
    if user_id <= 0:
        return None

    try:
        errors = json.loads(parts[2])
    except json.JSONDecodeError:
        return None

    if not isinstance(errors, list) or not errors:
        return None
    if not all(isinstance(error, dict) and error for error in errors):
        return None

    return user_id, errors


def _parse_save_prepared_keyboard_button_args(text: str):
    """Parse ``/savepreparedkeyboard`` args into user id and prepared message id."""
    parts = (text or "").split(maxsplit=2)
    if len(parts) != 3:
        return None

    try:
        user_id = int(parts[1])
    except ValueError:
        return None
    if user_id <= 0:
        return None

    prepared_message_id = parts[2].strip()
    if not prepared_message_id:
        return None

    return user_id, prepared_message_id


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


def _parse_poll_option(segment: str):
    if POLL_OPTION_LINK_SEPARATOR not in segment:
        return segment.strip()

    option_text, _, raw_url = segment.partition(POLL_OPTION_LINK_SEPARATOR)
    option_text = option_text.strip()
    url = raw_url.strip()
    if not option_text or not url.startswith(("http://", "https://")):
        return None

    return {
        "text": option_text,
        "media": {
            "type": "link",
            "url": url,
        },
    }


def _parse_poll_args(text: str):
    """Parse ``/poll`` args into ``(question, options)``.

    Splits the raw command text into the command and the remainder, then splits
    the remainder on the vertical bar (``|``) so the first segment is the poll
    ``question`` and the following segments are the answer ``options``. Every
    plain segment is trimmed of surrounding whitespace but keeps any internal
    spaces. Option segments may use ``Option => https://example.com`` to attach
    Bot API 10.1 ``InputMediaLink`` media to that option.
    Returns ``None`` when there are no arguments, when the separator is missing
    so no option is given, or when the question or any option is empty, so the
    caller can show usage. The caller validates the question/option lengths and
    the 1-12 option count against Telegram's limits.
    """
    parts = (text or "").split(maxsplit=1)
    if len(parts) < 2:
        return None

    segments = [segment.strip() for segment in parts[1].split(POLL_OPTION_SEPARATOR)]
    question = segments[0]
    options = [_parse_poll_option(segment) for segment in segments[1:]]
    if not question or not options:
        return None

    if any(option is None or not option for option in options):
        return None

    return question, options


def _parse_stop_poll_args(text: str):
    parts = (text or "").split()
    if len(parts) != 3:
        return None

    raw_chat_id, raw_message_id = parts[1], parts[2]
    try:
        message_id = int(raw_message_id)
    except ValueError:
        return None

    if message_id <= 0:
        return None

    if raw_chat_id.startswith("@"):
        chat_id: int | str = raw_chat_id
    else:
        try:
            chat_id = int(raw_chat_id)
        except ValueError:
            return None

    return chat_id, message_id


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


def _parse_game_args(text: str):
    """Parse ``/game`` args into a single-element ``(game_short_name,)`` tuple."""
    parts = (text or "").split()
    if len(parts) != 2:
        return None

    game_short_name = parts[1].strip()
    if not game_short_name:
        return None

    return (game_short_name,)


def _parse_bool_option(value: str):
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes", "on"}:
        return True
    if normalized in {"false", "0", "no", "off"}:
        return False
    return None


def _parse_set_game_score_args(text: str):
    """Parse ``/setgamescore`` args into kwargs for ``perform_set_game_score``."""
    parts = (text or "").split()
    if len(parts) < 4:
        return None

    try:
        user_id = int(parts[1])
        score = int(parts[2])
    except ValueError:
        return None

    kwargs = {
        "user_id": user_id,
        "score": score,
        "chat_id": None,
        "message_id": None,
        "inline_message_id": None,
        "force": None,
        "disable_edit_message": None,
    }
    allowed_keys = {
        "chat_id",
        "message_id",
        "inline_message_id",
        "force",
        "disable_edit_message",
    }
    seen = set()
    for raw_part in parts[3:]:
        if "=" not in raw_part:
            return None
        key, value = raw_part.split("=", 1)
        if key not in allowed_keys or key in seen or value == "":
            return None
        seen.add(key)
        if key in {"chat_id", "message_id"}:
            try:
                kwargs[key] = int(value)
            except ValueError:
                return None
        elif key in {"force", "disable_edit_message"}:
            parsed_bool = _parse_bool_option(value)
            if parsed_bool is None:
                return None
            kwargs[key] = parsed_bool
        else:
            kwargs[key] = value

    has_chat_message = kwargs["chat_id"] is not None or kwargs["message_id"] is not None
    has_inline_message = kwargs["inline_message_id"] is not None
    if has_chat_message == has_inline_message:
        return None
    if has_chat_message and (kwargs["chat_id"] is None or kwargs["message_id"] is None):
        return None

    return kwargs


def _parse_get_game_high_scores_args(text: str):
    """Parse ``/gamehighscores`` args for ``perform_get_game_high_scores``."""
    parts = (text or "").split()
    if len(parts) < 3:
        return None

    try:
        user_id = int(parts[1])
    except ValueError:
        return None

    kwargs = {
        "user_id": user_id,
        "chat_id": None,
        "message_id": None,
        "inline_message_id": None,
    }
    allowed_keys = {"chat_id", "message_id", "inline_message_id"}
    seen = set()
    for raw_part in parts[2:]:
        if "=" not in raw_part:
            return None
        key, value = raw_part.split("=", 1)
        if key not in allowed_keys or key in seen or value == "":
            return None
        seen.add(key)
        if key in {"chat_id", "message_id"}:
            try:
                kwargs[key] = int(value)
            except ValueError:
                return None
        else:
            kwargs[key] = value

    has_chat_message = kwargs["chat_id"] is not None or kwargs["message_id"] is not None
    has_inline_message = kwargs["inline_message_id"] is not None
    if has_chat_message == has_inline_message:
        return None
    if has_chat_message and (kwargs["chat_id"] is None or kwargs["message_id"] is None):
        return None

    return kwargs


def _format_game_high_scores(scores) -> str:
    if not scores:
        return "No game high scores returned."

    lines = ["Game high scores:"]
    for index, score in enumerate(scores, start=1):
        position = getattr(score, "position", index)
        user = getattr(score, "user", None)
        user_id = getattr(user, "id", "unknown")
        value = getattr(score, "score", "unknown")
        lines.append(f"{position}. user_id={user_id} score={value}")
    return "\n".join(lines)


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


def _is_valid_rich_message_payload(value) -> bool:
    if not isinstance(value, dict) or not value:
        return False

    has_html = "html" in value
    has_markdown = "markdown" in value
    if has_html == has_markdown:
        return False

    content_key = "html" if has_html else "markdown"
    content = value.get(content_key)
    if not isinstance(content, str) or not content:
        return False

    if "is_rtl" in value and not isinstance(value["is_rtl"], bool):
        return False

    if "skip_entity_detection" in value and not isinstance(
        value["skip_entity_detection"], bool
    ):
        return False

    return True


def _parse_rich_message_args(text: str):
    """Parse ``/richmessage`` args into an ``InputRichMessage`` dict."""
    parts = (text or "").split(maxsplit=1)
    if len(parts) != 2:
        return None

    try:
        rich_message = json.loads(parts[1])
    except json.JSONDecodeError:
        return None

    if not _is_valid_rich_message_payload(rich_message):
        return None

    return rich_message


def _parse_rich_message_draft_args(text: str):
    """Parse ``/richmessagedraft`` args into ``(draft_id, InputRichMessage)``."""
    parts = (text or "").split(maxsplit=2)
    if len(parts) != 3:
        return None

    try:
        draft_id = int(parts[1])
    except ValueError:
        return None

    if draft_id == 0:
        return None

    try:
        rich_message = json.loads(parts[2])
    except json.JSONDecodeError:
        return None

    if not _is_valid_rich_message_payload(rich_message):
        return None

    return draft_id, rich_message


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


def _parse_edit_checklist_args(text: str):
    """Parse ``/editchecklist`` args into business id, target and checklist."""
    parts = (text or "").split(maxsplit=4)
    if len(parts) < 5:
        return None

    business_connection_id = parts[1].strip()
    try:
        chat_id = int(parts[2])
        message_id = int(parts[3])
    except ValueError:
        return None

    if not business_connection_id or message_id <= 0:
        return None

    segments = [segment.strip() for segment in parts[4].split(CHECKLIST_TASK_SEPARATOR)]
    title = segments[0]
    tasks = segments[1:]
    if not title or not tasks:
        return None
    if any(not task for task in tasks):
        return None

    return business_connection_id, chat_id, message_id, title, tasks


def _parse_post_story_args(text: str):
    """Parse ``/poststory`` args into business id, active period, photo, caption."""
    parts = (text or "").split(maxsplit=4)
    if len(parts) < 4:
        return None

    business_connection_id = parts[1].strip()
    active_period_raw = parts[2].strip()
    photo = parts[3].strip()
    if not business_connection_id or not active_period_raw or not photo:
        return None

    try:
        active_period = int(active_period_raw)
    except ValueError:
        return None

    caption = parts[4].strip() if len(parts) >= 5 else None
    if caption == "":
        caption = None

    return business_connection_id, active_period, photo, caption


def _parse_repost_story_args(text: str):
    """Parse ``/repoststory`` args into business id, source story and period."""
    parts = (text or "").split(maxsplit=4)
    if len(parts) != 5:
        return None

    business_connection_id = parts[1].strip()
    if not business_connection_id:
        return None

    try:
        from_chat_id = int(parts[2].strip())
        from_story_id = int(parts[3].strip())
        active_period = int(parts[4].strip())
    except ValueError:
        return None

    if from_chat_id == 0 or from_story_id <= 0:
        return None

    return business_connection_id, from_chat_id, from_story_id, active_period


def _parse_edit_story_args(text: str):
    """Parse ``/editstory`` args into business id, story id, photo and caption."""
    parts = (text or "").split(maxsplit=4)
    if len(parts) < 4:
        return None

    business_connection_id = parts[1].strip()
    photo = parts[3].strip()
    if not business_connection_id or not photo:
        return None

    try:
        story_id = int(parts[2].strip())
    except ValueError:
        return None

    if story_id <= 0:
        return None

    caption = parts[4].strip() if len(parts) >= 5 else None
    if caption == "":
        caption = None

    return business_connection_id, story_id, photo, caption


def _parse_edit_message_caption_args(text: str):
    """Parse ``/editcaption`` args into target, caption and raw API options."""
    parts = (text or "").split(maxsplit=3)
    if len(parts) < 2:
        return None

    target: dict[str, object]
    caption_index: int
    if parts[1].startswith("inline="):
        inline_message_id = parts[1].split("=", maxsplit=1)[1].strip()
        if not inline_message_id:
            return None
        target = {"inline_message_id": inline_message_id}
        caption_index = 2
    else:
        if len(parts) < 3:
            return None
        try:
            chat_id = int(parts[1])
            message_id = int(parts[2])
        except ValueError:
            return None
        if message_id <= 0:
            return None
        target = {"chat_id": chat_id, "message_id": message_id}
        caption_index = 3

    raw_caption = parts[caption_index].strip() if len(parts) > caption_index else ""
    caption_tokens = raw_caption.split()
    options: dict[str, object] = {}
    kept_tokens: list[str] = []
    for token in caption_tokens:
        lower = token.lower()
        if lower.startswith("parse_mode="):
            parse_mode = token.split("=", maxsplit=1)[1].strip()
            if not parse_mode:
                return None
            options["parse_mode"] = parse_mode
        elif lower in {"above=true", "show_caption_above_media=true"}:
            options["show_caption_above_media"] = True
        elif lower in {"above=false", "show_caption_above_media=false"}:
            options["show_caption_above_media"] = False
        else:
            kept_tokens.append(token)

    caption = " ".join(kept_tokens).strip() or None
    return target, caption, options


def _parse_edit_message_media_args(text: str):
    """Parse ``/editmedia`` args into target, media descriptor and raw API options."""
    parts = (text or "").split(maxsplit=5)
    if len(parts) < 4:
        return None

    target: dict[str, object]
    media_type_index: int
    if parts[1].startswith("inline="):
        inline_message_id = parts[1].split("=", maxsplit=1)[1].strip()
        if not inline_message_id:
            return None
        target = {"inline_message_id": inline_message_id}
        media_type_index = 2
    else:
        if len(parts) < 5:
            return None
        try:
            chat_id = int(parts[1])
            message_id = int(parts[2])
        except ValueError:
            return None
        if message_id <= 0:
            return None
        target = {"chat_id": chat_id, "message_id": message_id}
        media_type_index = 3

    media_type = parts[media_type_index].strip().lower()
    media = parts[media_type_index + 1].strip()
    if media_type not in EDIT_MESSAGE_MEDIA_TYPES or not media:
        return None

    raw_caption = (
        parts[media_type_index + 2].strip()
        if len(parts) > media_type_index + 2
        else ""
    )
    caption_tokens = raw_caption.split()
    options: dict[str, object] = {}
    kept_tokens: list[str] = []
    for token in caption_tokens:
        lower = token.lower()
        if lower.startswith("parse_mode="):
            parse_mode = token.split("=", maxsplit=1)[1].strip()
            if not parse_mode:
                return None
            options["parse_mode"] = parse_mode
        elif lower in {"above=true", "show_caption_above_media=true"}:
            options["show_caption_above_media"] = True
        elif lower in {"above=false", "show_caption_above_media=false"}:
            options["show_caption_above_media"] = False
        elif lower in {"spoiler=true", "has_spoiler=true"}:
            options["has_spoiler"] = True
        elif lower in {"spoiler=false", "has_spoiler=false"}:
            options["has_spoiler"] = False
        else:
            kept_tokens.append(token)

    caption = " ".join(kept_tokens).strip() or None
    return target, media_type, media, caption, options


def _parse_edit_message_reply_markup_args(text: str):
    """Parse ``/editreplymarkup`` args into target and raw reply markup."""
    parts = (text or "").split()
    if len(parts) < 2:
        return None

    target: dict[str, object]
    action_index: int
    if parts[1].startswith("inline="):
        inline_message_id = parts[1].split("=", maxsplit=1)[1].strip()
        if not inline_message_id:
            return None
        target = {"inline_message_id": inline_message_id}
        action_index = 2
    else:
        if len(parts) < 3:
            return None
        try:
            chat_id = int(parts[1])
            message_id = int(parts[2])
        except ValueError:
            return None
        if message_id <= 0:
            return None
        target = {"chat_id": chat_id, "message_id": message_id}
        action_index = 3

    if len(parts) <= action_index or parts[action_index].lower() == "clear":
        return target, None
    if parts[action_index].lower() == "empty":
        return target, {"inline_keyboard": []}
    return None


def _parse_edit_message_live_location_args(text: str):
    """Parse ``/editlivelocation`` args into target, coordinates and options."""
    parts = (text or "").split()
    if len(parts) < 4:
        return None

    target: dict[str, object]
    latitude_index: int
    if parts[1].startswith("inline="):
        inline_message_id = parts[1].split("=", maxsplit=1)[1].strip()
        if not inline_message_id:
            return None
        target = {"inline_message_id": inline_message_id}
        latitude_index = 2
    else:
        if len(parts) < 5:
            return None
        try:
            chat_id = int(parts[1])
            message_id = int(parts[2])
        except ValueError:
            return None
        if message_id <= 0:
            return None
        target = {"chat_id": chat_id, "message_id": message_id}
        latitude_index = 3

    try:
        latitude = float(parts[latitude_index])
        longitude = float(parts[latitude_index + 1])
    except (IndexError, ValueError):
        return None

    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        return None

    options: dict[str, object] = {}
    for token in parts[latitude_index + 2 :]:
        lower = token.lower()
        if lower.startswith("accuracy="):
            try:
                accuracy = float(token.split("=", maxsplit=1)[1])
            except ValueError:
                return None
            if not 0 <= accuracy <= 1500:
                return None
            options["horizontal_accuracy"] = accuracy
        elif lower.startswith("heading="):
            try:
                heading = int(token.split("=", maxsplit=1)[1])
            except ValueError:
                return None
            if not 1 <= heading <= 360:
                return None
            options["heading"] = heading
        elif lower.startswith("proximity=") or lower.startswith(
            "proximity_alert_radius="
        ):
            try:
                radius = int(token.split("=", maxsplit=1)[1])
            except ValueError:
                return None
            if not 1 <= radius <= 100000:
                return None
            options["proximity_alert_radius"] = radius
        else:
            return None

    return target, latitude, longitude, options


def _parse_message_management_target_args(text: str):
    """Parse command args into a regular or inline message target."""
    parts = (text or "").split()
    if len(parts) < 2:
        return None

    if parts[1].startswith("inline="):
        if len(parts) != 2:
            return None
        inline_message_id = parts[1].split("=", maxsplit=1)[1].strip()
        if not inline_message_id:
            return None
        return {"inline_message_id": inline_message_id}

    if len(parts) != 3:
        return None
    try:
        chat_id = int(parts[1])
        message_id = int(parts[2])
    except ValueError:
        return None
    if message_id <= 0:
        return None
    return {"chat_id": chat_id, "message_id": message_id}


def _parse_approve_suggested_post_args(
    text: str,
) -> tuple[int | str, int, int | None] | None:
    """Parse ``/approvesuggestedpost`` args into chat id, message id and date."""
    parts = (text or "").split()
    if len(parts) not in (3, 4):
        return None

    raw_chat_id = parts[1].strip()
    if not raw_chat_id:
        return None
    try:
        chat_id: int | str = int(raw_chat_id)
    except ValueError:
        if not raw_chat_id.startswith("@"):
            return None
        chat_id = raw_chat_id

    try:
        message_id = int(parts[2])
    except ValueError:
        return None
    if message_id <= 0:
        return None

    send_date = None
    if len(parts) == 4:
        try:
            send_date = int(parts[3])
        except ValueError:
            return None
        if send_date <= 0:
            return None

    return chat_id, message_id, send_date


def _parse_decline_suggested_post_args(
    text: str,
) -> tuple[int | str, int, str | None] | None:
    """Parse ``/declinesuggestedpost`` args into chat id, message id and comment."""
    parts = (text or "").split(maxsplit=3)
    if len(parts) not in (3, 4):
        return None

    raw_chat_id = parts[1].strip()
    if not raw_chat_id:
        return None
    try:
        chat_id: int | str = int(raw_chat_id)
    except ValueError:
        if not raw_chat_id.startswith("@"):
            return None
        chat_id = raw_chat_id

    try:
        message_id = int(parts[2])
    except ValueError:
        return None
    if message_id <= 0:
        return None

    comment = None
    if len(parts) == 4:
        comment = parts[3].strip()
        if len(comment) > DECLINE_SUGGESTED_POST_COMMENT_LIMIT:
            return None

    return chat_id, message_id, comment


def _parse_delete_story_args(text: str):
    """Parse ``/deletestory`` args into business id and story id."""
    parts = (text or "").split()
    if len(parts) != 3:
        return None

    business_connection_id = parts[1].strip()
    if not business_connection_id:
        return None

    try:
        story_id = int(parts[2].strip())
    except ValueError:
        return None

    if story_id <= 0:
        return None

    return business_connection_id, story_id


def _parse_business_connection_args(text: str) -> str | None:
    """Parse ``/businessconnection`` args into ``business_connection_id``."""
    parts = (text or "").split()
    if len(parts) != 2:
        return None

    business_connection_id = parts[1].strip()
    return business_connection_id or None


def _parse_get_business_account_star_balance_args(text: str) -> str | None:
    """Parse ``/businessstarbalance`` args into ``business_connection_id``."""
    parts = (text or "").split()
    if len(parts) != 2:
        return None

    business_connection_id = parts[1].strip()
    return business_connection_id or None


def _parse_get_my_star_balance_args(text: str) -> bool:
    """Parse ``/mystarbalance`` args."""
    return len((text or "").split()) == 1


def _parse_get_star_transactions_args(text: str) -> dict[str, int | None] | None:
    """Parse ``/startransactions`` optional pagination args."""
    parts = (text or "").split()
    if not parts:
        return None

    parsed: dict[str, int | None] = {"offset": None, "limit": None}
    for token in parts[1:]:
        if "=" not in token:
            return None
        key, value = token.split("=", 1)
        if key not in {"offset", "limit"} or not value:
            return None
        try:
            number = int(value)
        except ValueError:
            return None
        if key == "offset":
            if number < 0:
                return None
            parsed["offset"] = number
        else:
            if not (
                GET_STAR_TRANSACTIONS_MIN_LIMIT
                <= number
                <= GET_STAR_TRANSACTIONS_MAX_LIMIT
            ):
                return None
            parsed["limit"] = number
    return parsed


def _parse_get_business_account_gifts_args(
    text: str,
) -> tuple[str, dict[str, bool | str | int]] | None:
    """Parse ``/businessgifts`` args into connection id and optional filters."""
    parts = (text or "").split()
    if len(parts) < 2:
        return None

    business_connection_id = parts[1].strip()
    if not business_connection_id:
        return None

    bool_keys = {
        "exclude_unsaved",
        "exclude_saved",
        "exclude_unlimited",
        "exclude_limited",
        "exclude_unique",
        "sort_by_price",
    }
    options: dict[str, bool | str | int] = {}
    for option in parts[2:]:
        if "=" not in option:
            return None
        key, value = option.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key in bool_keys:
            parsed_value = _parse_bool_option(value)
            if parsed_value is None:
                return None
            options[key] = parsed_value
        elif key == "offset":
            if not value:
                return None
            options[key] = value
        elif key == "limit":
            try:
                limit = int(value)
            except ValueError:
                return None
            if not (
                GET_BUSINESS_ACCOUNT_GIFTS_MIN_LIMIT
                <= limit
                <= GET_BUSINESS_ACCOUNT_GIFTS_MAX_LIMIT
            ):
                return None
            options[key] = limit
        else:
            return None

    return business_connection_id, options


def _parse_get_user_gifts_args(
    text: str,
) -> tuple[int, dict[str, bool | str | int]] | None:
    """Parse ``/usergifts`` args into user id and optional filters."""
    parts = (text or "").split()
    if len(parts) < 2:
        return None

    try:
        user_id = int(parts[1])
    except ValueError:
        return None
    if user_id <= 0:
        return None

    bool_keys = {
        "exclude_unsaved",
        "exclude_saved",
        "exclude_unlimited",
        "exclude_limited",
        "exclude_unique",
        "sort_by_price",
    }
    options: dict[str, bool | str | int] = {}
    for option in parts[2:]:
        if "=" not in option:
            return None
        key, value = option.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key in bool_keys:
            parsed_value = _parse_bool_option(value)
            if parsed_value is None:
                return None
            options[key] = parsed_value
        elif key == "offset":
            if not value:
                return None
            options[key] = value
        elif key == "limit":
            try:
                limit = int(value)
            except ValueError:
                return None
            if not (GET_USER_GIFTS_MIN_LIMIT <= limit <= GET_USER_GIFTS_MAX_LIMIT):
                return None
            options[key] = limit
        else:
            return None

    return user_id, options


def _parse_get_chat_gifts_args(
    text: str,
) -> tuple[int | str, dict[str, bool | str | int]] | None:
    """Parse ``/chatgifts`` args into chat id and optional filters."""
    parts = (text or "").split()
    if len(parts) < 2:
        return None

    chat_id_raw = parts[1].strip()
    if not chat_id_raw:
        return None

    if chat_id_raw.startswith("@"):
        chat_id: int | str = chat_id_raw
    else:
        try:
            chat_id = int(chat_id_raw)
        except ValueError:
            return None
        if chat_id == 0:
            return None

    bool_keys = {
        "exclude_unsaved",
        "exclude_saved",
        "exclude_unlimited",
        "exclude_limited_upgradable",
        "exclude_limited_non_upgradable",
        "exclude_from_blockchain",
        "exclude_unique",
        "sort_by_price",
    }
    options: dict[str, bool | str | int] = {}
    for option in parts[2:]:
        if "=" not in option:
            return None
        key, value = option.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key in bool_keys:
            parsed_value = _parse_bool_option(value)
            if parsed_value is None:
                return None
            options[key] = parsed_value
        elif key == "offset":
            if not value:
                return None
            options[key] = value
        elif key == "limit":
            try:
                limit = int(value)
            except ValueError:
                return None
            if not (GET_CHAT_GIFTS_MIN_LIMIT <= limit <= GET_CHAT_GIFTS_MAX_LIMIT):
                return None
            options[key] = limit
        else:
            return None

    return chat_id, options


def _parse_transfer_business_account_stars_args(
    text: str,
) -> tuple[str, int, bool] | None:
    """Parse transfer Stars args into connection id, amount and confirmation."""
    parts = (text or "").split()
    if len(parts) not in {3, 4}:
        return None

    business_connection_id = parts[1].strip()
    if not business_connection_id:
        return None

    try:
        star_count = int(parts[2])
    except ValueError:
        return None
    if star_count <= 0:
        return None

    confirmed = False
    if len(parts) == 4:
        if parts[3].lower() != TRANSFER_BUSINESS_ACCOUNT_STARS_CONFIRM_KEYWORD:
            return None
        confirmed = True

    return business_connection_id, star_count, confirmed


def _parse_convert_gift_to_stars_args(text: str) -> tuple[str, str, bool] | None:
    """Parse convert gift args into connection id, owned gift id and confirm."""
    parts = (text or "").split()
    if len(parts) not in {3, 4}:
        return None

    business_connection_id = parts[1].strip()
    owned_gift_id = parts[2].strip()
    if not business_connection_id or not owned_gift_id:
        return None

    confirmed = False
    if len(parts) == 4:
        if parts[3].lower() != CONVERT_GIFT_TO_STARS_CONFIRM_KEYWORD:
            return None
        confirmed = True

    return business_connection_id, owned_gift_id, confirmed


def _parse_refund_star_payment_args(text: str) -> tuple[int, str, bool] | None:
    """Parse refund args into user id, Telegram charge id and confirmation."""
    parts = (text or "").split()
    if len(parts) not in {3, 4}:
        return None

    try:
        user_id = int(parts[1])
    except ValueError:
        return None
    if user_id <= 0:
        return None

    telegram_payment_charge_id = parts[2].strip()
    if not telegram_payment_charge_id:
        return None

    confirmed = False
    if len(parts) == 4:
        if parts[3].lower() != REFUND_STAR_PAYMENT_CONFIRM_KEYWORD:
            return None
        confirmed = True

    return user_id, telegram_payment_charge_id, confirmed


def _parse_edit_user_star_subscription_args(
    text: str,
) -> tuple[int, str, bool, bool] | None:
    """Parse subscription edit args into user id, charge id, target state and confirmation."""
    parts = (text or "").split()
    if len(parts) not in {4, 5}:
        return None

    try:
        user_id = int(parts[1])
    except ValueError:
        return None
    if user_id <= 0:
        return None

    telegram_payment_charge_id = parts[2].strip()
    if not telegram_payment_charge_id:
        return None

    state = parts[3].lower()
    if state == "canceled":
        is_canceled = True
    elif state == "active":
        is_canceled = False
    else:
        return None

    confirmed = False
    if len(parts) == 5:
        if parts[4].lower() != EDIT_USER_STAR_SUBSCRIPTION_CONFIRM_KEYWORD:
            return None
        confirmed = True

    return user_id, telegram_payment_charge_id, is_canceled, confirmed


def _parse_upgrade_gift_args(
    text: str,
) -> tuple[str, str, bool | None, bool] | None:
    """Parse upgrade gift args into connection id, gift id, options and confirm."""
    parts = (text or "").split()
    if len(parts) not in {3, 4, 5}:
        return None

    business_connection_id = parts[1].strip()
    owned_gift_id = parts[2].strip()
    if not business_connection_id or not owned_gift_id:
        return None

    keep_original_details: bool | None = None
    confirmed = False
    for option in parts[3:]:
        if option.lower() == UPGRADE_GIFT_CONFIRM_KEYWORD:
            if confirmed:
                return None
            confirmed = True
            continue

        if "=" not in option:
            return None
        key, value = option.split("=", 1)
        if key.strip() != "keep_original_details":
            return None
        parsed_value = _parse_bool_option(value.strip())
        if parsed_value is None or keep_original_details is not None:
            return None
        keep_original_details = parsed_value

    return business_connection_id, owned_gift_id, keep_original_details, confirmed


def _parse_transfer_gift_args(
    text: str,
) -> tuple[str, str, int, int | None, bool] | None:
    """Parse transfer gift args into connection id, gift id, target and options."""
    parts = (text or "").split()
    if len(parts) not in {4, 5, 6}:
        return None

    business_connection_id = parts[1].strip()
    owned_gift_id = parts[2].strip()
    if not business_connection_id or not owned_gift_id:
        return None

    try:
        new_owner_chat_id = int(parts[3])
    except ValueError:
        return None
    if new_owner_chat_id == 0:
        return None

    star_count: int | None = None
    confirmed = False
    for option in parts[4:]:
        if option.lower() == TRANSFER_GIFT_CONFIRM_KEYWORD:
            if confirmed:
                return None
            confirmed = True
            continue

        if "=" not in option:
            return None
        key, value = option.split("=", 1)
        if key.strip() != "star_count":
            return None
        if star_count is not None:
            return None
        try:
            parsed_star_count = int(value.strip())
        except ValueError:
            return None
        if parsed_star_count < 0:
            return None
        star_count = parsed_star_count

    return (
        business_connection_id,
        owned_gift_id,
        new_owner_chat_id,
        star_count,
        confirmed,
    )


def _parse_read_business_message_args(text: str) -> tuple[str, int] | None:
    """Parse ``/readbusinessmessage`` args into connection id and message id."""
    parts = (text or "").split()
    if len(parts) != 3:
        return None

    business_connection_id = parts[1].strip()
    if not business_connection_id:
        return None

    try:
        message_id = int(parts[2])
    except ValueError:
        return None
    if message_id <= 0:
        return None

    return business_connection_id, message_id


def _parse_set_business_account_name_args(
    text: str,
) -> tuple[str, str, str | None] | None:
    """Parse ``/setbusinessaccountname`` args into connection id and name."""
    parts = (text or "").split()
    if len(parts) not in (3, 4):
        return None

    business_connection_id = parts[1].strip()
    first_name = parts[2].strip()
    last_name = parts[3].strip() if len(parts) == 4 else None
    if not business_connection_id or not first_name:
        return None
    if len(first_name) > MAX_BUSINESS_ACCOUNT_NAME_LENGTH:
        return None
    if last_name is not None and len(last_name) > MAX_BUSINESS_ACCOUNT_NAME_LENGTH:
        return None

    return business_connection_id, first_name, last_name


def _parse_set_business_account_username_args(text: str) -> tuple[str, str] | None:
    """Parse ``/setbusinessaccountusername`` args into connection id and username."""
    parts = (text or "").split()
    if len(parts) != 3:
        return None

    business_connection_id = parts[1].strip()
    username = parts[2].strip().lstrip("@")
    if not business_connection_id or not username:
        return None
    if not (
        MIN_BUSINESS_ACCOUNT_USERNAME_LENGTH
        <= len(username)
        <= MAX_BUSINESS_ACCOUNT_USERNAME_LENGTH
    ):
        return None

    return business_connection_id, username


def _parse_set_business_account_bio_args(text: str) -> tuple[str, str] | None:
    """Parse ``/setbusinessaccountbio`` args into connection id and bio text."""
    parts = (text or "").split(maxsplit=2)
    if len(parts) != 3:
        return None

    business_connection_id = parts[1].strip()
    bio = parts[2].strip()
    if not business_connection_id or not bio:
        return None
    if bio.lower() == SET_BUSINESS_ACCOUNT_BIO_CLEAR_KEYWORD:
        return business_connection_id, ""
    if len(bio) > MAX_BUSINESS_ACCOUNT_BIO_LENGTH:
        return None

    return business_connection_id, bio


def _parse_set_business_account_profile_photo_args(
    text: str,
) -> tuple[str, str, bool] | None:
    """Parse profile photo args into connection id, local path and public flag."""
    parts = (text or "").split(maxsplit=3)
    if len(parts) < 3:
        return None

    business_connection_id = parts[1].strip()
    if not business_connection_id:
        return None

    is_public = False
    photo_path = parts[2].strip()
    if len(parts) == 4:
        tail = parts[3].strip()
        public_prefix = "public="
        if tail.lower().startswith(public_prefix):
            value = tail[len(public_prefix) :].strip().lower()
            if value not in {"true", "false"}:
                return None
            is_public = value == "true"
        else:
            photo_path = f"{photo_path} {tail}".strip()

    if not photo_path:
        return None

    return business_connection_id, photo_path, is_public


def _parse_remove_business_account_profile_photo_args(
    text: str,
) -> tuple[str, bool] | None:
    """Parse remove profile photo args into connection id and public flag."""
    parts = (text or "").split()
    if len(parts) not in {3, 4}:
        return None

    business_connection_id = parts[1].strip()
    if not business_connection_id:
        return None

    options = parts[2:]
    if options[-1].lower() != REMOVE_BUSINESS_ACCOUNT_PROFILE_PHOTO_CONFIRM_KEYWORD:
        return None

    is_public = False
    for option in options[:-1]:
        public_prefix = "public="
        if not option.lower().startswith(public_prefix):
            return None
        value = option[len(public_prefix) :].strip().lower()
        if value not in {"true", "false"}:
            return None
        is_public = value == "true"

    return business_connection_id, is_public


def _parse_bool_option(value: str) -> bool | None:
    normalized = value.strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    return None


def _parse_set_business_account_gift_settings_args(
    text: str,
) -> tuple[str, bool, dict[str, bool]] | None:
    """Parse gift settings args into connection id, button flag and gift types."""
    parts = (text or "").split()
    if len(parts) != 8:
        return None

    business_connection_id = parts[1].strip()
    if not business_connection_id:
        return None

    options: dict[str, bool] = {}
    for option in parts[2:]:
        if "=" not in option:
            return None
        key, value = option.split("=", 1)
        key = key.strip()
        parsed_value = _parse_bool_option(value)
        if parsed_value is None:
            return None
        options[key] = parsed_value

    show_gift_button = options.pop("show_gift_button", None)
    if show_gift_button is None:
        return None
    if set(options) != set(ACCEPTED_GIFT_TYPE_KEYS):
        return None

    accepted_gift_types = {
        key: options[key] for key in ACCEPTED_GIFT_TYPE_KEYS
    }
    return business_connection_id, show_gift_button, accepted_gift_types


def _parse_delete_business_messages_args(text: str) -> tuple[str, list[int], bool] | None:
    """Parse ``/deletebusinessmessages`` args into connection id, ids, confirm flag."""
    parts = (text or "").split()
    if len(parts) < 3:
        return None

    business_connection_id = parts[1].strip()
    if not business_connection_id:
        return None

    confirmed = parts[-1].lower() == DELETE_BUSINESS_MESSAGES_CONFIRM_KEYWORD
    id_parts = parts[2:-1] if confirmed else parts[2:]
    raw_ids = [
        raw_id
        for part in id_parts
        for raw_id in part.split(",")
        if raw_id.strip()
    ]
    if not raw_ids or len(raw_ids) > MAX_DELETE_BUSINESS_MESSAGES:
        return None

    try:
        message_ids = [int(raw_id) for raw_id in raw_ids]
    except ValueError:
        return None
    if any(message_id <= 0 for message_id in message_ids):
        return None

    return business_connection_id, message_ids, confirmed


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


def _parse_available_gifts_args(text: str) -> bool | None:
    """Parse ``/availablegifts`` args into confirmation state."""
    parts = (text or "").split()
    if len(parts) == 1:
        return False
    if len(parts) == 2:
        if parts[1].strip().lower() != GET_AVAILABLE_GIFTS_CONFIRM_KEYWORD:
            return None
        return True
    return None


def _parse_send_gift_args(
    text: str,
) -> tuple[str, int | str, str, bool, str | None] | None:
    """Parse ``/sendgift`` args into receiver, gift id and confirmation state."""
    parts = (text or "").split(maxsplit=5)
    if len(parts) not in (4, 5, 6):
        return None

    receiver_type = parts[1].strip().lower()
    if receiver_type not in ("user", "chat"):
        return None

    receiver_raw = parts[2]
    if receiver_type == "user":
        try:
            receiver_id: int | str = int(receiver_raw)
        except ValueError:
            return None
        if receiver_id <= 0:
            return None
    else:
        try:
            receiver_id = int(receiver_raw)
        except ValueError:
            if not receiver_raw.startswith("@") or len(receiver_raw) <= 1:
                return None
            receiver_id = receiver_raw

    gift_id = parts[3].strip()
    if not gift_id:
        return None

    if len(parts) == 4:
        return receiver_type, receiver_id, gift_id, False, None

    if parts[4].strip().lower() != SEND_GIFT_CONFIRM_KEYWORD:
        return None

    gift_text = parts[5].strip() if len(parts) == 6 else None
    return receiver_type, receiver_id, gift_id, True, gift_text or None


def _parse_gift_premium_args(
    text: str,
) -> tuple[int, int, int, bool, str | None] | None:
    """Parse ``/giftpremium`` args into product terms and confirmation state."""
    parts = (text or "").split(maxsplit=5)
    if len(parts) not in (4, 5, 6):
        return None

    try:
        user_id = int(parts[1])
        month_count = int(parts[2])
        star_count = int(parts[3])
    except ValueError:
        return None

    if user_id <= 0:
        return None
    if not (MIN_PREMIUM_MONTHS <= month_count <= MAX_PREMIUM_MONTHS):
        return None
    if star_count <= 0:
        return None

    if len(parts) == 4:
        return user_id, month_count, star_count, False, None

    if parts[4].strip().lower() != GIFT_PREMIUM_CONFIRM_KEYWORD:
        return None

    gift_text = parts[5].strip() if len(parts) == 6 else None
    return user_id, month_count, star_count, True, gift_text or None


def _parse_verify_user_args(text: str) -> tuple[int, bool, str | None] | None:
    """Parse ``/verifyuser`` args into user id and confirmation state."""
    parts = (text or "").split(maxsplit=3)
    if len(parts) not in (2, 3, 4):
        return None

    try:
        user_id = int(parts[1])
    except ValueError:
        return None

    if user_id <= 0:
        return None

    if len(parts) == 2:
        return user_id, False, None

    if parts[2].strip().lower() != VERIFY_USER_CONFIRM_KEYWORD:
        return None

    custom_description = parts[3].strip() if len(parts) == 4 else None
    return user_id, True, custom_description or None


def _parse_remove_user_verification_args(text: str) -> tuple[int, bool] | None:
    """Parse ``/removeuserverification`` args into user id and confirmation."""
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

    if parts[2].strip().lower() != REMOVE_USER_VERIFICATION_CONFIRM_KEYWORD:
        return None

    return user_id, True


def _parse_remove_chat_verification_args(text: str) -> tuple[int | str, bool] | None:
    """Parse ``/removechatverification`` args into chat id and confirmation."""
    parts = (text or "").split()
    if len(parts) not in (2, 3):
        return None

    raw_chat_id = parts[1].strip()
    if not raw_chat_id:
        return None

    chat_id: int | str
    try:
        chat_id = int(raw_chat_id)
    except ValueError:
        if not raw_chat_id.startswith("@") or len(raw_chat_id) == 1:
            return None
        chat_id = raw_chat_id

    if chat_id == 0:
        return None

    if len(parts) == 2:
        return chat_id, False

    if parts[2].strip().lower() != REMOVE_CHAT_VERIFICATION_CONFIRM_KEYWORD:
        return None

    return chat_id, True


def _parse_verify_chat_args(text: str) -> tuple[int | str, bool, str | None] | None:
    """Parse ``/verifychat`` args into chat id and confirmation state."""
    parts = (text or "").split(maxsplit=3)
    if len(parts) not in (2, 3, 4):
        return None

    raw_chat_id = parts[1].strip()
    if not raw_chat_id:
        return None

    chat_id: int | str
    try:
        chat_id = int(raw_chat_id)
    except ValueError:
        if not raw_chat_id.startswith("@") or len(raw_chat_id) == 1:
            return None
        chat_id = raw_chat_id

    if chat_id == 0:
        return None

    if len(parts) == 2:
        return chat_id, False, None

    if parts[2].strip().lower() != VERIFY_CHAT_CONFIRM_KEYWORD:
        return None

    custom_description = parts[3].strip() if len(parts) == 4 else None
    return chat_id, True, custom_description or None


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


def _parse_delete_message_reaction_args(text: str) -> tuple[int, int, int] | None:
    """Parse ``/deletereaction`` args into ``(chat_id, message_id, user_id)``."""
    parts = (text or "").split()
    if len(parts) != 4:
        return None

    try:
        chat_id = int(parts[1])
        message_id = int(parts[2])
        user_id = int(parts[3])
    except ValueError:
        return None

    if message_id < 1 or user_id < 1:
        return None

    return chat_id, message_id, user_id


def _parse_delete_all_message_reactions_args(text: str) -> tuple[int, int] | None:
    """Parse ``/deleteallreactions`` args into ``(chat_id, message_id)``."""
    parts = (text or "").split()
    if len(parts) != 3:
        return None

    try:
        chat_id = int(parts[1])
        message_id = int(parts[2])
    except ValueError:
        return None

    if message_id < 1:
        return None

    return chat_id, message_id


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


def _parse_delete_message_args(text: str):
    """Parse ``/deletemessage`` args into ``chat_id``, ``message_id`` and confirm flag."""
    parts = (text or "").split()
    if len(parts) not in {3, 4}:
        return None

    confirmed = len(parts) == 4 and parts[3].lower() == DELETE_MESSAGE_CONFIRM_KEYWORD
    if len(parts) == 4 and not confirmed:
        return None

    try:
        chat_id = int(parts[1])
        message_id = int(parts[2])
    except ValueError:
        return None

    if message_id <= 0:
        return None

    return chat_id, message_id, confirmed


def _parse_delete_messages_args(text: str) -> tuple[int, list[int], bool] | None:
    """Parse ``/deletemessages`` args into chat id, message ids and confirm flag."""
    parts = (text or "").split()
    if len(parts) < 3:
        return None

    try:
        chat_id = int(parts[1])
    except ValueError:
        return None

    confirmed = parts[-1].lower() == DELETE_MESSAGES_CONFIRM_KEYWORD
    id_parts = parts[2:-1] if confirmed else parts[2:]
    raw_ids = [
        raw_id
        for part in id_parts
        for raw_id in part.split(",")
        if raw_id.strip()
    ]
    if not raw_ids:
        return None

    try:
        message_ids = [int(raw_id) for raw_id in raw_ids]
    except ValueError:
        return None
    if any(message_id <= 0 for message_id in message_ids):
        return None

    return chat_id, message_ids, confirmed


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


def _parse_get_chat_menu_button_args(text: str):
    """Parse ``/getchatmenubutton`` args into optional ``chat_id``."""
    parts = (text or "").split()
    if not parts:
        return False
    if len(parts) == 1:
        return None
    if len(parts) != 2 or not parts[1].startswith("chat_id="):
        return False

    raw_chat_id = parts[1].split("=", maxsplit=1)[1]
    try:
        return int(raw_chat_id)
    except ValueError:
        return False


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


def _default_administrator_rights_for_preset(preset: str):
    from aiogram.types import ChatAdministratorRights

    normalized = (preset or "").strip().lower()
    if normalized == "clear":
        return None
    if normalized == "moderator":
        return ChatAdministratorRights(
            is_anonymous=False,
            can_manage_chat=True,
            can_delete_messages=True,
            can_manage_video_chats=True,
            can_restrict_members=True,
            can_promote_members=False,
            can_change_info=False,
            can_invite_users=True,
            can_post_stories=False,
            can_edit_stories=False,
            can_delete_stories=False,
            can_pin_messages=True,
            can_manage_topics=True,
        )
    if normalized == "manager":
        return ChatAdministratorRights(
            is_anonymous=False,
            can_manage_chat=True,
            can_delete_messages=True,
            can_manage_video_chats=True,
            can_restrict_members=True,
            can_promote_members=True,
            can_change_info=True,
            can_invite_users=True,
            can_post_stories=False,
            can_edit_stories=False,
            can_delete_stories=False,
            can_pin_messages=True,
            can_manage_topics=True,
        )
    if normalized == "channel":
        return ChatAdministratorRights(
            is_anonymous=False,
            can_manage_chat=True,
            can_manage_video_chats=False,
            can_restrict_members=False,
            can_promote_members=False,
            can_change_info=True,
            can_invite_users=True,
            can_post_messages=True,
            can_edit_messages=True,
            can_delete_messages=True,
            can_post_stories=True,
            can_edit_stories=True,
            can_delete_stories=True,
        )
    return False


def _parse_set_my_default_administrator_rights_args(text: str):
    """Parse ``/setmydefaultrights`` args into preset, rights and target flag."""
    parts = (text or "").split()
    if len(parts) < 2 or len(parts) > 3:
        return None

    preset = parts[1].strip().lower()
    rights = _default_administrator_rights_for_preset(preset)
    if rights is False:
        return None

    for_channels = None
    if len(parts) == 3:
        key, separator, value = parts[2].partition("=")
        if key != "for_channels" or separator != "=":
            return None
        for_channels = _parse_bool_value(value)
        if for_channels is None:
            return None

    return preset, rights, for_channels


def _parse_get_my_default_administrator_rights_args(text: str):
    """Parse ``/getmydefaultrights`` args into optional target flag."""
    parts = (text or "").split()
    if len(parts) == 1:
        return None
    if len(parts) != 2:
        return INVALID_COMMAND_ARGS

    key, separator, value = parts[1].partition("=")
    if key != "for_channels" or separator != "=":
        return INVALID_COMMAND_ARGS

    parsed = _parse_bool_value(value)
    if parsed is None:
        return INVALID_COMMAND_ARGS
    return parsed


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


def _parse_get_sticker_set_args(text: str):
    """Parse ``/getstickerset`` args into a sticker set name."""
    parts = (text or "").split()
    if len(parts) != 2:
        return None

    name = parts[1].strip()
    if not name or any(char.isspace() for char in name):
        return None
    return name


def _parse_custom_emoji_stickers_args(text: str):
    """Parse ``/customemojistickers`` args into custom emoji ids."""
    parts = (text or "").split()
    if len(parts) < 2:
        return None
    return [item.strip() for item in parts[1:] if item.strip()]


def _parse_upload_sticker_file_args(text: str):
    """Parse ``/uploadstickerfile`` args into user id, format and local path."""
    parts = (text or "").split(maxsplit=3)
    if len(parts) != 4:
        return None

    try:
        user_id = int(parts[1])
    except ValueError:
        return None

    if user_id <= 0:
        return None

    sticker_format = parts[2].strip()
    sticker_path = parts[3].strip()
    if not sticker_format or not sticker_path:
        return None
    return user_id, sticker_format, sticker_path


def _parse_create_new_sticker_set_args(text: str):
    """Parse ``/createnewstickerset`` args into the first-sticker scenario."""
    parts = (text or "").split(maxsplit=7)
    if len(parts) != 8:
        return None

    try:
        user_id = int(parts[1])
    except ValueError:
        return None

    if user_id <= 0:
        return None

    name = parts[2].strip()
    sticker_type = parts[3].strip()
    sticker_format = parts[4].strip()
    sticker = parts[5].strip()
    emoji_list = [item.strip() for item in parts[6].split(",") if item.strip()]
    title = parts[7].strip()
    if not all([name, sticker_type, sticker_format, sticker, emoji_list, title]):
        return None
    return user_id, name, sticker_type, sticker_format, sticker, emoji_list, title


def _parse_add_sticker_to_set_args(text: str):
    """Parse ``/addstickertoset`` args into the single-sticker scenario."""
    parts = (text or "").split(maxsplit=5)
    if len(parts) != 6:
        return None

    try:
        user_id = int(parts[1])
    except ValueError:
        return None

    if user_id <= 0:
        return None

    name = parts[2].strip()
    sticker_format = parts[3].strip()
    sticker = parts[4].strip()
    emoji_list = [item.strip() for item in parts[5].split(",") if item.strip()]
    if not all([name, sticker_format, sticker, emoji_list]):
        return None
    return user_id, name, sticker_format, sticker, emoji_list


def _parse_replace_sticker_in_set_args(text: str):
    """Parse ``/replacestickerinset`` args into the replacement scenario."""
    parts = (text or "").split(maxsplit=6)
    if len(parts) != 7:
        return None

    try:
        user_id = int(parts[1])
    except ValueError:
        return None

    if user_id <= 0:
        return None

    name = parts[2].strip()
    old_sticker = parts[3].strip()
    sticker_format = parts[4].strip()
    sticker = parts[5].strip()
    emoji_list = [item.strip() for item in parts[6].split(",") if item.strip()]
    if not all([name, old_sticker, sticker_format, sticker, emoji_list]):
        return None
    return user_id, name, old_sticker, sticker_format, sticker, emoji_list


def _parse_set_sticker_position_in_set_args(text: str):
    """Parse ``/setstickerposition`` args into sticker file id and position."""
    parts = (text or "").split()
    if len(parts) != 3:
        return None

    sticker = parts[1].strip()
    try:
        position = int(parts[2])
    except ValueError:
        return None

    if not sticker or position < 0:
        return None
    return sticker, position


def _parse_set_sticker_emoji_list_args(text: str):
    """Parse ``/setstickeremojis`` args into sticker file id and emoji list."""
    parts = (text or "").split(maxsplit=2)
    if len(parts) != 3:
        return None

    sticker = parts[1].strip()
    emoji_list = [item.strip() for item in parts[2].split(",") if item.strip()]
    if not sticker or not emoji_list:
        return None
    return sticker, emoji_list


def _parse_set_sticker_mask_position_args(text: str):
    """Parse ``/setstickermaskposition`` args into sticker and MaskPosition."""
    parts = (text or "").split()
    if len(parts) == 3 and parts[2].strip() == "-":
        sticker = parts[1].strip()
        if not sticker:
            return None
        return sticker, None

    if len(parts) != 6:
        return None

    sticker = parts[1].strip()
    point = parts[2].strip()
    try:
        x_shift = float(parts[3])
        y_shift = float(parts[4])
        scale = float(parts[5])
    except ValueError:
        return None

    if not sticker or scale <= 0:
        return None
    return sticker, {
        "point": point,
        "x_shift": x_shift,
        "y_shift": y_shift,
        "scale": scale,
    }


def _parse_set_sticker_keywords_args(text: str):
    """Parse ``/setstickerkeywords`` args into sticker file id and keywords."""
    parts = (text or "").split(maxsplit=2)
    if len(parts) != 3:
        return None

    sticker = parts[1].strip()
    raw_keywords = parts[2].strip()
    if not sticker or not raw_keywords:
        return None

    if raw_keywords == "-":
        return sticker, []

    keywords = [item.strip() for item in raw_keywords.split(",") if item.strip()]
    if not keywords:
        return None
    return sticker, keywords


def _parse_set_sticker_set_title_args(text: str):
    """Parse ``/setstickersettitle`` args into sticker set name and title."""
    parts = (text or "").split(maxsplit=2)
    if len(parts) != 3:
        return None

    name = parts[1].strip()
    title = parts[2].strip()
    if not name or any(char.isspace() for char in name) or not title:
        return None
    return name, title


def _parse_set_sticker_set_thumbnail_args(text: str):
    """Parse ``/setstickersetthumbnail`` args into the thumbnail scenario."""
    parts = (text or "").split()
    if len(parts) != 5:
        return None

    try:
        user_id = int(parts[1])
    except ValueError:
        return None

    if user_id <= 0:
        return None

    name = parts[2].strip()
    sticker_format = parts[3].strip()
    thumbnail = parts[4].strip()
    if not all([name, sticker_format, thumbnail]):
        return None
    return user_id, name, sticker_format, thumbnail


def _parse_set_custom_emoji_sticker_set_thumbnail_args(text: str):
    """Parse ``/setcustomemojithumbnail`` args into the thumbnail scenario."""
    parts = (text or "").split()
    if len(parts) != 3:
        return None

    name = parts[1].strip()
    custom_emoji_id = parts[2].strip()
    if not all([name, custom_emoji_id]):
        return None
    return name, custom_emoji_id


def _parse_delete_sticker_from_set_args(text: str):
    """Parse ``/deletestickerfromset`` args into sticker file id."""
    parts = (text or "").split()
    if len(parts) != 2:
        return None

    sticker = parts[1].strip()
    if not sticker:
        return None
    return sticker


def _parse_delete_sticker_set_args(text: str):
    """Parse ``/deletestickerset`` args into sticker set name."""
    parts = (text or "").split()
    if len(parts) != 2:
        return None

    name = parts[1].strip()
    if not name:
        return None
    return name


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


def _parse_answer_chat_join_request_query_args(text: str):
    """Parse ``/answerjoinrequestquery`` args into query id and result."""
    parts = (text or "").split()
    if len(parts) != 3:
        return None

    query_id = parts[1].strip()
    result = parts[2].strip()
    if not query_id or result not in CHAT_JOIN_REQUEST_QUERY_RESULTS:
        return None

    return query_id, result


def _parse_send_chat_join_request_web_app_args(text: str):
    """Parse ``/joinrequestwebapp`` args into query id and Mini App URL."""
    parts = (text or "").split()
    if len(parts) != 3:
        return None

    query_id = parts[1].strip()
    web_app_url = parts[2].strip()
    if not query_id or not web_app_url.startswith(("http://", "https://")):
        return None

    return query_id, web_app_url


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
