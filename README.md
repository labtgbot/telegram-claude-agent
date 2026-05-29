# Telegram Claude Agent

**Repository:** https://github.com/labtgbot/telegram-claude-agent

A professional Telegram bot agent that integrates with [free-claude-code](https://github.com/labtgbot/free-claude-code), providing access to Claude Code capabilities via the Telegram Bot API.

## Features

- Connect to a locally or remotely deployed free-claude-code instance
- Support for streaming responses with real-time updates
- Group privacy mode for mention/reply interactions without shared history
- Handle media: images, documents (PDF, TXT, DOCX), voice messages (with Whisper transcription)
- Core commands: /start, /help, /model, /settings, /webhook, /deletewebhook, /logout, /clear
- Built-in rate limiting and security (webhook secret token)
- Structured logging with structlog
- Optional Redis caching (not implemented, but architecture ready)
- Easy deployment with Docker and docker-compose

## Tech Stack

- **Bot framework**: aiogram 3.3.0 (asynchronous Telegram Bot API framework)
- **HTTP client**: httpx with streaming support
- **Server**: FastAPI + uvicorn
- **Config**: pydantic-settings
- **Logging**: structlog (JSON)
- **Media**: Pillow, PyPDF2, python-docx, (optional) openai-whisper

## Prerequisites

- Python 3.11 or higher
- A Telegram bot token from [@BotFather](https://t.me/botfather)
- A running free-claude-code instance (default: http://localhost:8082)

## Installation

### From source

```bash
git clone https://github.com/labtgbot/telegram-claude-agent.git
cd telegram-claude-agent
python -m venv venv
source venv/bin/activate  # on Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Optional dependencies for voice transcription

```bash
pip install openai-whisper  # may require ffmpeg
```

## Configuration

Copy `.env.example` to `.env` and fill in the required values:

```env
FREE_CLAUDE_BASE_URL=http://localhost:8082
FREE_CLAUDE_AUTH_TOKEN=your_proxy_auth_token
FREE_CLAUDE_DEFAULT_MODEL=nvidia_nim/z-ai/glm4.7
FREE_CLAUDE_TIMEOUT_SECONDS=120
FREE_CLAUDE_STREAMING_ENABLED=true

TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_WEBHOOK_URL=https://your-domain.com/webhook  # optional; if empty, uses polling
TELEGRAM_GUEST_MODE_ENABLED=true
TELEGRAM_ALLOWED_CHAT_IDS=  # optional whitelist
TELEGRAM_ADMIN_CHAT_IDS=  # optional admin webhook command allowlist
TELEGRAM_CHAT_ACTION_ENABLED=true  # show "typing…" while a request is handled
TELEGRAM_MESSAGE_DRAFT_ENABLED=false  # stream replies via ephemeral drafts (private chats only)
TELEGRAM_BOT_NAME=  # optional startup sync for the bot display name
TELEGRAM_BOT_NAME_LANGUAGE_CODE=  # optional IETF language code for localized bot name
TELEGRAM_BOT_SHORT_DESCRIPTION=  # optional startup sync for the bot profile short description
TELEGRAM_BOT_SHORT_DESCRIPTION_LANGUAGE_CODE=  # optional IETF language code for localized bot short description
TELEGRAM_BOT_DESCRIPTION=  # optional startup sync for the bot profile description
TELEGRAM_BOT_DESCRIPTION_LANGUAGE_CODE=  # optional IETF language code for localized bot description
TELEGRAM_BOT_DEFAULT_ADMINISTRATOR_RIGHTS=  # optional startup sync preset: moderator, manager, channel, or clear
TELEGRAM_BOT_DEFAULT_ADMINISTRATOR_RIGHTS_FOR_CHANNELS=  # optional true for channels, false for groups

API_SECRET_TOKEN=random_secret_for_webhook_verification
RATE_LIMIT_REQUESTS_PER_MINUTE=60
LOG_LEVEL=INFO
```

### Environment variables

- `FREE_CLAUDE_BASE_URL` – base URL of the free-claude-code proxy.
- `FREE_CLAUDE_AUTH_TOKEN` – authentication token for the proxy.
- `FREE_CLAUDE_DEFAULT_MODEL` – default model ID to use.
- `FREE_CLAUDE_TIMEOUT_SECONDS` – HTTP timeout for proxy requests.
- `FREE_CLAUDE_STREAMING_ENABLED` – whether to stream responses (`true`/`false`).
- `TELEGRAM_BOT_TOKEN` – your bot token from BotFather.
- `TELEGRAM_WEBHOOK_URL` – if set, the bot will use webhook mode; otherwise, it uses long polling.
- `TELEGRAM_GUEST_MODE_ENABLED` – enable no-history group privacy mode for mentioned/replied messages (`true`/`false`).
- `TELEGRAM_ALLOWED_CHAT_IDS` – optional comma-separated list of chat IDs to restrict operation.
- `TELEGRAM_ADMIN_CHAT_IDS` – optional comma-separated list of chat IDs allowed to run admin commands. Diagnostics like `/webhook` and lifecycle commands like `/deletewebhook` fall back to `TELEGRAM_ALLOWED_CHAT_IDS` when empty; destructive commands like `/logout` require this list and do not fall back. If both lists are empty, admin commands are disabled.
- `TELEGRAM_CHAT_ACTION_ENABLED` – whether to show a `typing…` chat action while Claude/proxy handles a request (`true`/`false`, default `true`). Set to `false` to keep the chat silent during processing.
- `TELEGRAM_MESSAGE_DRAFT_ENABLED` – whether to stream replies through ephemeral `sendMessageDraft` previews instead of repeatedly editing a message while Claude generates the answer (`true`/`false`, default `false`). Telegram limits the method to private chats, so other chats keep edit-based streaming.
- `TELEGRAM_BOT_NAME` – optional bot display name to apply with Telegram `setMyName` on startup. Leave unset to skip profile sync; an empty string clears the selected name.
- `TELEGRAM_BOT_NAME_LANGUAGE_CODE` – optional language code for a localized `setMyName` update. Leave empty to update the default bot name.
- `TELEGRAM_BOT_SHORT_DESCRIPTION` – optional bot profile short description to apply with Telegram `setMyShortDescription` on startup. Leave unset to skip profile sync; an empty string clears the selected short description.
- `TELEGRAM_BOT_SHORT_DESCRIPTION_LANGUAGE_CODE` – optional language code for a localized `setMyShortDescription` update. Leave empty to update the default bot short description.
- `TELEGRAM_BOT_DESCRIPTION` – optional bot profile description to apply with Telegram `setMyDescription` on startup. Leave unset to skip profile sync; an empty string clears the selected description.
- `TELEGRAM_BOT_DESCRIPTION_LANGUAGE_CODE` – optional language code for a localized `setMyDescription` update. Leave empty to update the default bot description.
- `TELEGRAM_BOT_DEFAULT_ADMINISTRATOR_RIGHTS` – optional preset to apply with Telegram `setMyDefaultAdministratorRights` on startup. Supported values are `moderator`, `manager`, `channel`, and `clear`; leave unset to skip sync.
- `TELEGRAM_BOT_DEFAULT_ADMINISTRATOR_RIGHTS_FOR_CHANNELS` – optional target flag for `setMyDefaultAdministratorRights`: `true` for channels, `false` for groups and supergroups, empty for Telegram default targeting.
- `API_SECRET_TOKEN` – secret token for verifying webhook requests (highly recommended for webhook mode).
- `RATE_LIMIT_REQUESTS_PER_MINUTE` – maximum requests per user per minute.
- `LOG_LEVEL` – logging level (default `INFO`).

## Running the bot

### Development

```bash
# Ensure free-claude-code is running on the configured port
uvicorn bot.main:app --reload --port 8000
```

The bot will start polling by default if no webhook URL is set.

### Production

#### Using Docker

```bash
docker-compose up -d
```

See `docker-compose.yml` for a reference setup including free-claude-code.

#### Using systemd (example)

```ini
[Unit]
Description=Telegram Claude Agent
After=network.target

[Service]
Type=simple
User=bot
WorkingDirectory=/opt/telegram-claude-agent
EnvironmentFile=/opt/telegram-claude-agent/.env
ExecStart=/opt/telegram-claude-agent/venv/bin/uvicorn bot.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Make sure to set `TELEGRAM_WEBHOOK_URL` to a publicly accessible HTTPS URL.

## Usage

### Commands

- `/start` – Show welcome message.
- `/help` – Show help text.
- `/model` – Show current model and list available models. Use `/model <model_id>` or an inline model button to switch.
- `/settings` – Display your current settings with an inline refresh button.
- `/webhook` – Show webhook diagnostics for allowed admin chats.
- `/deletewebhook [drop_pending_updates=true|false]` – Delete the webhook for
  allowed admin chats; pending updates are kept by default.
- `/logout` – Log the bot out of the cloud Bot API server (admin only, requires text or inline confirmation).
- `/close` – Close the bot instance on the current Bot API server (admin only, requires text or inline confirmation).
- `/forward` – Forward a message from another chat into this chat for support/moderation review (admin only).
- `/forwards` – Forward several messages from another chat into this chat, preserving album grouping (admin only).
- `/copy` – Copy a message from another chat into this chat without a link to the original sender (admin only).
- `/copies` – Copy several messages from another chat into this chat without a link to the original sender, preserving album grouping (admin only).
- `/photo` – Send an image into this chat as a real Telegram photo via a URL or file_id (admin only).
- `/audio` – Send an audio file into this chat as a playable music track via a URL or file_id (admin only).
- `/livephoto` – Send a live photo (a short video paired with its static cover) into this chat via file_ids (admin only).
- `/document` – Send a file into this chat as a document via a URL or file_id (admin only).
- `/video` – Send a video into this chat as a playable Telegram video via a URL or file_id (admin only).
- `/videonote` – Send a rounded square video message (video note) into this chat via a file_id (admin only).
- `/animation` – Send an animation (GIF or soundless video) into this chat as a playable looping clip via a URL or file_id (admin only).
- `/sticker` – Send a sticker or custom emoji into this chat via a URL or file_id (admin only).
- `/getstickerset <sticker_set_name>` – Fetch sticker set metadata and sticker file_ids by set name (admin only).
- `/customemojistickers <custom_emoji_id> [...]` – Fetch custom emoji sticker metadata by up to 200 custom emoji ids (admin only).
- `/addstickertoset <user_id> <name> <sticker_format> <sticker_file_id> <emoji[,emoji...]>` – Add a pre-uploaded sticker to an existing sticker set (admin only).
- `/replacestickerinset <user_id> <name> <old_sticker_file_id> <sticker_format> <new_sticker_file_id> <emoji[,emoji...]>` – Replace a sticker in an existing sticker set (admin only).
- `/setstickerposition <sticker_file_id> <position>` – Move a sticker inside its sticker set by zero-based position (admin only).
- `/setstickeremojis <sticker_file_id> <emoji[,emoji...]>` – Replace the emoji list for a sticker in its sticker set (admin only).
- `/setstickermaskposition <sticker_file_id> <point> <x_shift> <y_shift> <scale>` – Change a mask sticker position in its sticker set (admin only). Pass `/setstickermaskposition <sticker_file_id> -` to clear it.
- `/setstickerkeywords <sticker_file_id> <keyword[,keyword...]|->` – Replace or clear sticker search keywords in its sticker set (admin only).
- `/setstickersetthumbnail <user_id> <sticker_set_name> <format> <thumbnail_file_id|->` – Set or clear a sticker set thumbnail (admin only).
- `/setcustomemojithumbnail <sticker_set_name> <custom_emoji_id|->` – Set or clear a custom emoji sticker set thumbnail (admin only).
- `/deletestickerfromset <sticker_file_id>` – Delete a sticker from its sticker set (admin only).
- `/deletestickerset <sticker_set_name>` – Delete a bot-created sticker set (admin only).
- `/voice` – Send a voice message into this chat as a playable audio clip (shown as a waveform) via a URL or file_id (admin only).
- `/paidmedia` – Send a paid photo into this chat that users must pay for with Telegram Stars to access, via a URL or file_id (admin only).
- `/sendinvoice` – Send a Telegram Stars test invoice into this chat (admin only).
- `/answerwebappquery` – Answer a Telegram Web App query with one inline result (admin only).
- `/savepreparedinline` – Save one prepared inline message for a user (admin only).
- `/savepreparedkeyboard` – Save a prepared keyboard button for a Mini App user (admin only).
- `/location` – Send a point on the map into this chat as a real Telegram location via latitude and longitude (admin only).
- `/venue` – Send a venue (a named place with a title and an address pinned on the map) into this chat via latitude and longitude (admin only).
- `/poll` – Send a native poll (an interactive question with 2-10 tappable answer options) into this chat (admin only).
- `/stoppoll` – Stop a bot-sent native poll by chat/message id and return the final poll state (admin only).
- `/approvesuggestedpost` – Approve a direct messages suggested post by chat/message id, with an optional Unix send date (admin only).
- `/declinesuggestedpost` – Decline a direct messages suggested post by chat/message id, with an optional creator comment (admin only).
- `/contact` – Send a phone contact (a name with a phone number that can be saved to the address book) into this chat (admin only).
- `/dice` – Send an animated dice (an emoji that shows a random value) into this chat (admin only).
- `/chataction` – Show a chat action (a transient status such as `typing…`) in this chat (admin only).
- `/messagedraft` – Stream an ephemeral message draft (a ~30-second preview shown above the input field) into this private chat (admin only).
- `/checklist` – Send a checklist (a titled list of 1-30 tasks) into this chat on behalf of a connected business account (admin only).
- `/editchecklist` – Edit an existing business checklist message by chat/message id (admin only).
- `/poststory` – Post a photo story on behalf of a connected business account by `business_connection_id` (admin only).
- `/repoststory` – Repost a bot-posted story between managed business accounts by `business_connection_id` (admin only).
- `/editstory` – Edit a bot-posted photo story for a connected business account by `business_connection_id` and `story_id` (admin only).
- `/businessconnection` – Fetch metadata for a connected Telegram business account by `business_connection_id` (admin only).
- `/businessstarbalance` – Fetch the Telegram Stars balance of a connected business account by `business_connection_id` (admin only).
- `/businessgifts` – Fetch owned gifts of a connected business account by `business_connection_id` (admin only).
- `/chatgifts` – Fetch owned gifts of a channel chat by `chat_id` or `@channelusername` (admin only).
- `/transferbusinessstars` – Transfer Telegram Stars from a connected business account to the bot balance (admin only, requires confirmation).
- `/convertgiftstars` – Convert an owned gift of a connected business account to Telegram Stars (admin only, requires confirmation).
- `/upgradegift` – Upgrade an owned gift of a connected business account with Telegram Stars (admin only, requires confirmation).
- `/transfergift` – Transfer a unique owned gift of a connected business account to another chat (admin only, requires confirmation).
- `/readbusinessmessage` – Mark one connected business-account message as read by `business_connection_id` and `message_id` (admin only).
- `/setbusinessaccountname` – Set the first and optional last name of a connected business account by `business_connection_id` (admin only).
- `/setbusinessaccountbio` – Set or clear the bio of a connected business account by `business_connection_id` (admin only).
- `/setbusinessaccountprofilephoto` – Set the static JPG profile photo of a connected business account by `business_connection_id` and local `photo_path` (admin only).
- `/removebusinessaccountprofilephoto` – Remove a profile photo of a connected business account by `business_connection_id` (admin only, requires confirmation).
- `/setbusinessaccountgiftsettings` – Change incoming gift settings of a connected business account by `business_connection_id` (admin only).
- `/deletebusinessmessages` – Delete connected business-account messages by `business_connection_id` and `message_ids` (admin only, requires confirmation).
- `/deletemessage` – Delete one message by `chat_id` and `message_id` where Telegram allows the bot to delete it (admin only, requires confirmation).
- `/deleteallreactions` – Delete all reactions from one message by `chat_id` and `message_id` (admin only).
- `/managedbottoken` – Fetch the live token of a managed bot by its Telegram user id (admin only).
- `/managedbotaccess` – Fetch access settings for a managed bot by its Telegram user id (admin only).
- `/setmanagedbotaccess` – Update access settings for a managed bot by its Telegram user id (admin only, requires confirmation).
- `/replacemanagedbottoken` – Rotate the live token of a managed bot by its Telegram user id (admin only, requires confirmation).
- `/availablegifts` – Fetch the current Telegram gift catalog for billing/rewards review (admin only, requires confirmation).
- `/usergifts` – Fetch owned gifts of a Telegram user by `user_id` (admin only).
- `/sendgift` – Send a Telegram gift to a user or channel with explicit Stars-spending confirmation (admin only).
- `/giftpremium` – Gift Telegram Premium to a user with explicit Stars-spending confirmation (admin only).
- `/removeuserverification <user_id> confirm` – Remove Telegram verification from a user with explicit confirmation (admin only).
- `/removechatverification <chat_id|@username> confirm` – Remove Telegram verification from a chat with explicit confirmation (admin only).
- `/mediagroup` – Send 2-10 media items into this chat as a single album (media group) via URLs or file_ids (admin only).
- `/banchatmember <chat_id> <user_id> [until_date_unix] [revoke=true|false]` – Ban a user from a group, supergroup, or channel where the bot has `can_restrict_members` (admin only).
- `/banchatsenderchat <chat_id> <sender_chat_id>` – Ban a channel chat from sending messages as itself into a supergroup or channel where the bot has `can_restrict_members` (admin only).
- `/unbanchatmember <chat_id> <user_id> [only_if_banned=true|false]` – Unban a user from a group, supergroup, or channel where the bot has `can_restrict_members` (admin only).
- `/restrictchatmember <chat_id> <user_id> <mute|readonly|unrestrict> [until_date_unix] [independent=true|false]` – Restrict or restore a group/supergroup member where the bot has `can_restrict_members` (admin only).
- `/setchatpermissions <chat_id> <closed|text|media|open> [independent=true|false]` – Set default group/supergroup member permissions where the bot has `can_restrict_members` (admin only).
- `/pinchatmessage <chat_id> <message_id> [silent|loud]` – Pin a message where the bot has `can_pin_messages` in groups/supergroups or `can_edit_messages` in channels (admin only).
- `/unpinchatmessage <chat_id> [message_id]` – Unpin a specific or most recent pinned message where the bot has `can_pin_messages` in groups/supergroups or `can_edit_messages` in channels (admin only).
- `/unpinallchatmessages <chat_id>` – Unpin all pinned messages where the bot has `can_pin_messages` in groups/supergroups or `can_edit_messages` in channels (admin only).
- `/editreplymarkup <chat_id> <message_id> [clear|empty]` – Edit only the inline keyboard of a bot-sent message, or clear it by omitting the final argument (admin only).
- `/setchatphoto <chat_id> <photo_path>` – Set a new group/supergroup photo from a local file where the bot can change chat information (admin only).
- `/deletechatphoto <chat_id>` – Delete the current group/supergroup photo where the bot can change chat information (admin only).
- `/setchatmenubutton [chat_id=<id>] default|commands|web_app <text> <url>` – Set the bot menu button for one chat or the default menu button (admin only).
- `/getchatmenubutton [chat_id=<id>]` – Fetch the bot menu button for one chat or the default menu button (admin only).
- `/setmyname <name> [language=<code>]` – Set or clear the bot display name shown in Telegram clients (admin only).
- `/setmydescription <description> [language=<code>]` – Set or clear the public bot profile description shown in Telegram clients (admin only).
- `/setmydefaultrights <moderator|manager|channel|clear> [for_channels=true|false]` – Set or clear default administrator rights requested when the bot is added as administrator (admin only).
- `/getmydefaultrights [for_channels=true|false]` – Fetch default administrator rights requested when the bot is added as administrator (admin only).
- `/removemyprofilephoto confirm` – Remove the bot profile photo through Bot API 10.0 (admin only, requires confirmation; rollback is `/setmyprofilephoto <photo_path>` with the previous image).
- `/getmyname [language=<code>]` – Fetch the bot display name shown in Telegram clients (admin only).

`getMyDefaultAdministratorRights` is also audited on startup after optional
`TELEGRAM_BOT_DEFAULT_ADMINISTRATOR_RIGHTS` sync. The read path accepts only
`for_channels=true|false`, requires no bot administrator rights and no special
update types, and is guarded by `TELEGRAM_ADMIN_CHAT_IDS` when exposed as
`/getmydefaultrights`. It verifies BotFather/startup state without calling
`free-claude-code`; rollback for wrong defaults is `/setmydefaultrights clear`
or changing the preset and restarting the service. The service uses aiogram's
typed method when available and an isolated raw Bot API helper on pinned
`aiogram==3.3.0` runtimes that do not expose it yet.
- `/setchatdescription <chat_id> [description]` – Set or clear a group,
  supergroup, or channel description where the bot can change chat information
  (admin only).
- `/setchatstickerset <chat_id> <sticker_set_name>` – Set a supergroup sticker
  set where the bot can change chat information (admin only).
- `/deletechatstickerset <chat_id>` – Delete a supergroup sticker set where
  the bot can change chat information (admin only).
- `/getstickerset <sticker_set_name>` – Fetch sticker set metadata and sticker
  file_ids by set name (admin only).
- `/customemojistickers <custom_emoji_id> [...]` – Fetch custom emoji sticker
  metadata by id for sticker/custom emoji lifecycle review (admin only).
- `/addstickertoset <user_id> <name> <sticker_format> <sticker_file_id> <emoji[,emoji...]>` – Add a pre-uploaded sticker to an existing sticker set (admin only).
- `/replacestickerinset <user_id> <name> <old_sticker_file_id> <sticker_format> <new_sticker_file_id> <emoji[,emoji...]>` – Replace a sticker in an existing sticker set (admin only).
- `/setstickerposition <sticker_file_id> <position>` – Move a sticker inside
  its sticker set by zero-based position (admin only).
- `/setstickeremojis <sticker_file_id> <emoji[,emoji...]>` – Replace the
  emoji list for a sticker in its sticker set (admin only).
- `/setstickermaskposition <sticker_file_id> <point> <x_shift> <y_shift> <scale>` – Change a mask sticker position in its sticker set (admin only). Pass `/setstickermaskposition <sticker_file_id> -` to clear it.
- `/setstickerkeywords <sticker_file_id> <keyword[,keyword...]|->` – Replace
  or clear sticker search keywords in its sticker set (admin only).
- `/setstickersettitle <sticker_set_name> <title>` – Change a sticker set
  title for a set created by the bot (admin only).
- `/setstickersetthumbnail <user_id> <sticker_set_name> <format> <thumbnail_file_id|->` – Set or clear a sticker set thumbnail (admin only).
- `/setcustomemojithumbnail <sticker_set_name> <custom_emoji_id|->` – Set or clear a custom emoji sticker set thumbnail (admin only).
- `/deletestickerfromset <sticker_file_id>` – Delete a sticker from its
  sticker set (admin only).
- `/deletestickerset <sticker_set_name>` – Delete a bot-created sticker set
  (admin only).
- `/promotechatmember <chat_id> <user_id> <moderator|manager|demote>` – Promote or demote a group, supergroup, or channel member where the bot has `can_promote_members` (admin only).
- `/approvechatjoinrequest <chat_id> <user_id>` – Approve a pending join request where the bot has `can_invite_users` (admin only).
- `/declinechatjoinrequest <chat_id> <user_id>` – Decline a pending join request where the bot has `can_invite_users` (admin only).
- `/exportchatinvitelink <chat_id>` – Export a new primary invite link for a group, supergroup, or channel where the bot has `can_invite_users` (admin only).
- `/getchat <chat_id>` – Fetch Telegram chat metadata for a private chat, group, supergroup, or channel (admin only).
- `/getchatadministrators <chat_id>` – Fetch the administrator list and rights for a group, supergroup, or channel known to the bot (admin only).
- `/getchatmembercount <chat_id>` – Fetch the member count for a group, supergroup, or channel known to the bot (admin only).
- `/forumtopiciconstickers` – Fetch available forum topic icon stickers and their `custom_emoji_id` values (admin only).
- `/createforumtopic <chat_id> <name> [icon_color=<rgb_int>] [icon_custom_emoji_id=<id>]` – Create a forum topic in a supergroup where the bot can manage topics (admin only).
- `/editforumtopic <chat_id> <message_thread_id> [name=<text>] [icon_custom_emoji_id=<id>]` – Edit a forum topic in a supergroup where the bot can manage topics (admin only).
- `/editgeneralforumtopic <chat_id> <name>` – Edit the General forum topic in a supergroup where the bot can manage topics (admin only).
- `/closeforumtopic <chat_id> <message_thread_id>` – Close a forum topic in a supergroup where the bot can manage topics (admin only).
- `/reopenforumtopic <chat_id> <message_thread_id>` – Reopen a closed forum topic in a supergroup where the bot can manage topics (admin only).
- `/reopengeneralforumtopic <chat_id>` – Reopen the General forum topic in a supergroup where the bot can manage topics (admin only).
- `/hidegeneralforumtopic <chat_id>` – Hide the General forum topic in a supergroup where the bot can manage topics (admin only).
- `/unhidegeneralforumtopic <chat_id>` – Unhide the General forum topic in a supergroup where the bot can manage topics (admin only).
- `/deleteforumtopic <chat_id> <message_thread_id>` – Delete a forum topic in a supergroup where the bot can manage topics (admin only).
- `/unpinallforumtopicmessages <chat_id> <message_thread_id>` – Unpin all pinned messages in a forum topic where the bot can manage topics (admin only).
- `/unpinallgeneralforumtopicmessages <chat_id>` – Unpin all pinned messages in the General forum topic where the bot can manage topics (admin only).
- `/userpersonalchatmessages <user_id> [limit]` – Fetch recent messages from the user's personal chat with the bot (admin only).
- `/leavechat <chat_id> confirm` – Make the bot leave a group, supergroup, or channel (admin only, requires confirmation).
- `/createchatinvitelink <chat_id> [name=<text>] [expire_date=<unix_time>] [member_limit=<1-99999>] [creates_join_request=true|false]` – Create an additional invite link where the bot has `can_invite_users` (admin only).
- `/editchatinvitelink <chat_id> <invite_link> [name=<text>] [expire_date=<unix_time>] [member_limit=<1-99999>] [creates_join_request=true|false]` – Edit an existing non-primary invite link where the bot has `can_invite_users` (admin only).
- `/revokechatinvitelink <chat_id> <invite_link>` – Revoke an invite link created by the bot where the bot has `can_invite_users` (admin only).
- `/createchatsubscriptioninvitelink <chat_id> <subscription_price> [name=<text>] [subscription_period=2592000]` – Create a paid subscription invite link where the bot has `can_invite_users` (admin only).
- `/editchatsubscriptioninvitelink <chat_id> <invite_link> [name=<text>]` – Edit an existing subscription invite link where the bot has `can_invite_users` (admin only).
- `/clear` – Clear your conversation history and show an inline repeat action.

### Official Telegram Guest Mode

When Telegram delivers a Guest Mode message with `Message.guest_query_id`, the
bot now sends the final Claude response through the raw Bot API
`answerGuestQuery` endpoint. This lets Telegram return the answer to the guest
query without requiring the bot to be a member of the target chat. If Telegram
rejects the guest query answer, the handler logs the error and falls back to the
normal chat reply path.

### Callback queries

Inline keyboard actions for `/settings`, `/model`, `/clear`, `/logout`, and
`/close` are answered with Telegram Bot API `answerCallbackQuery` through
aiogram's typed API. The bot must receive `callback_query` updates. Callback
answer text follows Telegram's 200-character limit, Telegram errors are
structured-log events, and admin callbacks keep the same strict
`TELEGRAM_ADMIN_CHAT_IDS` checks as the matching text commands.

### Webhook diagnostics and lifecycle

The restricted `/webhook` command calls Telegram Bot API `getWebhookInfo`
through aiogram's typed API. It requires no Telegram method parameters and
shows the current webhook status, webhook URL, pending update count,
`allowed_updates`, certificate flag, connection limit, and the latest delivery
or synchronization error reported by Telegram.

The restricted `/deletewebhook` command calls Telegram Bot API `deleteWebhook`
through aiogram's typed API before switching the bot back to long polling or a
local Bot API server. It accepts one optional argument:
`drop_pending_updates=true|false`. The default is `false`, so pending updates
are kept unless an administrator explicitly asks Telegram to drop them.

Both commands require only a valid bot token; no chat administrator rights or
special update subscriptions are required. Use `TELEGRAM_ADMIN_CHAT_IDS` to
restrict this operational output and lifecycle control to private admin chats
or trusted operations groups. If `TELEGRAM_ADMIN_CHAT_IDS` is empty, the
commands fall back to `TELEGRAM_ALLOWED_CHAT_IDS`. If both lists are empty,
admin webhook commands are disabled. The global rate-limit middleware still
applies to these commands.

When the bot is running in long polling mode, Telegram returns webhook info with
an empty `url`, which `/webhook` displays as disabled. `/deletewebhook` changes
Telegram delivery state but does not call `free-claude-code`; rollback is
setting `TELEGRAM_WEBHOOK_URL` again and restarting the bot, or re-registering
the webhook with `setWebhook`. If `drop_pending_updates=true` was used, already
dropped updates cannot be recovered from Telegram.

### Log out from the cloud Bot API

The restricted `/logout` command calls Telegram Bot API `logOut` through
aiogram's typed `Bot.log_out()` wrapper. The method takes no parameters and
returns `True` on success. It is the operational step required before launching
the bot against a local Bot API server.

Because `logOut` is destructive, it is guarded more strictly than `/webhook`:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- it requires explicit confirmation: a bare `/logout` only prints a warning,
  and the logout runs only after `/logout confirm`.

After a successful call the bot stops receiving updates from the cloud Bot API
server and cannot log back into it for 10 minutes. Recovery is simply waiting
out the 10-minute window (or finishing the migration to a local Bot API server)
and starting the bot again so it logs back in.

### Close the bot instance

The restricted `/close` command calls Telegram Bot API `close` through
aiogram's typed `Bot.close()` wrapper. The method takes no parameters and
returns `True` on success. It closes the running bot instance and is the
operational step required before moving the bot from one local Bot API server
to another.

Because `close` is destructive, it is guarded exactly like `/logout`:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- it requires explicit confirmation: a bare `/close` only prints a warning,
  and the close runs only after `/close confirm`.

Delete the webhook before calling `close` so the bot is not relaunched after a
server restart. Telegram returns error 429 if `close` is called within the
first 10 minutes after the bot was launched. Recovery is simply moving the bot
to its new Bot API server and starting it again to resume processing updates.

### Forward messages for moderation

The restricted `/forward` command calls Telegram Bot API `forwardMessage`
through aiogram's typed `Bot.forward_message()` wrapper. It is meant for a
support/moderation scenario: an operator pulls a specific message from a chat
the bot is a member of into the current admin chat for review.

Usage: `/forward <from_chat_id> <message_id> [share]`

- the message is always forwarded into the chat where the command was issued;
- the forwarded copy is protected from further forwarding and saving by default
  (`protect_content=true`), so moderated content is not leaked further; append
  `share` to drop that protection;
- Telegram rejects forwarding of service messages and messages whose original
  already has protected content, and the bot must be able to access
  `from_chat_id` (it must be a member of that chat). Such cases return a
  Telegram error that the command reports back instead of forwarding.

Because the command relays content between chats, it is guarded like the other
admin commands:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- the global rate-limit middleware still applies.

The `/setchatpermissions <chat_id> <closed|text|media|open>
[independent=true|false]` admin command calls Telegram Bot API
`setChatPermissions` through aiogram's typed API. It changes the default
permissions for all non-administrator members in a target group or supergroup;
it does not change administrator permissions and is independent from the
free-claude-code proxy.

The target `chat_id` and preset are required. `closed` denies sending messages,
`text` allows text messages only, `media` allows text plus common media and
reactions but keeps polls, other messages, link previews and management actions
disabled, and `open` restores common member permissions including invites, pins
and topic management. The optional `independent=true|false` flag is passed as
`use_independent_chat_permissions`; when enabled, Telegram applies media
permission flags independently instead of deriving them from broader send
permissions.

The bot must already be an administrator in the target group or supergroup
with `can_restrict_members`. No special update subscription is required because
the scenario is initiated by a normal Telegram message update. Telegram
permission errors such as missing admin rights, unknown chats, or unsupported
chat types are reported back to the admin chat. Rollback is another
`/setchatpermissions` call with the previous preset, usually `open`, or a
manual permission change in Telegram's chat administration UI.

Because the command changes the default permissions for a whole chat, it is
guarded like the other admin commands:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- the global rate-limit middleware still applies.

### Set bot commands

The restricted `/setmycommands` command calls Telegram Bot API `setMyCommands`
through aiogram's typed `Bot.set_my_commands()` wrapper. It updates the default
command list shown in Telegram clients, so BotFather command configuration can
be reproduced from the repository.

Usage: `/setmycommands command:Description | command2:Description`

Example: `/setmycommands start:Start the bot | help:Show help | model:Show or change the AI model`

- Telegram accepts 0-100 commands in one list;
- command names must be lowercase Latin letters, digits or underscores and
  1-32 characters long;
- descriptions are required and must be 1-256 characters long;
- the bot does not need chat administrator rights, but the command changes the
  bot's public UI and is guarded like the other admin commands.

It is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
**not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
is empty, the command is disabled. The global rate-limit middleware still
applies.

### Set chat menu button

The restricted `/setchatmenubutton` command calls Telegram Bot API
`setChatMenuButton` through aiogram's typed `Bot.set_chat_menu_button()`
wrapper. It updates the bot menu button for a selected chat, or the default
menu button when `chat_id` is omitted.

Usage: `/setchatmenubutton [chat_id=<id>] default|commands|web_app <text> <url>`

Examples:

- `/setchatmenubutton commands`
- `/setchatmenubutton chat_id=-100123 default`
- `/setchatmenubutton chat_id=-100123 web_app Support https://example.com`

It is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
**not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
is empty, the command is disabled. The global rate-limit middleware still
applies.

### Get chat menu button

The restricted `/getchatmenubutton` command calls Telegram Bot API
`getChatMenuButton` through aiogram's typed `Bot.get_chat_menu_button()`
wrapper. It is a read-only diagnostic for checking the menu button Telegram
currently serves for a selected chat, or the default menu button when `chat_id`
is omitted.

Usage: `/getchatmenubutton [chat_id=<id>]`

Examples:

- `/getchatmenubutton`
- `/getchatmenubutton chat_id=-100123`

The method does not require chat administrator rights or special update types,
but the command is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS`
and does **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if
`TELEGRAM_ADMIN_CHAT_IDS` is empty, the command is disabled. The global
rate-limit middleware still applies.

### Set bot name

The restricted `/setmyname` command calls Telegram Bot API `setMyName` through
aiogram's typed `Bot.set_my_name()` wrapper. It updates the bot display name
shown in Telegram clients. The same sync can run automatically at startup by
setting `TELEGRAM_BOT_NAME` and optional `TELEGRAM_BOT_NAME_LANGUAGE_CODE`.

Usage: `/setmyname <name> [language=<code>]` or `/setmyname --clear [language=<code>]`

Examples:

- `/setmyname Claude Agent`
- `/setmyname Claude Agent language=ru`
- `/setmyname --clear language=ru` to clear the localized Russian name

- Telegram limits `name` to 0-64 characters; empty name clears the selected
  default or localized name.
- The method does not require chat administrator rights and does not need
  special update types, but it changes the bot's public profile and is guarded
  like the other admin commands.
- Rollback is to run `/setmyname` again with the previous name, clear the
  configured env values and restart, or restore the name through BotFather.

It is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
**not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
is empty, the command is disabled. The global rate-limit middleware still
applies.

### Set bot short description

The restricted `/setmyshortdescription` command calls Telegram Bot API
`setMyShortDescription` through aiogram's typed
`Bot.set_my_short_description()` wrapper. It updates the public bot profile
short description shown in Telegram clients. The same sync can run
automatically at startup by setting `TELEGRAM_BOT_SHORT_DESCRIPTION` and
optional `TELEGRAM_BOT_SHORT_DESCRIPTION_LANGUAGE_CODE`.

Usage: `/setmyshortdescription <short_description> [language=<code>]` or `/setmyshortdescription --clear [language=<code>]`

Examples:

- `/setmyshortdescription Claude agent`
- `/setmyshortdescription Claude agent language=ru`
- `/setmyshortdescription --clear language=ru` to clear the localized Russian short description

- Telegram limits `short_description` to 0-120 characters; empty short
  description clears the selected default or localized short description.
- The method does not require chat administrator rights and does not need
  special update types, but it changes the bot's public profile and is guarded
  like the other admin commands.
- Rollback is to run `/setmyshortdescription` again with the previous short
  description, clear the configured env values and restart, or restore it
  through BotFather.

It is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
**not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
is empty, the command is disabled. The global rate-limit middleware still
applies.

### Get bot short description

The restricted `/getmyshortdescription` command calls Telegram Bot API
`getMyShortDescription` through aiogram's typed
`Bot.get_my_short_description()` wrapper. It is a read-only diagnostic for
checking the default or localized bot short description that Telegram currently
serves after startup sync, `/setmyshortdescription` or BotFather changes.
Startup also audits the configured language variant after optional
`TELEGRAM_BOT_SHORT_DESCRIPTION` sync.

Usage: `/getmyshortdescription [language=<code>]`

Examples:

- `/getmyshortdescription`
- `/getmyshortdescription language=ru`

- Telegram accepts only optional `language_code` and returns
  `BotShortDescription`.
- The method does not require chat administrator rights and does not need
  special update types.
- The command is admin-only because profile diagnostics belong to the
  reproducible BotFather/startup-sync operational flow.

It is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
**not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
is empty, the command is disabled. The global rate-limit middleware still
applies.

### Set bot description

The restricted `/setmydescription` command calls Telegram Bot API
`setMyDescription` through aiogram's typed `Bot.set_my_description()` wrapper.
It updates the public bot profile description shown in Telegram clients. The
same sync can run automatically at startup by setting
`TELEGRAM_BOT_DESCRIPTION` and optional
`TELEGRAM_BOT_DESCRIPTION_LANGUAGE_CODE`.

Usage: `/setmydescription <description> [language=<code>]` or `/setmydescription --clear [language=<code>]`

Examples:

- `/setmydescription Claude agent for Telegram`
- `/setmydescription Claude agent for Telegram language=ru`
- `/setmydescription --clear language=ru` to clear the localized Russian description

- Telegram limits `description` to 0-512 characters; empty description clears
  the selected default or localized description.
- The method does not require chat administrator rights and does not need
  special update types, but it changes the bot's public profile and is guarded
  like the other admin commands.
- Rollback is to run `/setmydescription` again with the previous description,
  clear the configured env values and restart, or restore the description
  through BotFather.

It is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
**not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
is empty, the command is disabled. The global rate-limit middleware still
applies.

### Get bot description

The restricted `/getmydescription` command calls Telegram Bot API
`getMyDescription` through aiogram's typed `Bot.get_my_description()` wrapper.
It is a read-only diagnostic for checking the default or localized bot
description that Telegram currently serves after startup sync,
`/setmydescription` or BotFather changes. Startup also audits the configured
language variant after optional `TELEGRAM_BOT_DESCRIPTION` sync.

Usage: `/getmydescription [language=<code>]`

Examples:

- `/getmydescription`
- `/getmydescription language=ru`

- Telegram accepts only optional `language_code` and returns `BotDescription`.
- The method does not require chat administrator rights and does not need
  special update types.
- The command is admin-only because profile diagnostics belong to the
  reproducible BotFather/startup-sync operational flow.

It is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
**not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
is empty, the command is disabled. The global rate-limit middleware still
applies.

### Get bot name

The restricted `/getmyname` command calls Telegram Bot API `getMyName` through
aiogram's typed `Bot.get_my_name()` wrapper. It is a read-only diagnostic for
checking the default or localized bot display name that Telegram currently
serves after startup sync, `/setmyname` or BotFather changes. Startup also
audits the configured language variant after optional `TELEGRAM_BOT_NAME` sync.

Usage: `/getmyname [language=<code>]`

Examples:

- `/getmyname`
- `/getmyname language=ru`

- Telegram accepts only optional `language_code` and returns `BotName`.
- The method does not require chat administrator rights and does not need
  special update types.
- The command is admin-only because profile diagnostics belong to the
  reproducible BotFather/startup-sync operational flow.

It is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
**not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
is empty, the command is disabled. The global rate-limit middleware still
applies.

### Get bot commands

The restricted `/getmycommands` command calls Telegram Bot API `getMyCommands`
through aiogram's typed `Bot.get_my_commands()` wrapper. It is a read-only
diagnostic for checking the command menu that Telegram currently serves for the
default or selected scope/language after `/setmycommands`, `/deletemycommands`
or BotFather changes.

Usage: `/getmycommands [scope=<scope>] [chat_id=<id>] [user_id=<id>] [language=<code>]`

Examples:

- `/getmycommands`
- `/getmycommands scope=chat chat_id=-100123 language=en`
- `/getmycommands scope=chat_member chat_id=-100123 user_id=123456 language=uk`

Supported scopes: `default`, `all_private_chats`, `all_group_chats`,
`all_chat_administrators`, `chat`, `chat_administrators`, `chat_member`.

- `chat` and `chat_administrators` require `chat_id`;
- `chat_member` requires both `chat_id` and `user_id`;
- `language` is optional and targets a localized command menu;
- the bot does not need chat administrator rights, but the command can expose
  operational command-menu configuration and is guarded like the other admin
  diagnostics.

It is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
**not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
is empty, the command is disabled. The global rate-limit middleware still
applies.

### Delete bot commands

The restricted `/deletemycommands` command calls Telegram Bot API
`deleteMyCommands` through aiogram's typed `Bot.delete_my_commands()` wrapper.
It clears the command menu for the default or selected scope/language before a
fresh `/setmycommands` synchronization.

Usage: `/deletemycommands [scope=<scope>] [chat_id=<id>] [user_id=<id>] [language=<code>]`

Examples:

- `/deletemycommands`
- `/deletemycommands scope=chat chat_id=-100123 language=en`
- `/deletemycommands scope=chat_member chat_id=-100123 user_id=123456 language=uk`

Supported scopes: `default`, `all_private_chats`, `all_group_chats`,
`all_chat_administrators`, `chat`, `chat_administrators`, `chat_member`.

- `chat` and `chat_administrators` require `chat_id`;
- `chat_member` requires both `chat_id` and `user_id`;
- `language` is optional and targets a localized command menu;
- the bot does not need chat administrator rights, but the command changes the
  bot's public UI and is guarded like the other admin commands;
- rollback is to run `/setmycommands` again for the intended scope/language or
  restore commands via BotFather.

It is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
**not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
is empty, the command is disabled. The global rate-limit middleware still
applies.

`forwardMessage` forwards a single message; forwarding a whole album as a group
is the job of `forwardMessages`, exposed as `/forwards`.

### Forward several messages for moderation

The restricted `/forwards` command calls Telegram Bot API `forwardMessages`
through aiogram's typed `Bot.forward_messages()` wrapper. It serves the same
support/moderation scenario as `/forward`, but moves a batch of messages at
once and, unlike calling `/forward` repeatedly, **preserves album grouping**:
messages that originally belonged to one album are re-sent together as an album.

Usage: `/forwards <from_chat_id> <message_id> [<message_id> ...] [share]`

- the messages are always forwarded into the chat where the command was issued;
- provide 1-100 message ids in strictly increasing order, as Telegram requires;
  the command validates both bounds before calling Telegram;
- the forwarded copies are protected from further forwarding and saving by
  default (`protect_content=true`), so moderated content is not leaked further;
  append `share` to drop that protection;
- Telegram skips messages it cannot forward (service messages or messages whose
  original already has protected content) instead of failing the whole batch, so
  the success message reports how many of the requested messages were actually
  forwarded;
- the bot must be able to access `from_chat_id` (it must be a member of that
  chat); otherwise Telegram returns an error that the command reports back.

Because the command relays content between chats, it is guarded like the other
admin commands:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- the global rate-limit middleware still applies.

### Copy messages for moderation

The restricted `/copy` command calls Telegram Bot API `copyMessage` through
aiogram's typed `Bot.copy_message()` wrapper. Like `/forward` it serves a
support/moderation scenario, but it differs in an important way: `copyMessage`
re-sends the message content as a **new message with no link to the original
sender** (there is no "forwarded from" header), so an operator can review or
re-post moderated content without exposing the source.

Usage: `/copy <from_chat_id> <message_id> [share]`

- the message is always copied into the chat where the command was issued;
- the copied message is protected from further forwarding and saving by default
  (`protect_content=true`), so moderated content is not leaked further; append
  `share` to drop that protection;
- Telegram cannot copy service messages, paid media, giveaway/giveaway-winners
  and invoice messages, and the bot must be able to access `from_chat_id` (it
  must be a member of that chat). Such cases return a Telegram error that the
  command reports back instead of copying;
- on success Telegram returns only the new `MessageId`, not a full `Message`.

Because the command relays content between chats, it is guarded like the other
admin commands:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- the global rate-limit middleware still applies.

`copyMessage` copies a single message; copying a whole album as a group is the
job of `copyMessages`, exposed as `/copies`.

### Copy several messages for moderation

The restricted `/copies` command calls Telegram Bot API `copyMessages` through
aiogram's typed `Bot.copy_messages()` wrapper. It serves the same
support/moderation scenario as `/copy`, but moves a batch of messages at once.
Like `/copy` the copies have **no link to the original sender** (there is no
"forwarded from" header), and like `/forwards` it **preserves album grouping**:
messages that originally belonged to one album are re-sent together as an album.

Usage: `/copies <from_chat_id> <message_id> [<message_id> ...] [share] [nocaption]`

- the messages are always copied into the chat where the command was issued;
- provide 1-100 message ids in strictly increasing order, as Telegram requires;
  the command validates both bounds before calling Telegram;
- the copied messages are protected from further forwarding and saving by
  default (`protect_content=true`), so moderated content is not leaked further;
  append `share` to drop that protection;
- append `nocaption` to copy the messages without their original captions
  (`remove_caption=true`); unlike `/copy`, `copyMessages` cannot set a new
  caption, it can only drop the existing ones. Both keywords may be combined at
  the end in any order;
- Telegram skips messages it cannot copy (service, giveaway/giveaway-winners and
  invoice messages) instead of failing the whole batch, so the success message
  reports how many of the requested messages were actually copied;
- the bot must be able to access `from_chat_id` (it must be a member of that
  chat); otherwise Telegram returns an error that the command reports back.

Because the command relays content between chats, it is guarded like the other
admin commands:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- the global rate-limit middleware still applies.

### Send a photo

The restricted `/photo` command calls Telegram Bot API `sendPhoto` through
aiogram's typed `Bot.send_photo()` wrapper. It lets an operator deliver a
generated or received image into the chat as a **real Telegram photo** instead
of only a textual interpretation.

Usage: `/photo <url_or_file_id> [caption]`

- the photo is always sent into the chat where the command was issued;
- the photo reference is either an HTTP(S) URL that Telegram fetches itself or a
  `file_id` of a photo that already exists on Telegram servers;
- the caption is optional, may contain spaces, and is limited to 1024
  characters (the command validates this bound before calling Telegram);
- Telegram limits the photo to 10 MB, its total width+height to 10000 and its
  width/height ratio to 20; an invalid reference or oversized image returns a
  Telegram error that the command reports back instead of sending.

Because the command makes the bot post content, it is guarded like the other
admin commands:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- the global rate-limit middleware still applies.

### Send an audio file

The restricted `/audio` command calls Telegram Bot API `sendAudio` through
aiogram's typed `Bot.send_audio()` wrapper. It lets an operator deliver a
generated or received sound clip into the chat as a **playable music track**
instead of only a textual interpretation.

Usage: `/audio <url_or_file_id> [caption]`

- the audio is always sent into the chat where the command was issued;
- the audio reference is either an HTTP(S) URL that Telegram fetches itself or a
  `file_id` of an audio file that already exists on Telegram servers;
- the caption is optional, may contain spaces, and is limited to 1024
  characters (the command validates this bound before calling Telegram);
- Telegram expects the audio in the `.MP3` or `.M4A` format and limits a file
  sent by URL or `file_id` to 20 MB; an invalid reference or unsupported file
  returns a Telegram error that the command reports back instead of sending.

Because the command makes the bot post content, it is guarded like the other
admin commands:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- the global rate-limit middleware still applies.

### Send a live photo

The restricted `/livephoto` command calls Telegram Bot API `sendLivePhoto`
(introduced in Bot API 10.0). Because the pinned `aiogram==3.3.0` predates this
method and ships no typed wrapper, the command goes through an **isolated raw
Bot API helper** (`bot/services/send_live_photo.py`) that POSTs the request
over `httpx` instead of using a typed aiogram method. It lets an operator post
a **live photo** — a short looping video paired with its static cover photo —
into the chat instead of only a textual interpretation.

Usage: `/livephoto <live_photo_file_id> <photo_file_id> [caption]`

- the live photo is always sent into the chat where the command was issued;
- Telegram does **not** support sending live photos by URL, so both references
  must be `file_id` values of media that already exist on Telegram servers
  (`live_photo` is the video, `photo` is its static cover);
- the `live_photo` video must be at most 10 seconds long and 10 MB;
- the caption is optional, may contain spaces, and is limited to 1024
  characters (the command validates this bound before calling Telegram);
- an invalid reference or unsupported file returns a Telegram error that the
  command reports back instead of sending.

Because the command makes the bot post content, it is guarded like the other
admin commands:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- the global rate-limit middleware still applies.

### Send a file as a document

The restricted `/document` command calls Telegram Bot API `sendDocument`
through aiogram's typed `Bot.send_document()` wrapper. It lets an operator
return large text, PDF or source artifacts as a **downloadable document** when
a plain message does not fit instead of only a textual interpretation.

Usage: `/document <url_or_file_id> [caption]`

- the document is always sent into the chat where the command was issued;
- the document reference is either an HTTP(S) URL that Telegram fetches itself
  or a `file_id` of a file that already exists on Telegram servers;
- the caption is optional, may contain spaces, and is limited to 1024
  characters (the command validates this bound before calling Telegram);
- Telegram limits a file sent by URL to 20 MB; an invalid reference returns a
  Telegram error that the command reports back instead of sending.

Because the command makes the bot post content, it is guarded like the other
admin commands:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- the global rate-limit middleware still applies.

### Send a video

The restricted `/video` command calls Telegram Bot API `sendVideo` through
aiogram's typed `Bot.send_video()` wrapper. It lets an operator deliver a
generated or received clip into the chat as a **playable video** instead of
only a textual interpretation.

Usage: `/video <url_or_file_id> [caption]`

- the video is always sent into the chat where the command was issued;
- the video reference is either an HTTP(S) URL that Telegram fetches itself or a
  `file_id` of a video that already exists on Telegram servers;
- the caption is optional, may contain spaces, and is limited to 1024
  characters (the command validates this bound before calling Telegram);
- Telegram clients support MPEG4 videos (other formats may be sent as a
  document) and limit a file sent by URL to 20 MB; an invalid reference or
  unsupported file returns a Telegram error that the command reports back
  instead of sending.

Because the command makes the bot post content, it is guarded like the other
admin commands:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- the global rate-limit middleware still applies.

### Send a video note

The restricted `/videonote` command calls Telegram Bot API `sendVideoNote`
through aiogram's typed `Bot.send_video_note()` wrapper. It lets an operator
deliver a generated or received clip into the chat as a **rounded square video
message** (video note) instead of only a textual interpretation.

Usage: `/videonote <file_id>`

- the video note is always sent into the chat where the command was issued;
- the reference must be a `file_id` of a video note that already exists on
  Telegram servers (or an uploaded file); unlike `/video`, Telegram currently
  does **not** support sending video notes by URL;
- video notes have no caption, so any text after the `file_id` is ignored;
- an invalid `file_id` returns a Telegram error that the command reports back
  instead of sending.

Because the command makes the bot post content, it is guarded like the other
admin commands:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- the global rate-limit middleware still applies.

### Send an animation

The restricted `/animation` command calls Telegram Bot API `sendAnimation`
through aiogram's typed `Bot.send_animation()` wrapper. It lets an operator
deliver a generated or received GIF into the chat as a **playable looping
animation** instead of only a textual interpretation.

Usage: `/animation <url_or_file_id> [caption]`

- the animation is always sent into the chat where the command was issued;
- the animation reference is either an HTTP(S) URL that Telegram fetches itself
  or a `file_id` of an animation that already exists on Telegram servers;
- the caption is optional, may contain spaces, and is limited to 1024
  characters (the command validates this bound before calling Telegram);
- Telegram delivers GIF and H.264/MPEG-4 AVC files without sound and limits a
  file sent by URL to 20 MB; an invalid reference or unsupported file returns a
  Telegram error that the command reports back instead of sending.

Because the command makes the bot post content, it is guarded like the other
admin commands:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- the global rate-limit middleware still applies.

### Send a sticker

The restricted `/sticker` command calls Telegram Bot API `sendSticker` through
aiogram's typed `Bot.send_sticker()` wrapper. It lets an operator deliver a
sticker or custom emoji into the current chat without involving the Claude chat
flow.

Usage: `/sticker <url_or_file_id> [emoji]`

- the sticker is always sent into the chat where the command was issued;
- the sticker reference is a `file_id` of a sticker already on Telegram servers
  or an HTTP(S) URL Telegram can fetch for static `.WEBP` stickers;
- video stickers can only be sent by `file_id`, and animated stickers cannot be
  sent by HTTP URL;
- the optional emoji hint is passed to Telegram for newly uploaded stickers;
- static and animated stickers are limited to 512 KB, video stickers are
  limited to 256 KB, and sticker dimensions must fit in a 512x512 square.

Because the command makes the bot post content, it is guarded like the other
admin commands:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- Telegram errors such as invalid file references, unsupported formats or chat
  permission failures are reported back to the operator;
- the global rate-limit middleware still applies.

### Create a sticker set

The restricted `/createnewstickerset` command calls Telegram Bot API
`createNewStickerSet` through an isolated raw helper because the project pins
`aiogram==3.3.0`. It covers the first lifecycle step for sticker/custom emoji
sets by creating a set with one pre-uploaded sticker `file_id`.

Usage: `/createnewstickerset <user_id> <name> <sticker_type> <sticker_format> <sticker_file_id> <emoji[,emoji...]> <title>`

- use `/uploadstickerfile` first when the asset is a local file on the bot host;
- `sticker_type` must be `regular`, `mask` or `custom_emoji`;
- `sticker_format` must be `static`, `animated` or `video`;
- the sticker set name must be unique and follow Telegram's bot-owned naming
  rule, ending with `_by_<bot_username>`;
- the target user must be the owner of the created set.

Because the command creates Telegram state, it is guarded like the other admin
commands:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- Telegram validation and rate-limit errors are reported back to the operator;

### Add a sticker to a set

The restricted `/addstickertoset` command calls Telegram Bot API
`addStickerToSet` through the same raw Bot API path as sticker set creation.
It appends one pre-uploaded sticker `file_id` to an existing set owned by the
target user.

Usage: `/addstickertoset <user_id> <name> <sticker_format> <sticker_file_id> <emoji[,emoji...]>`

- use `/uploadstickerfile` first when the asset is a local file on the bot host;
- `sticker_format` must be `static`, `animated` or `video`;
- the target user must own the existing sticker set;
- Telegram validation and rate-limit errors are reported back to the operator.
- rollback is manual: delete or replace the created sticker set through the
  Telegram sticker lifecycle tools.

### Replace a sticker in a set

The restricted `/replacestickerinset` command calls Telegram Bot API
`replaceStickerInSet` through an isolated raw helper because the project pins
`aiogram==3.3.0`. It replaces one existing sticker/custom emoji in a bot-owned
set with a new pre-uploaded sticker `file_id`.

Usage: `/replacestickerinset <user_id> <name> <old_sticker_file_id> <sticker_format> <new_sticker_file_id> <emoji[,emoji...]>`

- use `/getstickerset` first to inspect current sticker file ids;
- use `/uploadstickerfile` first when the replacement asset is a local file on
  the bot host;
- `sticker_format` must be `static`, `animated` or `video`;
- the target user must own the existing sticker set;
- Telegram only allows replacing stickers in sets created by the bot;
- no special update types are required because the scenario starts from a
  normal admin command message;
- Telegram validation and rate-limit errors are reported back to the operator;
- rollback is manual: call `/replacestickerinset` again with the previous
  sticker file id and emoji metadata, or use the Telegram sticker lifecycle
  tools.

### Set sticker position in a set

The restricted `/setstickerposition` command calls Telegram Bot API
`setStickerPositionInSet` through an isolated raw helper because the project
pins `aiogram==3.3.0`. It moves an existing sticker to a zero-based position
inside its current sticker set and completes the basic create/add/reorder
sticker set lifecycle.

Usage: `/setstickerposition <sticker_file_id> <position>`

- use `/getstickerset` first to inspect the current order and sticker file ids;
- `position` is zero-based and must be a non-negative integer;
- Telegram only allows moving stickers in sets created by the bot;
- no special update types are required because the scenario starts from a
  normal admin command message;
- Telegram validation and rate-limit errors are reported back to the operator;
- rollback is manual: call `/setstickerposition` again with the previous
  position or reorder the set through Telegram sticker lifecycle tools.

### Set sticker emoji list

The restricted `/setstickeremojis` command calls Telegram Bot API
`setStickerEmojiList` through an isolated raw helper because the project pins
`aiogram==3.3.0`. It replaces the emoji metadata for an existing sticker or
custom emoji in its current sticker set and extends the optional creative/media
module without affecting the main Claude chat flow.

Usage: `/setstickeremojis <sticker_file_id> <emoji[,emoji...]>`

- use `/getstickerset` first to inspect current sticker file ids and emoji
  metadata;
- `emoji_list` must contain at least one non-empty comma-separated emoji;
- Telegram only allows updating stickers in sets created by the bot;
- no special update types are required because the scenario starts from a
  normal admin command message;
- Telegram validation and rate-limit errors are reported back to the operator;
- rollback is manual: call `/setstickeremojis` again with the previous emoji
  list captured from `/getstickerset`.

### Set sticker mask position

The restricted `/setstickermaskposition` command calls Telegram Bot API
`setStickerMaskPosition` through an isolated raw helper because the project
pins `aiogram==3.3.0`. It changes or clears the `MaskPosition` metadata for an
existing mask sticker in a bot-created sticker set and extends the optional
creative/media module without affecting the main Claude chat flow.

Usage: `/setstickermaskposition <sticker_file_id> <point> <x_shift> <y_shift> <scale>`
Clear: `/setstickermaskposition <sticker_file_id> -`

- use `/getstickerset` first to inspect current sticker file ids and mask
  metadata;
- `point` must be `forehead`, `eyes`, `mouth` or `chin`;
- `x_shift` and `y_shift` are floats measured in mask widths/heights relative
  to the selected face point, and `scale` must be greater than zero;
- Telegram only allows updating mask stickers in sets created by the bot;
- no special update types are required because the scenario starts from a
  normal admin command message;
- Telegram validation and rate-limit errors are reported back to the operator;
- rollback is manual: call `/setstickermaskposition` again with the previous
  mask position from `/getstickerset`, or pass `-` to remove the mask position.

### Set sticker keywords

The restricted `/setstickerkeywords` command calls Telegram Bot API
`setStickerKeywords` through an isolated raw helper because the project pins
`aiogram==3.3.0`. It replaces the search keywords for an existing sticker in
its current sticker set and extends the optional creative/media module without
affecting the main Claude chat flow.

Usage: `/setstickerkeywords <sticker_file_id> <keyword[,keyword...]|->`

- use `/getstickerset` first to inspect current sticker file ids;
- `keywords` accepts up to 20 comma-separated strings; pass `-` to clear the
  keyword list;
- Telegram only allows updating stickers in sets created by the bot;
- no special update types are required because the scenario starts from a
  normal admin command message;
- Telegram validation and rate-limit errors are reported back to the operator;
- rollback is manual: call `/setstickerkeywords` again with the previous
  keywords captured from operational notes or Telegram tooling.

### Set sticker set title

The restricted `/setstickersettitle` command calls Telegram Bot API
`setStickerSetTitle` through an isolated raw helper because the project pins
`aiogram==3.3.0`. It changes the title of a bot-created sticker set by set
name and extends the optional creative/media module without affecting the main
Claude chat flow.

Usage: `/setstickersettitle <sticker_set_name> <title>`

- use `/getstickerset` first to inspect the current set name and title;
- `title` is required and limited to 64 characters;
- Telegram only allows updating sticker sets created by the bot;
- no special update types are required because the scenario starts from a
  normal admin command message;
- Telegram validation and rate-limit errors are reported back to the operator;
- rollback is manual: call `/setstickersettitle` again with the previous title
  captured from `/getstickerset` or operational notes.

### Set sticker set thumbnail

The restricted `/setstickersetthumbnail` command calls Telegram Bot API
`setStickerSetThumbnail` through an isolated raw helper because the project pins
`aiogram==3.3.0`. It sets or clears the thumbnail of a bot-created sticker set
by set name, owner `user_id`, sticker `format`, and thumbnail `file_id`.

Usage: `/setstickersetthumbnail <user_id> <sticker_set_name> <format> <thumbnail_file_id|->`

- use `/getstickerset` first to inspect the current set name and thumbnail;
- `format` must be `static`, `animated`, or `video`;
- pass `-` as `thumbnail_file_id` to clear the current thumbnail;
- Telegram only allows updating sticker sets created by the bot;
- no special update types are required because the scenario starts from a
  normal admin command message;
- Telegram validation and rate-limit errors are reported back to the operator;
- rollback is manual: call `/setstickersetthumbnail` again with the previous
  thumbnail file id captured from `/getstickerset` or operational notes.

### Set custom emoji sticker set thumbnail

The restricted `/setcustomemojithumbnail` command calls Telegram Bot API
`setCustomEmojiStickerSetThumbnail` through an isolated raw helper because the
project pins `aiogram==3.3.0`. It sets or clears the thumbnail of a bot-created
custom emoji sticker set by set name and a `custom_emoji_id` from that set.

Usage: `/setcustomemojithumbnail <sticker_set_name> <custom_emoji_id|->`

- use `/getstickerset` first to inspect the current set name and custom emoji
  ids;
- pass `-` as `custom_emoji_id` to clear the current thumbnail;
- Telegram only allows updating custom emoji sticker sets created by the bot;
- no special update types are required because the scenario starts from a
  normal admin command message;
- Telegram validation and rate-limit errors are reported back to the operator;
- rollback is manual: call `/setcustomemojithumbnail` again with the previous
  custom emoji id captured from `/getstickerset` or operational notes.

### Delete a sticker from a set

The restricted `/deletestickerfromset` command calls Telegram Bot API
`deleteStickerFromSet` through an isolated raw helper because the project pins
`aiogram==3.3.0`. It removes an existing sticker from its current sticker set
and completes the create/add/reorder/delete sticker set lifecycle.

Usage: `/deletestickerfromset <sticker_file_id>`

- use `/getstickerset` first to inspect current sticker file ids;
- Telegram only allows deleting stickers from sets created by the bot;
- no special update types are required because the scenario starts from a
  normal admin command message;
- Telegram validation and rate-limit errors are reported back to the operator;
- rollback is manual: add the sticker back with `/addstickertoset` using the
  original sticker file id and emoji metadata.

### Delete a sticker set

The restricted `/deletestickerset` command calls Telegram Bot API
`deleteStickerSet` through an isolated raw helper because the project pins
`aiogram==3.3.0`. It removes an entire bot-created sticker set by set name and
finishes the sticker set lifecycle for destructive cleanup.

Usage: `/deletestickerset <sticker_set_name>`

- use `/getstickerset` first to verify the target set name and save any
  rollback metadata;
- Telegram only allows deleting sticker sets created by the bot;
- the command is deny-by-default and only runs from `TELEGRAM_ADMIN_CHAT_IDS`;
- no special update types are required because the operation starts from an
  admin command message;
- rollback is operational: recreate the set with `/createnewstickerset`, then
  add the needed stickers back with `/addstickertoset` from saved file ids and
  emoji metadata.

### Send a voice message

The restricted `/voice` command calls Telegram Bot API `sendVoice` through
aiogram's typed `Bot.send_voice()` wrapper. It lets an operator deliver a
generated or received audio clip into the chat as a **playable voice message**
(shown as a waveform) instead of only a textual interpretation.

Usage: `/voice <url_or_file_id> [caption]`

- the voice message is always sent into the chat where the command was issued;
- the voice reference is either an HTTP(S) URL that Telegram fetches itself or a
  `file_id` of a voice message that already exists on Telegram servers;
- the caption is optional, may contain spaces, and is limited to 1024
  characters (the command validates this bound before calling Telegram);
- for playback as a voice message Telegram expects an `.OGG` file encoded with
  OPUS, or an `.MP3` or `.M4A` file, and limits a file sent by URL to 20 MB; an
  invalid reference or unsupported file returns a Telegram error that the
  command reports back instead of sending.

Because the command makes the bot post content, it is guarded like the other
admin commands:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- the global rate-limit middleware still applies.

### Send paid media

The restricted `/paidmedia` command calls Telegram Bot API `sendPaidMedia`
(introduced in Bot API 7.6). Because the pinned `aiogram==3.3.0` predates this
method and ships no typed wrapper, the command goes through an **isolated raw
Bot API helper** (`bot/services/send_paid_media.py`) that POSTs the request
over `httpx` instead of using a typed aiogram method. It lets an operator post
a **paid photo** that users must pay for with Telegram Stars before they can see
it, instead of only a textual interpretation.

Usage: `/paidmedia <star_count> <url_or_file_id> [caption]`

- the paid media is always sent into the chat where the command was issued;
- `star_count` is the price in Telegram Stars and must be between 1 and 25000
  (the command validates this bound before calling Telegram);
- when the chat is a channel, all Telegram Star proceeds are credited to the
  channel's balance; otherwise they are credited to the bot's balance;
- the media reference is either an HTTP(S) URL that Telegram fetches itself or a
  `file_id` of a photo that already exists on Telegram servers (the command
  sends a single photo; the helper accepts the full `media` array for up to 10
  photo/video items);
- the caption is optional, may contain spaces, and is limited to 1024
  characters (the command validates this bound before calling Telegram);
- an invalid reference, insufficient bot rights or unsupported file returns a
  Telegram error that the command reports back instead of sending.

Because the command makes the bot post monetized content, it is guarded like the
other admin commands:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- the global rate-limit middleware still applies.

### Shipping queries

Telegram `answerShippingQuery` is intentionally blocked by product scope. The
bot exposes Telegram Stars test invoices, invoice links and paid media, but it
does not sell physical goods, request shipping addresses or keep a
shipping-options catalog. Accepting a `shipping_query` without that domain would
create a false checkout path, so no `shipping_query` handler is registered and
`bot/services/answer_shipping_query.py` always raises a dedicated
blocked-by-product error before any Telegram request can be made.

To enable this method later, add a physical-goods checkout design first:
signed/idempotent invoice payloads, allowed `shipping_query` updates, validated
shipping options, fulfillment and rollback policy, audit logs and security
tests. This flow is separate from `free-claude-code`.

### Web App prepared messages

The restricted `/answerwebappquery`, `/savepreparedinline` and
`/savepreparedkeyboard` commands cover the Mini App integration layer around
Telegram Web Apps, prepared inline messages and prepared keyboard buttons.

`/answerwebappquery <web_app_query_id> <result_json>` calls
`answerWebAppQuery` through aiogram's typed wrapper and sends one
`InlineQueryResult` on behalf of the user who opened the Web App.

`/savepreparedinline <user_id> <result_json> [allow_user_chats=true|false]
[allow_bot_chats=true|false] [allow_group_chats=true|false]
[allow_channel_chats=true|false]` calls `savePreparedInlineMessage` through an
isolated raw Bot API helper because pinned `aiogram==3.3.0` has no typed wrapper
for that Bot API 10.0 method. The result JSON must be one `InlineQueryResult`;
Telegram returns a `PreparedInlineMessage` id that can be used by the next step.

`/savepreparedkeyboard <user_id> <prepared_message_id>` calls
`savePreparedKeyboardButton` through
`bot/services/save_prepared_keyboard_button.py`, another isolated raw Bot API
helper for Bot API 10.0. It stores the prepared keyboard button for the Mini App
user and references a prepared inline message id created earlier.

Security and operational notes:

- these flows are admin-triggered diagnostics/integration commands and do not
  call `free-claude-code`;
- they are only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and do
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the commands are disabled;
- the Mini App must validate Telegram init data and bind the action to the
  expected user before an operator stores a prepared keyboard button; this bot
  command validates local argument shape, while Telegram validates user
  eligibility, prepared message ids and Bot API authorization;
- no special chat administrator right is needed for these commands themselves,
  because they operate on a user/Web App context rather than a target group;
- no extra update type is required for the admin command path, but a production
  Mini App flow should receive and verify Web App init data or `web_app_data`
  outside this command before calling it;
- rollback is explicit: create and save a replacement prepared message/button
  or remove the Mini App entry point/menu button that exposes the prepared
  keyboard button;
- Telegram validation, authorization, transport and rate-limit errors are
  reported back to the admin chat, and the global rate-limit middleware still
  applies.

### Send a location

The restricted `/location` command calls Telegram Bot API `sendLocation`
through aiogram's typed `Bot.send_location()` wrapper. It lets an operator post
a **point on the map** into the chat as a real Telegram location instead of only
a textual interpretation.

Usage: `/location <latitude> <longitude>`

- the location is always sent into the chat where the command was issued;
- `latitude` and `longitude` are given in decimal degrees; latitude must be
  between -90 and 90 and longitude between -180 and 180 (the command validates
  these bounds before calling Telegram);
- locations have no caption, so any text after the coordinates is ignored;
- coordinates can reveal a person's whereabouts, so they are intentionally kept
  out of the structured logs;
- an invalid request (for example a chat the bot cannot post to) returns a
  Telegram error that the command reports back instead of sending.

Because the command makes the bot post a location, it is guarded like the other
admin commands:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- the global rate-limit middleware still applies.

### Send a venue

The restricted `/venue` command calls Telegram Bot API `sendVenue` through
aiogram's typed `Bot.send_venue()` wrapper. It lets an operator post a **venue**
into the chat as a real Telegram venue — a named place with a title and an
address pinned on the map — instead of only a textual interpretation.

Usage: `/venue <latitude> <longitude> <title> | <address>`

- the venue is always sent into the chat where the command was issued;
- `latitude` and `longitude` are given in decimal degrees; latitude must be
  between -90 and 90 and longitude between -180 and 180 (the command validates
  these bounds before calling Telegram);
- the `title` and the `address` follow the coordinates and are separated by a
  vertical bar (`|`); both may contain spaces and both are required, so the
  command shows usage when the separator is missing or either side is empty;
- a venue exposes a precise place and address, so they are intentionally kept
  out of the structured logs;
- an invalid request (for example a chat the bot cannot post to) returns a
  Telegram error that the command reports back instead of sending.

Because the command makes the bot post a venue, it is guarded like the other
admin commands:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- the global rate-limit middleware still applies.

### Edit a live location

The restricted `/editlivelocation` command calls Telegram Bot API
`editMessageLiveLocation` through an isolated raw Bot API helper. It lets an
operator move an active live location message that was previously sent by the
bot, either by regular `chat_id` + `message_id` or by `inline_message_id`.

Usage: `/editlivelocation <chat_id> <message_id> <latitude> <longitude>`
Usage: `/editlivelocation inline=<inline_message_id> <latitude> <longitude>`

Optional flags: `accuracy=<0-1500>`, `heading=<1-360>`,
`proximity=<1-100000>`.

- latitude and longitude are decimal degrees and are validated before Telegram
  is called;
- `horizontal_accuracy`, `heading` and `proximity_alert_radius` follow
  Telegram's documented ranges;
- the command only edits active live locations sent by the bot, and Telegram
  returns a validation error when the target message cannot be edited;
- no special update type is required for the command path; the bot must have
  normal permission to edit its own target message in the destination chat;
- coordinates can reveal a person's whereabouts, so the service keeps them out
  of structured logs;
- rollback is another `/editlivelocation` call with the previous coordinates,
  or `stopMessageLiveLocation`/manual Telegram action when the location should
  no longer be live.

Because this is a message-management action, it is guarded like the other admin
commands:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- the command does not call `free-claude-code`; it is an operator action for
  streaming, moderation and media workflows that need to update an existing
  Telegram message;
- Telegram validation, authorization, transport and rate-limit errors are
  reported back to the admin chat, and the global rate-limit middleware still
  applies.

### Stop a live location

The restricted `/stoplivelocation` command calls Telegram Bot API
`stopMessageLiveLocation` through an isolated raw Bot API helper. It lets an
operator stop an active live location message that was previously sent by the
bot, either by regular `chat_id` + `message_id` or by `inline_message_id`.

Usage: `/stoplivelocation <chat_id> <message_id>`
Usage: `/stoplivelocation inline=<inline_message_id>`

- `message_id` is validated before Telegram is called;
- the command only stops active live locations sent by the bot, and Telegram
  returns a validation error when the target message cannot be edited;
- no special update type is required for the command path; the bot must have
  normal permission to edit its own target message in the destination chat;
- the service does not log coordinates or message contents, only target ids and
  whether inline mode/reply markup were used;
- rollback requires sending a new live location or restoring state manually in
  Telegram.

Because this is a message-management action, it is guarded like the other admin
commands:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- the command does not call `free-claude-code`; it is an operator action for
  streaming, moderation and media workflows that need to stop an existing
  Telegram live-location message;
- Telegram validation, authorization, transport and rate-limit errors are
  reported back to the admin chat, and the global rate-limit middleware still
  applies.

### Send a poll

The restricted `/poll` command calls Telegram Bot API `sendPoll` through
aiogram's typed `Bot.send_poll()` wrapper. It lets an operator post a native
**poll** into the chat — an interactive question with tappable answer options —
instead of only a textual interpretation.

Usage: `/poll <question> | <option> | <option> [| <option> ...]`

- the poll is always sent into the chat where the command was issued;
- the `question` comes first and the answer `options` follow, all separated by a
  vertical bar (`|`); the question and every option may contain spaces;
- provide 2-10 options; the question is limited to 300 characters and each
  option to 100 characters (the command validates these limits before calling
  Telegram);
- the command shows usage when there are no arguments, when the separator is
  missing so no option is given, or when the question or any option is empty;
- the question and the answer options are content the operator chose to
  broadcast, so they are intentionally kept out of the structured logs;
- the poll is sent with Telegram's defaults (anonymous, single-answer regular
  poll);
- an invalid request (for example a chat the bot cannot post to) returns a
  Telegram error that the command reports back instead of sending.

Because the command makes the bot post a poll, it is guarded like the other
admin commands:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- the global rate-limit middleware still applies.

### Stop a poll

The restricted `/stoppoll` command calls Telegram Bot API `stopPoll` through
aiogram's typed `Bot.stop_poll()` wrapper. It lets an operator close an active
native poll that was previously sent by the bot and returns Telegram's final
`Poll` state.

Usage: `/stoppoll <chat_id> <message_id>`

- `chat_id` may be a numeric chat id or a channel username such as `@channel`;
- `message_id` must be the positive id of the poll message;
- Telegram only stops polls sent by the bot, and the poll must still be open;
- no special update type is required, because the flow starts from a normal
  admin command message;
- Telegram permission/state/rate-limit errors are reported back to the admin
  chat.

The command is guarded like other message-management admin commands:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- the global rate-limit middleware still applies.

### Decline a suggested post

The restricted `/declinesuggestedpost` command calls Telegram Bot API
`declineSuggestedPost` through an isolated raw HTTP helper, because the pinned
`aiogram==3.3.0` does not include this Bot API 10.0 method. It lets an operator
decline a suggested post in a direct messages chat.

Usage: `/declinesuggestedpost <chat_id> <message_id> [comment]`

- `chat_id` may be a numeric direct messages chat id or a channel username such
  as `@channel`;
- `message_id` must be the positive id of the suggested post message;
- `comment`, when provided, is sent to the creator of the suggested post and
  must be 0-128 characters;
- Telegram validates that the target message is a declinable suggested post and
  that the bot has the `can_manage_direct_messages` administrator right in the
  corresponding channel chat;
- Telegram permission/state/rate-limit errors are reported back to the admin
  chat.

The command is guarded like other message-management admin commands:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- the global rate-limit middleware still applies.

### Approve a suggested post

The restricted `/approvesuggestedpost` command calls Telegram Bot API
`approveSuggestedPost` through an isolated raw HTTP helper, because the pinned
`aiogram==3.3.0` does not include this Bot API 10.0 method. It lets an operator
approve a suggested post in a direct messages chat.

Usage: `/approvesuggestedpost <chat_id> <message_id> [send_date]`

- `chat_id` may be a numeric direct messages chat id or a channel username such
  as `@channel`;
- `message_id` must be the positive id of the suggested post message;
- `send_date`, when provided, must be a positive Unix timestamp;
- Telegram validates that the target message is an approvable suggested post
  and that the bot has the required rights in the direct messages chat;
- Telegram permission/state/rate-limit errors are reported back to the admin
  chat.

The command is guarded like other message-management admin commands:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- the global rate-limit middleware still applies.

### Send a contact

The restricted `/contact` command calls Telegram Bot API `sendContact` through
aiogram's typed `Bot.send_contact()` wrapper. It lets an operator post a phone
**contact** into the chat — a name with a phone number that the recipient can
save to the address book — instead of only a textual interpretation.

Usage: `/contact <phone_number> <first_name> [| <last_name>]`

- the contact is always sent into the chat where the command was issued;
- the `phone_number` comes first as a single token, followed by the contact's
  `first_name`; an optional `last_name` follows after a vertical bar (`|`);
- the phone number and the first name are required and must be non-empty; the
  first name may contain spaces and the last name is optional;
- the command shows usage when there are no arguments, when the first name is
  missing, or when the first name is empty;
- the phone number and the contact's name are personal data the operator chose
  to share, so they are intentionally kept out of the structured logs;
- an invalid request (for example an invalid phone number or a chat the bot
  cannot post to) returns a Telegram error that the command reports back instead
  of sending.

Because the command makes the bot post a contact, it is guarded like the other
admin commands:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- the global rate-limit middleware still applies.

### Send a dice

The restricted `/dice` command calls Telegram Bot API `sendDice` through
aiogram's typed `Bot.send_dice()` wrapper. It lets an operator post an animated
**dice** into the chat — an animated emoji that shows a random value chosen by
Telegram — instead of only a textual interpretation.

Usage: `/dice [emoji]`

- the dice is always sent into the chat where the command was issued;
- without an emoji a 🎲 die is sent (Telegram's default);
- the optional emoji must be one of `🎲`, `🎯`, `🏀`, `⚽`, `🎳` or `🎰`; the
  value range depends on the emoji (1-6 for `🎲`, `🎯` and `🎳`, 1-5 for `🏀`
  and `⚽`, and 1-64 for `🎰`);
- the command shows usage when an unsupported emoji or more than one argument is
  supplied, and does not contact Telegram in that case;
- the dice carries no operator-provided content, so the chosen emoji and the
  sent message id are logged;
- an invalid request (for example a chat the bot cannot post to) returns a
  Telegram error that the command reports back instead of sending.

Because the command makes the bot post a dice, it is guarded like the other
admin commands:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- the global rate-limit middleware still applies.

### Show a chat action

The bot calls Telegram Bot API `sendChatAction` through aiogram's typed
`Bot.send_chat_action()` wrapper to show a transient status — such as
**typing…** — that tells the user it is busy. Telegram clears the status after
about five seconds or as soon as the bot posts a message.

This happens automatically while Claude/proxy handles a chat message: the bot
shows `typing…` and refreshes it until the reply is ready, so a noticeably long
request no longer leaves the chat silent. The behaviour is controlled by
`TELEGRAM_CHAT_ACTION_ENABLED` (default `true`); set it to `false` to keep the
chat silent during processing.

The restricted `/chataction` command lets an operator trigger a chat action on
demand, mostly for testing:

Usage: `/chataction [action]`

- the action is always shown in the chat where the command was issued;
- without an argument a `typing` status is shown;
- the optional action must be one of `typing`, `upload_photo`, `record_video`,
  `upload_video`, `record_voice`, `upload_voice`, `upload_document`,
  `choose_sticker`, `find_location`, `record_video_note` or
  `upload_video_note`;
- the command shows usage when an unsupported action or more than one argument
  is supplied, and does not contact Telegram in that case;
- the action carries no operator-provided content, so the chosen action and the
  target chat are logged;
- an invalid request (for example a chat the bot cannot post to) returns a
  Telegram error that the command reports back.

Because the command makes the bot act on the chat, it is guarded like the other
admin commands:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- the global rate-limit middleware still applies.

### Stream an ephemeral message draft

The bot can preview a streaming reply through Telegram Bot API
`sendMessageDraft` (introduced in Bot API 10.0). Because the pinned
`aiogram==3.3.0` predates this method and ships no typed wrapper, the request
goes through an **isolated raw Bot API helper**
(`bot/services/send_message_draft.py`) that POSTs over `httpx` instead of using a
typed aiogram method. A message draft is the **ephemeral text shown above the
input field**: Telegram displays it for about 30 seconds and animates it in place
when the bot sends a new draft with the same non-zero `draft_id`, so it is an
alternative to repeatedly calling `editMessageText` while Claude generates the
answer.

When `TELEGRAM_MESSAGE_DRAFT_ENABLED` is `true` (default `false`) and streaming
is enabled, the bot uses drafts for the live preview **in private chats only**
(Telegram limits the method to them): it shows an empty `Thinking…` placeholder,
refreshes the draft as new text arrives (throttled to avoid flooding the
endpoint), and then persists the finished answer as a normal message. Group and
channel chats keep the edit-based streaming. A failed draft preview never breaks
the reply — the bot logs it and falls back to sending the final message.

The restricted `/messagedraft` command lets an operator trigger a draft on
demand, mostly for testing:

Usage: `/messagedraft [text]`

- the draft is always shown in the chat where the command was issued, which must
  be a private chat (Telegram limits the method to them);
- without an argument an empty `Thinking…` placeholder draft is shown;
- the text is limited to 4096 characters (the command validates this bound
  before calling Telegram);
- the draft text is operator-provided content, so only its length and structural
  metadata are logged, never the text itself;
- an invalid request (for example a non-private chat) returns a Telegram error
  that the command reports back instead of sending.

Because the command makes the bot post a draft, it is guarded like the other
admin commands:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- the global rate-limit middleware still applies.

### Send a checklist

The restricted `/checklist` command calls Telegram Bot API `sendChecklist`
(introduced in Bot API 9.1). Because the pinned `aiogram==3.3.0` predates this
method and ships no typed wrapper, the command goes through an **isolated raw
Bot API helper** (`bot/services/send_checklist.py`) that POSTs the request over
`httpx` instead of using a typed aiogram method. It lets an operator post a
**checklist** — a titled list of tasks recipients can tick off — into the chat
instead of only a textual interpretation.

`sendChecklist` sends the message **on behalf of a connected business account**,
so the bot must be connected to one and you must supply that live business
connection id. It cannot be used as an ordinary chat command without
business-mode.

Usage: `/checklist <business_connection_id> <title> | <task> [| <task> ...]`

- the checklist is always sent into the chat where the command was issued;
- the business connection id comes first as a single token (no spaces), then the
  title and the tasks, all separated by a vertical bar;
- provide between 1 and 30 tasks (the command validates this bound before
  calling Telegram); the handler assigns sequential task ids starting at 1;
- the title is limited to 255 characters and each task to 100 characters (the
  command validates these bounds before calling Telegram); the title and every
  task may contain spaces and must be non-empty;
- the command shows usage when the business connection id, the title or any task
  is missing or empty, and does not contact Telegram in that case;
- the title and task texts are operator-provided content, so only the task count
  and the sent message id are logged;
- a missing or expired `business_connection_id`, insufficient business-connection
  rights or any other invalid request returns a Telegram error that the command
  reports back instead of sending.

Because the command makes the bot post a checklist on behalf of a business
account, it is guarded like the other admin commands:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- the global rate-limit middleware still applies.

### Edit a checklist

The restricted `/editchecklist` command calls Telegram Bot API
`editMessageChecklist` (introduced in Bot API 10.0). Because the pinned
`aiogram==3.3.0` has no typed wrapper for this method, the command uses an
**isolated raw Bot API helper** (`bot/services/edit_message_checklist.py`) that
POSTs over `httpx` and JSON-serializes the replacement `InputChecklist`.

`editMessageChecklist` edits a checklist **on behalf of a connected business
account** and returns the edited `Message`. Telegram requires
`business_connection_id`, `chat_id`, `message_id` and `checklist`; optional
inline `reply_markup` is supported by the helper for service-level callers.

Usage: `/editchecklist <business_connection_id> <chat_id> <message_id> <title> | <task> [| <task> ...]`

- `chat_id` and `message_id` identify the existing checklist message to edit;
- provide between 1 and 30 replacement tasks; the handler assigns sequential
  task ids starting at 1;
- the title is limited to 255 characters and each task to 100 characters;
- malformed input is rejected before Telegram is contacted;
- title and task text are not written to structured logs; logs include target
  ids, task count and Telegram error shape.

The command is restricted to `TELEGRAM_ADMIN_CHAT_IDS` with no fallback to
`TELEGRAM_ALLOWED_CHAT_IDS`, does not call `free-claude-code`, and uses the
global command rate limit. Rollback is another `/editchecklist` call with the
previous checklist content, or manual editing from the connected business
account in Telegram.

### Post a business story

The restricted `/poststory` command calls Telegram Bot API `postStory`
(introduced in Bot API 10.0). Because the pinned `aiogram==3.3.0` predates this
method and ships no typed wrapper, the command goes through an **isolated raw
Bot API helper** (`bot/services/post_story.py`) that POSTs the request over
`httpx`. This is a dedicated admin publishing flow for stories and is not mixed
with Claude chat replies.

`postStory` posts on behalf of a managed business account, so the bot must have
the `can_manage_stories` business bot right for the supplied live
`business_connection_id`. The command currently exposes the safest minimal
content path: a photo story from a Telegram `photo_file_id`.

Usage: `/poststory <business_connection_id> <active_period> <photo_file_id> [caption]`

- `active_period` must be one of `21600`, `43200`, `86400` or `172800` seconds;
- the optional caption is limited to 2048 characters after Telegram entity
  parsing;
- the story content is sent as `{"type": "photo", "photo": "<photo_file_id>"}`;
- operator-provided caption text is kept out of structured logs; logs include
  only business connection id, active period, option flags and returned story id;
- a missing or expired `business_connection_id`, missing `can_manage_stories`
  right, invalid media or rate limit response is reported back to the operator.

Rollback is operational: delete or archive the posted story from the managed
business account in Telegram. The separate Bot API `deleteStory` method is
tracked independently and is not invoked by `/poststory`.

### Repost a business story

The restricted `/repoststory` command calls Telegram Bot API `repostStory`
(introduced in Bot API 10.0). Because the pinned `aiogram==3.3.0` predates this
method and ships no typed wrapper, the command goes through an **isolated raw
Bot API helper** (`bot/services/repost_story.py`) that POSTs the request over
`httpx`. This is a dedicated admin publishing flow for stories and is not mixed
with Claude chat replies.

`repostStory` reposts a story from another business account managed by the same
bot. The bot must have the `can_manage_stories` business bot right for both
business accounts, and the source story must have been posted or reposted by
the bot.

Usage: `/repoststory <business_connection_id> <from_chat_id> <from_story_id> <active_period>`

- `business_connection_id` identifies the destination business account;
- `from_chat_id` identifies the source business account chat that posted the
  story;
- `from_story_id` identifies the source story;
- `active_period` must be one of `21600`, `43200`, `86400` or `172800` seconds;
- operator-provided identifiers are logged, but no returned owner metadata is
  written to structured logs;
- a missing or expired `business_connection_id`, missing `can_manage_stories`
  right, inaccessible source story or rate limit response is reported back to
  the operator.

Rollback is operational: delete or archive the reposted story from the managed
business account in Telegram. The separate Bot API `deleteStory` method is
tracked independently and is not invoked by `/repoststory`.

### Edit a business story

The restricted `/editstory` command calls Telegram Bot API `editStory`
(introduced in Bot API 10.0). Because the pinned `aiogram==3.3.0` predates this
method and ships no typed wrapper, the command goes through an **isolated raw
Bot API helper** (`bot/services/edit_story.py`) that POSTs the request over
`httpx`. This is a dedicated admin publishing flow for stories and is not mixed
with Claude chat replies.

`editStory` edits a story that was previously posted by the bot on behalf of a
managed business account. The bot must have the `can_manage_stories` business
bot right for the supplied live `business_connection_id`. The command exposes a
minimal photo replacement path from a Telegram `photo_file_id`.

Usage: `/editstory <business_connection_id> <story_id> <photo_file_id> [caption]`

- `story_id` must identify an existing story posted by this bot for that
  business connection;
- the optional caption is limited to 2048 characters after Telegram entity
  parsing;
- the replacement story content is sent as
  `{"type": "photo", "photo": "<photo_file_id>"}`;
- operator-provided caption text is kept out of structured logs; logs include
  only business connection id, source story id and returned story id;
- a missing or expired `business_connection_id`, missing `can_manage_stories`
  right, inaccessible story, invalid media or rate limit response is reported
  back to the operator.

Rollback is operational: run `/editstory` again with the previous media and
caption if they are still available, or edit/archive the story from the managed
business account in Telegram.

### Get a business connection

The restricted `/businessconnection` command calls Telegram Bot API
`getBusinessConnection` to fetch a `BusinessConnection` object for a live
`business_connection_id`. Because the pinned `aiogram==3.3.0` does not expose a
typed wrapper for this Bot API 10.0 method, the command uses an isolated raw Bot
API helper (`bot/services/get_business_connection.py`) over `httpx`.

Usage: `/businessconnection <business_connection_id>`

The command reports the connection id, owner, user chat id, creation date,
`can_reply`, and enabled state. It does not manage tokens and does not call
`free-claude-code`; it is intended as a narrow admin diagnostic surface before
operators use business-account flows such as `/checklist`.

Because the response exposes business owner and lifecycle metadata, it is
guarded like the sensitive business commands:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- only structural state is logged; owner names and returned object contents are
  not written to structured logs;
- Telegram errors, such as an expired or unknown `business_connection_id`, are
  reported back without retrying or changing connection state.

### Get business account Star balance

The restricted `/businessstarbalance` command calls Telegram Bot API
`getBusinessAccountStarBalance` to fetch a `StarAmount` object for a live
`business_connection_id`. Because the pinned `aiogram==3.3.0` does not expose a
typed wrapper for this Bot API 10.0 method, the command uses an isolated raw Bot
API helper (`bot/services/get_business_account_star_balance.py`) over `httpx`.

Usage: `/businessstarbalance <business_connection_id>`

- `business_connection_id` must come from a live business connection update or
  another trusted operator source;
- Telegram requires the current `can_view_gifts_and_stars` business right and
  enforces connection ownership, expired connection and permission errors;
- the command is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and
  does **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`;
- structured logs contain the connection id and response shape, but not the
  returned Stars amount.

The command does not call `free-claude-code` and is read-only. Transfers from
the business account balance require a separate explicit flow.

### Get business account gifts

The restricted `/businessgifts` command calls Telegram Bot API
`getBusinessAccountGifts` to fetch an `OwnedGifts` page for a live
`business_connection_id`. Because the pinned `aiogram==3.3.0` does not expose a
typed wrapper for this Bot API 10.0 method, the command uses an isolated raw Bot
API helper (`bot/services/get_business_account_gifts.py`) over `httpx`.

Usage: `/businessgifts <business_connection_id> [exclude_unsaved=true|false] [exclude_saved=true|false] [exclude_unlimited=true|false] [exclude_limited=true|false] [exclude_unique=true|false] [sort_by_price=true|false] [offset=<offset>] [limit=1..100]`

- `business_connection_id` must come from a live business connection update or
  another trusted operator source;
- boolean filters are optional and are sent only when set to `true`;
- `offset` is Telegram's pagination cursor from a previous response, and
  `limit` must be from 1 to 100;
- Telegram enforces connection ownership, expired connection handling and the
  current business right to view gifts and Stars; those errors are reported
  back without retry;
- the command is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and
  does **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`;
- structured logs contain the connection id, item count, next-offset presence
  and error shape, but not full gift payloads.

The command does not call `free-claude-code` and is read-only. Rollback is
operational: stop using the command, remove the admin chat from
`TELEGRAM_ADMIN_CHAT_IDS`, or adjust the bot's business rights in Telegram.
Integration testing is opt-in because it needs a real bot token and live
business connection id.

### Get chat gifts

The restricted `/chatgifts` command calls Telegram Bot API `getChatGifts` to
fetch an `OwnedGifts` page for a channel chat. Because the pinned
`aiogram==3.3.0` does not expose a typed wrapper for this Bot API method, the
command uses an isolated raw Bot API helper (`bot/services/get_chat_gifts.py`)
over `httpx`.

Usage: `/chatgifts <chat_id|@channelusername> [exclude_unsaved=true|false] [exclude_saved=true|false] [exclude_unlimited=true|false] [exclude_limited_upgradable=true|false] [exclude_limited_non_upgradable=true|false] [exclude_from_blockchain=true|false] [exclude_unique=true|false] [sort_by_price=true|false] [offset=<offset>] [limit=1..100]`

- `chat_id` can be a numeric Telegram channel id or `@channelusername`;
- boolean filters are optional and are sent only when set to `true`;
- `offset` is Telegram's pagination cursor from a previous response, and
  `limit` must be from 1 to 100;
- Telegram supports this method for channel chats and can require the bot's
  `can_post_messages` administrator right for full visibility;
- the command is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and
  does **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`;
- structured logs contain the chat id, item count, next-offset presence and
  error shape, but not full gift payloads.

The command does not call `free-claude-code` and is read-only. Conversion,
upgrade or transfer operations require separate explicit commands.

### Transfer business account Stars

The restricted `/transferbusinessstars` command calls Telegram Bot API
`transferBusinessAccountStars` to move Telegram Stars from a connected business
account balance to this bot's balance for withdrawal. Because the pinned
`aiogram==3.3.0` does not expose a typed wrapper for this Bot API 10.0 method,
the command uses an isolated raw Bot API helper
(`bot/services/transfer_business_account_stars.py`) over `httpx`.

Usage: `/transferbusinessstars <business_connection_id> <star_count> confirm`

- `business_connection_id` must come from a live business connection update or
  another trusted operator source;
- `star_count` must be a positive integer amount of whole Telegram Stars;
- Telegram requires the current `can_transfer_stars` business right and
  enforces connection ownership, expired connection and available-balance
  checks;
- the command is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and
  does **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`;
- `confirm` is required because the operation moves value out of the business
  account and cannot be reversed by this bot;
- structured logs contain the connection id, requested Star count and error
  shape, but no owner profile data or business connection object.

The command does not call `free-claude-code`. Rollback is operational only:
stop using the command, remove the admin chat from `TELEGRAM_ADMIN_CHAT_IDS`,
or adjust the bot's business rights in Telegram.

### Convert gift to Stars

The restricted `/convertgiftstars` command calls Telegram Bot API
`convertGiftToStars` to convert one regular owned gift of a connected business
account into Telegram Stars on that business account balance. Because the pinned
`aiogram==3.3.0` does not expose a typed wrapper for this Bot API 10.0 method,
the command uses an isolated raw Bot API helper
(`bot/services/convert_gift_to_stars.py`) over `httpx`.

Usage: `/convertgiftstars <business_connection_id> <owned_gift_id> confirm`

- `business_connection_id` and `owned_gift_id` must come from
  `/businessgifts` or another trusted operator source;
- Telegram requires the current business right to convert gifts to Stars and
  enforces connection ownership, expired connection and gift eligibility checks;
- the command is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and
  does **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`;
- `confirm` is required because the operation consumes the original gift and
  cannot be reversed by this bot;
- structured logs contain the connection id, owned gift id and error shape, but
  no owner profile data or full gift payload.

The command does not call `free-claude-code`. Rollback is operational only:
stop using the command, remove the admin chat from `TELEGRAM_ADMIN_CHAT_IDS`,
or adjust the bot's business rights in Telegram. Operators can verify the new
business Stars balance with `/businessstarbalance`.

### Upgrade gift

The restricted `/upgradegift` command calls Telegram Bot API `upgradeGift` to
upgrade one owned gift of a connected business account. Because the pinned
`aiogram==3.3.0` does not expose a typed wrapper for this Bot API 10.0 method,
the command uses an isolated raw Bot API helper
(`bot/services/upgrade_gift.py`) over `httpx`.

Usage: `/upgradegift <business_connection_id> <owned_gift_id> [keep_original_details=true|false] confirm`

- `business_connection_id` and `owned_gift_id` must come from
  `/businessgifts` or another trusted operator source;
- `keep_original_details` is optional and is sent to Telegram only when the
  operator provides it explicitly;
- Telegram requires connection ownership, an upgradable gift, enough Stars on
  the business account balance and the current business right to transfer and
  upgrade gifts;
- the command is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and
  does **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`;
- `confirm` is required because the operation spends Stars and cannot be
  reversed by this bot;
- structured logs contain the connection id, owned gift id, optional detail
  flag and error shape, but no owner profile data or full gift payload.

The command does not call `free-claude-code`. Rollback is operational only:
stop using the command, remove the admin chat from `TELEGRAM_ADMIN_CHAT_IDS`,
or adjust the bot's business rights in Telegram.

### Read a business message

The restricted `/readbusinessmessage` command calls Telegram Bot API
`readBusinessMessage` to mark one message from a connected business account as
read. Because the pinned `aiogram==3.3.0` does not expose a typed wrapper for
this Bot API 10.0 method, the command uses an isolated raw Bot API helper
(`bot/services/read_business_message.py`) over `httpx`.

Usage: `/readbusinessmessage <business_connection_id> <message_id>`

- `business_connection_id` must come from a live business connection update or
  another trusted operator source;
- `message_id` must be a positive integer for a message that belongs to that
  business connection;
- Telegram enforces connection ownership, current business rights and expired or
  unknown connection handling; the command reports those Telegram errors without
  retrying or changing connection state;
- the command is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and
  does **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`;
- structured logs contain only the connection id, message id and error shape.

The command does not call `free-claude-code`. Rollback is operational: remove
the admin chat from `TELEGRAM_ADMIN_CHAT_IDS` or remove the command handler.

### Set business account name

The restricted `/setbusinessaccountname` command calls Telegram Bot API
`setBusinessAccountName` to update the first and optional last name of a
connected business account. Because the pinned `aiogram==3.3.0` does not expose
a typed wrapper for this Bot API 10.0 method, the command uses an isolated raw
Bot API helper (`bot/services/set_business_account_name.py`) over `httpx`.

Usage: `/setbusinessaccountname <business_connection_id> <first_name> [last_name]`

- `business_connection_id` must come from a live business connection update or
  another trusted operator source;
- `first_name` is required and `last_name` is optional; both are parsed as
  single tokens and limited to 64 characters each;
- Telegram enforces connection ownership, current business rights and expired or
  unknown connection handling; those errors are reported back without retry;
- the command is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and
  does **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`;
- structured logs contain only the connection id, whether a last name was
  supplied and the error shape; name values are kept out of structured logs.

The command does not call `free-claude-code`. Rollback is operational: set the
previous name through Telegram or remove the admin chat from
`TELEGRAM_ADMIN_CHAT_IDS` before further changes.

### Set business account username

The restricted `/setbusinessaccountusername` command calls Telegram Bot API
`setBusinessAccountUsername` to update the public username of a connected
business account. Because the pinned `aiogram==3.3.0` does not expose a typed
wrapper for this Bot API 10.0 method, the command uses an isolated raw Bot API
helper (`bot/services/set_business_account_username.py`) over `httpx`.

Usage: `/setbusinessaccountusername <business_connection_id> <username>`

- `business_connection_id` must come from a live business connection update or
  another trusted operator source;
- `username` may be passed with or without `@`, is parsed as a single token and
  must be 5-32 characters long;
- Telegram enforces connection ownership, current business rights, username
  availability and expired or unknown connection handling; those errors are
  reported back without retry;
- the command is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and
  does **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`;
- structured logs contain only the connection id and the error shape; username
  values are kept out of structured logs.

The command does not call `free-claude-code`. Rollback is operational: set the
previous username through Telegram or remove the admin chat from
`TELEGRAM_ADMIN_CHAT_IDS` before further changes.

### Set business account bio

The restricted `/setbusinessaccountbio` command calls Telegram Bot API
`setBusinessAccountBio` to update or clear the public bio of a connected
business account. Because the pinned `aiogram==3.3.0` does not expose a typed
wrapper for this Bot API 10.0 method, the command uses an isolated raw Bot API
helper (`bot/services/set_business_account_bio.py`) over `httpx`.

Usage: `/setbusinessaccountbio <business_connection_id> <bio|clear>`

- `business_connection_id` must come from a live business connection update or
  another trusted operator source;
- `bio` may contain spaces and must be at most 140 characters; pass `clear` to
  send an empty bio value and clear the current bio;
- Telegram enforces connection ownership, current `can_change_bio` business
  right and expired or unknown connection handling; those errors are reported
  back without retry;
- the command is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and
  does **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`;
- structured logs contain only the connection id, whether a bio value was
  supplied and the error shape; bio text is kept out of structured logs.

The command does not call `free-claude-code`. Rollback is operational: set the
previous bio through Telegram, use `clear`, or remove the admin chat from
`TELEGRAM_ADMIN_CHAT_IDS` before further changes.

### Set business account profile photo

The restricted `/setbusinessaccountprofilephoto` command calls Telegram Bot API
`setBusinessAccountProfilePhoto` to update the profile photo of a connected
business account. Because the pinned `aiogram==3.3.0` does not expose a typed
wrapper for this Bot API 10.0 method, the command uses an isolated raw
multipart Bot API helper (`bot/services/set_business_account_profile_photo.py`)
over `httpx`.

Usage: `/setbusinessaccountprofilephoto <business_connection_id> <photo_path> [public=true|false]`

- `business_connection_id` must come from a live business connection update or
  another trusted operator source;
- `photo_path` must point to a local JPG file available to the running bot
  process; Telegram requires a fresh upload for profile photos;
- pass `public=true` to set the public fallback photo visible when the main
  photo is hidden by the business account's privacy settings;
- Telegram enforces connection ownership, current `can_edit_profile_photo`
  business right and expired or unknown connection handling; those errors are
  reported back without retry;
- the command is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and
  does **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`;
- structured logs contain the connection id, local path, visibility flag and
  error shape; file contents are never logged.

The command does not call `free-claude-code`. Rollback is operational: run the
command again with the previous photo, use Telegram's business account profile
controls, or remove the admin chat from `TELEGRAM_ADMIN_CHAT_IDS` before further
changes.

### Remove business account profile photo

The restricted `/removebusinessaccountprofilephoto` command calls Telegram Bot
API `removeBusinessAccountProfilePhoto` to remove the main or public fallback
profile photo of a connected business account. Because the pinned
`aiogram==3.3.0` does not expose a typed wrapper for this Bot API 10.0 method,
the command uses an isolated raw Bot API helper
(`bot/services/remove_business_account_profile_photo.py`) over `httpx`.

Usage: `/removebusinessaccountprofilephoto <business_connection_id> [public=true|false] confirm`

- `business_connection_id` must come from a live business connection update or
  another trusted operator source;
- pass `public=true` to remove the public fallback photo instead of the main
  profile photo;
- `confirm` is required because the command changes public business account
  metadata;
- Telegram enforces connection ownership, current `can_edit_profile_photo`
  business right and expired or unknown connection handling; those errors are
  reported back without retry;
- the command is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and
  does **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`;
- structured logs contain the connection id, visibility flag and error shape.

The command does not call `free-claude-code`. Rollback is operational: run
`/setbusinessaccountprofilephoto` with the previous image, use Telegram's
business account profile controls, or remove the admin chat from
`TELEGRAM_ADMIN_CHAT_IDS` before further changes.

### Set business account gift settings

The restricted `/setbusinessaccountgiftsettings` command calls Telegram Bot API
`setBusinessAccountGiftSettings` to change incoming gift privacy settings of a
connected business account. Because the pinned `aiogram==3.3.0` does not expose
a typed wrapper for this Bot API 10.0 method, the command uses an isolated raw
Bot API helper (`bot/services/set_business_account_gift_settings.py`) over
`httpx`.

Usage: `/setbusinessaccountgiftsettings <business_connection_id> show_gift_button=true|false unlimited_gifts=true|false limited_gifts=true|false unique_gifts=true|false premium_subscription=true|false gifts_from_channels=true|false`

- `business_connection_id` must come from a live business connection update or
  another trusted operator source;
- `show_gift_button` controls whether the gift button should always be shown in
  the input field;
- every `AcceptedGiftTypes` flag must be supplied explicitly so reviews can see
  exactly which incoming gift categories are accepted;
- Telegram enforces connection ownership, current `can_change_gift_settings`
  business right and expired or unknown connection handling; those errors are
  reported back without retry;
- the command is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and
  does **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`;
- structured logs contain the connection id, gift button flag, count of enabled
  gift types and error shape.

The command does not call `free-claude-code`. Rollback is operational: run the
command again with the previous values, use Telegram's business account gift
privacy controls, or remove the admin chat from `TELEGRAM_ADMIN_CHAT_IDS`
before further changes.

### Delete business messages

The restricted `/deletebusinessmessages` command calls Telegram Bot API
`deleteBusinessMessages` to delete 1-100 messages from a connected business
account. Because the pinned `aiogram==3.3.0` does not expose a typed wrapper for
this Bot API 10.0 method, the command uses an isolated raw Bot API helper
(`bot/services/delete_business_messages.py`) over `httpx`.

Usage: `/deletebusinessmessages <business_connection_id> <message_id> [message_id ...] confirm`

- `business_connection_id` must come from a live business connection update or
  another trusted operator source;
- message ids may be separated by spaces or commas, must be positive integers,
  and the command accepts at most 100 ids per call;
- the command requires the explicit `confirm` keyword because Telegram deletes
  the messages and this bot cannot restore them;
- Telegram enforces connection ownership, current business rights and expired or
  unknown connection handling; those errors are reported back without retry;
- the command is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and
  does **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`;
- structured logs contain only the connection id, message count and error shape.

The command does not call `free-claude-code`. Rollback is operational only:
remove the admin chat from `TELEGRAM_ADMIN_CHAT_IDS` or remove the command
handler before further deletes.

### Delete a message

The restricted `/deletemessage` command calls Telegram Bot API `deleteMessage`
through aiogram's typed API. It is intended for controlled cleanup of bot
messages and trusted admin moderation actions.

Usage: `/deletemessage <chat_id> <message_id> confirm`

- `chat_id` and `message_id` identify the target message; `message_id` must be
  positive;
- the command requires the explicit `confirm` keyword because Telegram deletes
  the message and this bot cannot restore it;
- Telegram only allows deletion of messages that fit Bot API constraints:
  usually messages younger than 48 hours, dice messages in private chats only
  after 24 hours, and messages covered by the bot's own-message or admin
  deletion rights;
- the bot must have `can_delete_messages` to delete other users' messages in
  groups, supergroups or channels; own messages may be deletable without that
  moderation right where Telegram permits it;
- the command is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and
  does **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`;
- structured logs contain only the target chat id, message id and error shape.

No special update subscription is required because the scenario is initiated by
a normal command message from an admin chat. The command does not call
`free-claude-code`. Rollback is manual only: repost or restore the content
outside the Bot API.

### Delete messages in bulk

The restricted `/deletemessages` command calls Telegram Bot API
`deleteMessages` through aiogram's typed API. It is intended for controlled
bulk cleanup of bot messages and trusted admin moderation actions.

Usage: `/deletemessages <chat_id> <message_id> [message_id ...] confirm`

- `chat_id` and `message_id` values identify the target messages; message ids
  may be separated by spaces or commas and must be positive integers;
- Telegram accepts 1-100 message ids per `deleteMessages` request, so the helper
  chunks larger operator cleanup requests into 100-id Bot API calls;
- the command requires the explicit `confirm` keyword because Telegram deletes
  messages and this bot cannot restore them;
- Telegram skips messages that are not found and rejects chunks that violate Bot
  API constraints: usually messages older than 48 hours, dice messages in
  private chats newer than 24 hours, or messages outside the bot's own-message
  or admin deletion rights;
- the bot must have `can_delete_messages` to delete other users' messages in
  groups, supergroups or channels; own messages may be deletable without that
  moderation right where Telegram permits it;
- the command is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and
  does **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`;
- structured logs contain only the target chat id, per-chunk message counts and
  error shape, not message text.

No special update subscription is required because the scenario is initiated by
a normal command message from an admin chat. The command does not call
`free-claude-code`. Rollback is manual only: repost or restore the content
outside the Bot API. Partial Telegram failures are reported back to the
operator with the affected chunk ids while successful chunks remain deleted.

### Get a managed bot token

The restricted `/managedbottoken` command calls Telegram Bot API
`getManagedBotToken` to fetch the live token of a managed bot by its Telegram
`user_id`. Because the pinned `aiogram==3.3.0` does not expose a typed wrapper
for this Bot API 9.6 method, the command uses an isolated raw Bot API helper
(`bot/services/get_managed_bot_token.py`) over `httpx`.

Usage: `/managedbottoken <managed_bot_user_id>`

The `user_id` must be a positive integer from a trusted `managed_bot` update,
`managed_bot_created` message, or another operator-controlled source. Telegram
only returns a token when the calling bot is allowed to manage that bot. The
method does not require `free-claude-code` and does not change token lifecycle
state; rollback for an exposed token is to revoke/replace it through Telegram's
`replaceManagedBotToken` flow or BotFather.

Because the response is a credential, it is guarded like the most sensitive
admin commands:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- structured logs include only `user_id` and token length, never the token;
- Telegram permission, unknown managed-bot, token lifecycle, transport and
  rate-limit errors are reported back to the admin chat.

### Get managed bot access settings

The restricted `/managedbotaccess` command calls Telegram Bot API
`getManagedBotAccessSettings` to fetch the `BotAccessSettings` object of a
managed bot by its Telegram `user_id`. Because the pinned `aiogram==3.3.0` does
not expose a typed wrapper for this Bot API 10.0 method, the command uses an
isolated raw Bot API helper
(`bot/services/get_managed_bot_access_settings.py`) over `httpx`.

Usage: `/managedbotaccess <managed_bot_user_id>`

The `user_id` must be a positive integer from a trusted `managed_bot` update,
`managed_bot_created` message, or another operator-controlled source. Telegram
only returns the access settings when the calling bot is allowed to manage that
bot. The method does not require `free-claude-code` and does not change token
lifecycle state; rollback is simply to remove this admin command or change the
settings later through Telegram's `setManagedBotAccessSettings` flow.

The command reports whether access is restricted and how many additional users
are allowed. When Telegram includes the optional `added_users` list, the admin
response shows user ids and display names, while structured logs keep only
`user_id`, the restricted flag and user count.

Because the response exposes the managed bot allowlist, it is guarded like the
other sensitive managed-bot commands:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- no special update subscription is required for the command itself because it
  starts from a normal admin message; include `managed_bot` in allowed updates
  only when the operator needs to collect managed-bot lifecycle ids;
- Telegram permission, unknown managed-bot, transport and rate-limit errors are
  reported back to the admin chat.

### Set managed bot access settings

The restricted `/setmanagedbotaccess` command calls Telegram Bot API
`setManagedBotAccessSettings` to update the `BotAccessSettings` object of a
managed bot by its Telegram `user_id`. Because the pinned `aiogram==3.3.0` does
not expose a typed wrapper for this Bot API 10.0 method, the command uses an
isolated raw Bot API helper
(`bot/services/set_managed_bot_access_settings.py`) over `httpx`.

Usage:
`/setmanagedbotaccess <managed_bot_user_id> <restricted|open> [added_user_id ...] confirm`

The `user_id` and optional `added_user_id` values must be positive integers
from trusted operator-controlled sources. `restricted` sets
`is_access_restricted=true` and sends the listed user ids as `added_users`;
`open` sets `is_access_restricted=false` and omits the allowlist. Telegram only
updates access settings when the calling bot is allowed to manage that bot.

Because this command changes who can access a managed bot, it requires the
literal `confirm` argument. Rollback is to run `/managedbotaccess` before the
change, preserve the previous state, then run `/setmanagedbotaccess` again with
the previous restricted flag and user ids if the update must be reverted.

The command is guarded like the other sensitive managed-bot commands:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- structured logs include only `user_id`, the restricted flag and allowlist
  count, not the full allowlist values;
- Telegram permission, unknown managed-bot, transport and rate-limit errors are
  reported back to the admin chat.

### Replace a managed bot token

The restricted `/replacemanagedbottoken` command calls Telegram Bot API
`replaceManagedBotToken` to rotate the live token of a managed bot by its
Telegram `user_id`. Because the pinned `aiogram==3.3.0` does not expose a typed
wrapper for this Bot API 9.6 method, the command uses an isolated raw Bot API
helper (`bot/services/replace_managed_bot_token.py`) over `httpx`.

Usage: `/replacemanagedbottoken <managed_bot_user_id> confirm`

The `user_id` must be a positive integer from a trusted `managed_bot` update,
`managed_bot_created` message, or another operator-controlled source. Telegram
only replaces a token when the calling bot is allowed to manage that bot. The
method does not require `free-claude-code`, but it changes token lifecycle
state: the returned token must be moved into the relevant secret store and
deployments immediately, and rollback requires another rotation or a separately
preserved previous credential if Telegram still accepts it.

Because the command rotates a credential, it is guarded like a destructive
admin command:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- it requires explicit text confirmation with the `confirm` keyword;
- structured logs include only `user_id` and token length, never the token;
- Telegram permission, unknown managed-bot, token lifecycle, transport and
  rate-limit errors are reported back to the admin chat.

### Get available gifts

The restricted `/availablegifts` command calls Telegram Bot API
`getAvailableGifts` to fetch the current regular gift catalog. The method takes
no Bot API parameters and returns a `Gifts` object with a `gifts` list. Because
the pinned `aiogram==3.3.0` does not expose a typed wrapper for this Bot API
10.0 method, the command uses an isolated raw Bot API helper
(`bot/services/get_available_gifts.py`) over `httpx`.

Usage: `/availablegifts confirm`

This is a read-only admin billing/rewards diagnostic. It does not spend
Telegram Stars, send gifts, verify users, or call `free-claude-code`. The
command still requires the literal `confirm` argument because the returned
catalog is intended to precede separate spending or verification actions, which
must remain in their own confirmed commands with their own audit logs. Rollback
is to ignore the fetched catalog or remove the command; no Telegram state is
changed.

The command is guarded like the other sensitive billing/admin surfaces:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- structured logs include only gift count and gift ids, not unrelated chat or
  user data;
- no special update subscription or chat administrator rights are required
  because the command starts from a normal admin message;
- Telegram transport, permission and rate-limit errors are reported back to the
  admin chat.

### Send gift

The restricted `/sendgift` command calls Telegram Bot API `sendGift` to send a
regular gift to exactly one receiver: a `user_id` or a channel `chat_id`. The
method requires a `gift_id` from the current catalog and returns `True` on
success. Because gift delivery spends Telegram Stars from the bot balance and
the pinned `aiogram==3.3.0` does not expose this Bot API 10.0 method, the
implementation uses an isolated raw Bot API helper
(`bot/services/send_gift.py`) over `httpx`.

Usage: `/sendgift <user|chat> <receiver_id> <gift_id> confirm [text]`

Operators should fetch `/availablegifts confirm` first, choose the `gift_id`
from that trusted catalog, then run `/sendgift` only after reviewing product
rules, receiver identity and available Stars balance. Optional `text` is capped
at 128 characters before sending. Gift delivery cannot be rolled back by this
bot; rollback is operational only: stop using the command, replenish/reconcile
Stars out of band, and review the structured audit event.

The command is guarded like the other spending/admin surfaces:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- it requires the literal `confirm` keyword in the same command that sends the
  gift;
- Telegram requires exactly one receiver (`user_id` or `chat_id`); channel
  gifts depend on Telegram-side bot permissions and Stars balance;
- structured logs include the gift id, receiver type, upgrade flag and text
  presence, not the message text or unrelated user data;
- Telegram transport, permission, balance and rate-limit errors are reported
  back to the admin chat.

### Gift Premium subscription

The restricted `/giftpremium` command calls Telegram Bot API
`giftPremiumSubscription` to gift Telegram Premium to a user. The method
requires `user_id`, `month_count` and the exact `star_count` price to withdraw
from the bot's Stars balance, accepts optional gift text, and returns `True` on
success. Because the pinned `aiogram==3.3.0` does not expose this Bot API 10.0
method, the implementation uses an isolated raw Bot API helper
(`bot/services/gift_premium_subscription.py`) over `httpx`.

Usage: `/giftpremium <user_id> <month_count> <star_count> confirm [text]`

Operators must review Telegram's current Premium gift price and available Stars
balance before running the command. `month_count` is locally limited to
Telegram's documented `3..12` month range, `star_count` must be positive, and
optional `text` is capped at 128 characters before sending. The command is not
connected to `free-claude-code`; it is a separate admin billing/rewards action.
Premium gifting cannot be rolled back by this bot, so rollback is operational:
stop using the command, reconcile Stars out of band, and review the structured
audit event.

The command is guarded like the other spending/admin surfaces:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- it requires the literal `confirm` keyword in the same command that spends
  Stars;
- no special update subscription is required because the scenario starts from a
  normal admin message; Telegram validates the target user and Stars balance;
- structured logs include `user_id`, `month_count`, `star_count` and text
  presence, not the gift text or unrelated chat data;
- Telegram transport, permission, balance and rate-limit errors are reported
  back to the admin chat.

### Verify user

The restricted `/verifyuser` command calls Telegram Bot API `verifyUser` to
verify a user with the bot's verification authority. The method requires
`user_id`, accepts an optional `custom_description`, and returns `True` on
success. Because the pinned `aiogram==3.3.0` does not expose this Bot API 10.0
method, the implementation uses an isolated raw Bot API helper
(`bot/services/verify_user.py`) over `httpx`.

Usage: `/verifyuser <user_id> confirm [custom_description]`

Operators must review the user identity, product rules, verification authority
and rollback plan before running the command. `user_id` must be positive and
optional `custom_description` is capped at 70 characters before sending.
Verification is not connected to `free-claude-code`, gifts or Premium gifting;
it is a separate admin verification action. Rollback requires a separate
remove-verification action when available.

The command is guarded like the other verification/admin surfaces:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- it requires the literal `confirm` keyword in the same command that verifies
  the user;
- no special update subscription is required because the scenario starts from a
  normal admin message; Telegram validates the target user and bot authority;
- structured logs include `user_id` and description presence, not the
  description text or unrelated chat data;
- Telegram permission, transport and rate-limit errors are reported back to the
  admin chat.

### Remove user verification

The restricted `/removeuserverification` command calls Telegram Bot API
`removeUserVerification` to remove verification from a user with the bot's
verification authority. The method requires `user_id` and returns `True` on
success. No special update subscription is required because the scenario starts
from a normal admin message; Telegram validates the target user and the bot's
verification authority.

Because the pinned `aiogram==3.3.0` does not expose this Bot API 10.0 method,
the implementation uses an isolated raw Bot API helper
(`bot/services/remove_user_verification.py`) over `httpx`.

Usage: `/removeuserverification <user_id> confirm`

Operators must review the user identity, product rules, verification authority,
audit trail and rollback plan before running the command. `user_id` must be
positive. The command is not connected to `free-claude-code`, gifts or Premium
gifting; it is a separate admin verification action. Rollback is a separate
confirmed `/verifyuser <user_id> confirm [custom_description]` action.

The command is guarded like the other verification/admin surfaces:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- it requires the literal `confirm` keyword in the same command that removes
  the verification;
- structured logs include `user_id`, not unrelated chat data;
- Telegram permission, transport and rate-limit errors are reported back to the
  admin chat.

### Verify chat

The restricted `/verifychat` command calls Telegram Bot API `verifyChat` to
verify a chat with the bot's verification authority. The method requires
`chat_id`, accepts an optional `custom_description`, and returns `True` on
success. Because the pinned `aiogram==3.3.0` does not expose this Bot API 10.0
method, the implementation uses an isolated raw Bot API helper
(`bot/services/verify_chat.py`) over `httpx`.

Usage: `/verifychat <chat_id|@username> confirm [custom_description]`

Operators must review the chat identity, product rules, verification authority
and rollback plan before running the command. Numeric `chat_id` must not be
`0`, `@username` targets are passed through to Telegram, and optional
`custom_description` is capped at 70 characters before sending. Verification is
not connected to `free-claude-code`, gifts or Premium gifting; it is a separate
admin verification action. Rollback requires a separate remove-verification
action when available.

The command is guarded like the other verification/admin surfaces:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- it requires the literal `confirm` keyword in the same command that verifies
  the chat;
- no special update subscription is required because the scenario starts from a
  normal admin message; Telegram validates the target chat and bot authority;
- structured logs include `chat_id` and description presence, not the
  description text or unrelated chat data;
- Telegram permission, privacy, validation, transport and rate-limit errors are
  reported back to the admin chat.

### Remove chat verification

The restricted `/removechatverification` command calls Telegram Bot API
`removeChatVerification` to remove verification from a chat with the bot's
verification authority. The method requires `chat_id` and returns `True` on
success. Because the pinned `aiogram==3.3.0` does not expose this Bot API 10.0
method, the implementation uses an isolated raw Bot API helper
(`bot/services/remove_chat_verification.py`) over `httpx`.

Usage: `/removechatverification <chat_id|@username> confirm`

Operators must review the chat identity, product rules, verification authority
and rollback plan before running the command. Numeric `chat_id` must not be
`0`, and `@username` targets are passed through to Telegram. Removal is not
connected to `free-claude-code`, gifts or Premium gifting; it is a separate
admin verification action. Rollback requires a separate confirmed
`/verifychat <chat_id|@username> confirm [custom_description]` action.

The command is guarded like the other verification/admin surfaces:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- it requires the literal `confirm` keyword in the same command that removes
  the chat verification;
- no special update subscription is required because the scenario starts from a
  normal admin message; Telegram validates the target chat and bot authority;
- structured logs include `chat_id`, not unrelated chat data;
- Telegram permission, privacy, validation, transport and rate-limit errors are
  reported back to the admin chat.

### Send a media group

The restricted `/mediagroup` command calls Telegram Bot API `sendMediaGroup`
through aiogram's typed `Bot.send_media_group()` wrapper. It lets an operator
post several media items into the chat as a single **album** instead of separate
messages or only a textual interpretation.

Usage: `/mediagroup <type> <url_or_file_id> <url_or_file_id> [<url_or_file_id> ...] [caption <text>]`

- the album is always sent into the chat where the command was issued;
- `type` is one of `photo`, `video`, `document` or `audio`; all items in one
  album share the same type. Telegram only allows photos and videos to be mixed,
  while documents and audio must each be grouped on their own, so using a single
  type always produces a valid combination;
- provide between 2 and 10 media references (the command validates this bound
  before calling Telegram), each an HTTP(S) URL Telegram can fetch or a file_id
  of media already on Telegram servers;
- the optional album caption follows the literal word `caption`; the rest of the
  message becomes the caption and is applied to the album (its first item),
  limited to 1024 characters (validated before calling Telegram);
- an invalid request (for example a chat the bot cannot post to or a bad
  file_id) returns a Telegram error that the command reports back instead of
  sending.

Because the command makes the bot post an album, it is guarded like the other
admin commands:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- the global rate-limit middleware still applies.

### Chat member moderation

The `/banchatmember <chat_id> <user_id> [until_date_unix] [revoke=true|false]`
admin command calls Telegram Bot API `banChatMember` through aiogram's typed
API. It is intended for moderator-run group, supergroup, and channel
administration from trusted operations chats.

The target `chat_id` and `user_id` are required. The optional
`until_date_unix` is a Unix timestamp in seconds; omit it or pass `0` for a
permanent ban. Telegram treats durations shorter than 30 seconds or longer than
366 days as permanent. The optional `revoke=true|false` flag controls whether
the user's previous messages are deleted where Telegram supports that choice;
Telegram always revokes messages in supergroups and channels.

The bot must already be an administrator in the target chat with
`can_restrict_members`. No special update subscription is required because the
command is initiated by a normal Telegram message update. Telegram permission
errors such as missing admin rights, unknown chats, or users that cannot be
restricted are reported back to the admin chat.

Because the command removes a user from a chat, it is guarded like the other
admin commands:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- the global rate-limit middleware still applies.

The `/banchatsenderchat <chat_id> <sender_chat_id>` admin command calls
Telegram Bot API `banChatSenderChat` through aiogram's typed API. It is
intended for moderator-run supergroup and channel administration from trusted
operations chats, when a channel must be blocked from posting as a sender chat.

The target `chat_id` and `sender_chat_id` are required. The bot must already be
an administrator in the target supergroup or channel with `can_restrict_members`.
No special update subscription is required because the command is initiated by
a normal Telegram message update. Telegram permission errors such as missing
admin rights, unknown chats, or sender chats that cannot be restricted are
reported back to the admin chat.

Because the command blocks a channel identity from posting into a target chat,
it is guarded like the other admin commands:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- the global rate-limit middleware still applies.

The `/unbanchatmember <chat_id> <user_id> [only_if_banned=true|false]`
admin command calls Telegram Bot API `unbanChatMember` through aiogram's typed
API. It is intended for moderator-run group, supergroup, and channel
administration from trusted operations chats.

The target `chat_id` and `user_id` are required. The optional
`only_if_banned=true|false` flag is passed to Telegram as `only_if_banned`; when
omitted, Telegram uses its default behavior. The bot must already be an
administrator in the target chat with `can_restrict_members`. No special update
subscription is required because the command is initiated by a normal Telegram
message update. Telegram permission errors such as missing admin rights, unknown
chats, or users that cannot be unbanned are reported back to the admin chat.

Because the command restores access to a chat, it is guarded like the other
admin commands:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- the global rate-limit middleware still applies.

The `/unbanchatsenderchat <chat_id> <sender_chat_id>` admin command calls
Telegram Bot API `unbanChatSenderChat` through aiogram's typed API. It is
intended for moderator-run supergroup and channel administration from trusted
operations chats, when a previously banned channel identity must be allowed to
post as a sender chat again.

The target `chat_id` and `sender_chat_id` are required. The bot must already be
an administrator in the target supergroup or channel with `can_restrict_members`.
No special update subscription is required because the command is initiated by
a normal Telegram message update. Telegram permission errors such as missing
admin rights, unknown chats, or sender chats that cannot be unbanned are
reported back to the admin chat.

Because the command restores a channel identity's ability to post into a target
chat, it is guarded like the other admin commands:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- the global rate-limit middleware still applies.

The `/restrictchatmember <chat_id> <user_id> <mute|readonly|unrestrict>
[until_date_unix] [independent=true|false]` admin command calls Telegram Bot
API `restrictChatMember` through aiogram's typed API. It is intended for
moderator-run group and supergroup permission changes from trusted operations
chats.

The target `chat_id`, `user_id`, and preset are required. `mute` denies sending
messages, `readonly` allows text messages but denies media, polls, reactions,
link previews, invites, pins and topic management, and `unrestrict` restores
common member permissions. The optional `until_date_unix` is a Unix timestamp
in seconds; omit it or pass `0` for a permanent restriction. Telegram treats
durations shorter than 30 seconds or longer than 366 days as permanent. The
optional `independent=true|false` flag is passed as
`use_independent_chat_permissions`.

The bot must already be an administrator in the target group or supergroup
with `can_restrict_members`. No special update subscription is required because
the command is initiated by a normal Telegram message update. Telegram
permission errors such as missing admin rights, unknown chats, or users that
cannot be restricted are reported back to the admin chat.

Because the command changes user permissions, it is guarded like the other
admin commands:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- the global rate-limit middleware still applies.

### Pin chat messages

The `/pinchatmessage <chat_id> <message_id> [silent|loud]` admin command calls
Telegram Bot API `pinChatMessage` through aiogram's typed API. It is intended
for trusted operators to pin operational notices, moderation messages, or other
important messages in groups, supergroups, or channels.

The target `chat_id` and `message_id` are required. The optional notification
flag controls Telegram's `disable_notification` parameter: pass `silent` to pin
without notifying members, `loud` to request a notification, or omit the flag to
use Telegram's default behaviour. Rollback is manual: unpin the message in
Telegram or run `/unpinchatmessage <chat_id> <message_id>`.

The bot must already be an administrator in the target chat with
`can_pin_messages` in groups and supergroups, or `can_edit_messages` in
channels. No special update subscription is required because the command is
initiated by a normal Telegram message update. Telegram permission errors,
unknown chats, invalid message ids, or messages that cannot be pinned are
reported back to the admin chat.

Because the command changes visible chat state, it is guarded like the other
admin commands:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- the global rate-limit middleware still applies.

### Unpin chat messages

The `/unpinchatmessage <chat_id> [message_id]` admin command calls Telegram Bot
API `unpinChatMessage` through aiogram's typed API. It is intended for trusted
operators to remove stale, incorrect, or incident-related pinned messages from
groups, supergroups, or channels.

The target `chat_id` is required. The optional `message_id` identifies a pinned
message to unpin; when omitted, Telegram unpins the most recent pinned message.
Rollback is manual: pin the message again in Telegram or through another
operational tool.

The bot must already be an administrator in the target chat with
`can_pin_messages` in groups and supergroups, or `can_edit_messages` in
channels. No special update subscription is required because the command is
initiated by a normal Telegram message update. Telegram permission errors,
unknown chats, or messages that are not pinned are reported back to the admin
chat.

Because the command changes visible chat state, it is guarded like the other
admin commands:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- the global rate-limit middleware still applies.

### Set and delete chat photo

The `/setchatphoto <chat_id> <photo_path>` admin command calls Telegram Bot API
`setChatPhoto` through aiogram's typed API. It is intended for trusted
operators to update the visible photo of a group or supergroup during rebrand,
incident response, or moderation workflows.

Telegram requires `setChatPhoto` to upload a fresh image file, not reuse a
remote URL or `file_id`, so `photo_path` must point to a local image file
available to the running bot process. The bot must already be an administrator
in the target group or supergroup with the right to change chat information. No
special update subscription is required because the command is initiated by a
normal Telegram message update. Telegram permission, file, size, and image
validation errors are reported back to the admin chat.

Because the command changes visible chat metadata, it is guarded like the other
admin commands:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- the global rate-limit middleware still applies.

### Set chat sticker set

The `/setchatstickerset <chat_id> <sticker_set_name>` admin command calls
Telegram Bot API `setChatStickerSet` through aiogram's typed API. It is intended
for trusted operators to assign a group sticker set to a supergroup.

The command takes the target `chat_id` and the sticker set name. Telegram only
supports this method for supergroups, and the bot must already be an
administrator in the target supergroup with the right to change chat
information. No special update subscription is required because the command is
initiated by a normal Telegram message update. Telegram permission, chat type,
or sticker set validation errors are reported back to the admin chat.

Because the command changes visible chat metadata, it is guarded like the other
admin commands:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- the global rate-limit middleware still applies.

### Delete chat sticker set

The `/deletechatstickerset <chat_id>` admin command calls Telegram Bot API
`deleteChatStickerSet` through aiogram's typed API. It is intended for trusted
operators to remove the group sticker set from a supergroup.

The command takes only the target `chat_id`. Telegram only supports this method
for supergroups, and the bot must already be an administrator in the target
supergroup with the right to change chat information. No special update
subscription is required because the command is initiated by a normal Telegram
message update. Telegram permission, chat type, missing sticker set, or unknown
chat errors are reported back to the admin chat.

Rollback is manual: run `/setchatstickerset <chat_id> <sticker_set_name>` with
the previous sticker set name.

Because the command changes visible chat metadata, it is guarded like the other
admin commands:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- the global rate-limit middleware still applies.

### Get sticker set

The `/getstickerset <sticker_set_name>` admin command calls Telegram Bot API
`getStickerSet` through an isolated raw Bot API helper because the project pins
`aiogram==3.3.0`. It is intended for trusted operations chats when a moderator
or operator needs to inspect a sticker/custom emoji set before using it in
creative media flows or sticker set lifecycle work.

The command takes the sticker set `name`, not its display title, URL or sticker
`file_id`. Telegram returns a `StickerSet` with its title, type and stickers;
the bot responds with the set metadata and the first sticker `file_id` values
for operational inspection. No special update subscription is required because
the scenario starts from a normal command message. Telegram validation,
transport and rate-limit errors are reported back to the admin chat.

This command does not call `free-claude-code`, does not mutate Telegram state
and has no Telegram-side rollback step. To disable the operational surface,
remove the command chat from `TELEGRAM_ADMIN_CHAT_IDS`.

Because the command exposes reusable sticker identifiers, it is guarded like
the other admin commands:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- the global rate-limit middleware still applies.

The `/deletechatphoto <chat_id>` admin command calls Telegram Bot API
`deleteChatPhoto` through aiogram's typed API. It is intended for trusted
operators to remove the current group or supergroup photo after an incident,
rebrand, or moderation decision.

The command takes only the target `chat_id`. Telegram removes the current chat
photo when the call succeeds. Rollback is manual: set a new chat photo in
Telegram chat administration or through another operational tool.

The bot must already be an administrator in the target group or supergroup with
the right to change chat information. No special update subscription is
required because the command is initiated by a normal Telegram message update.
Telegram permission errors such as missing admin rights, unknown chats, or chats
without a removable photo are reported back to the admin chat.

Because the command changes visible chat metadata, it is guarded like the other
admin commands:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- the global rate-limit middleware still applies.

The `/promotechatmember <chat_id> <user_id> <moderator|manager|demote>` admin
command calls Telegram Bot API `promoteChatMember` through aiogram's typed API.
It is intended for trusted operators to promote or demote members in groups,
supergroups and channels without exposing this power to ordinary chats.

The target `chat_id`, `user_id`, and preset are required. `moderator` grants
common moderation rights (`can_manage_chat`, `can_delete_messages`,
`can_manage_video_chats`, `can_restrict_members`) but does not grant the ability
to promote other members. `manager` also grants common management rights such as
`can_change_info`, `can_invite_users`, `can_pin_messages` and
`can_manage_topics`. `demote` clears the common administrator rights that the
command manages.

The bot must already be an administrator in the target chat with
`can_promote_members`, and it can only grant rights that it has itself. No
special update subscription is required because the command is initiated by a
normal Telegram message update. Telegram permission errors such as missing admin
rights, insufficient grantable rights, unknown chats, or users that cannot be
promoted are reported back to the admin chat.

Because the command changes administrator privileges, it is guarded like the
other admin commands:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- the global rate-limit middleware still applies.

### Get chat information

The `/getchat <chat_id>` admin command calls Telegram Bot API `getChat` through
aiogram's typed API. It is intended for trusted operations chats when an
administrator needs to inspect Telegram metadata for a private chat, group,
supergroup or channel known to the bot.

The command takes only the target `chat_id`. When Telegram succeeds, the bot
returns a concise HTML summary with the chat id, type and common optional
fields such as title, username, bio, description, invite link, forum flag,
protected-content flag, linked chat id, auto-delete timer and slow-mode delay
when Telegram includes them in the response.

The bot must be able to access the target chat. For groups, supergroups and
channels this usually means the bot is already a member; Telegram permission
errors such as unknown chats, missing membership or inaccessible private chats
are reported back to the admin chat.

Because the command may expose private chat metadata, it is guarded like the
other admin commands:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- the global rate-limit middleware still applies.

### Get chat member count

The `/getchatmembercount <chat_id>` admin command calls Telegram Bot API
`getChatMemberCount` through aiogram's typed API. It is intended for trusted
operations chats when an administrator needs a quick size check for a group,
supergroup or channel known to the bot.

The command takes only the target `chat_id` and returns Telegram's integer
member count. The bot must be able to access the target chat; for groups,
supergroups and channels this usually means the bot is already a member.
Telegram permission errors such as unknown chats, missing membership,
restricted access or rate limits are reported back to the admin chat. No
special update subscriptions are required because the scenario starts from a
normal command message.

Because the command may expose private membership metadata, it is guarded like
the other admin commands:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- the global rate-limit middleware still applies.

### Get chat member

The `/getchatmember <chat_id> <user_id>` admin command calls Telegram Bot API
`getChatMember` through aiogram's typed API. It is intended for trusted
operations chats when an administrator needs to inspect a user's current status
and permissions in a group, supergroup or channel known to the bot.

The command takes the target `chat_id` and `user_id`. When Telegram succeeds,
the bot returns a concise HTML summary with the requested ids, Telegram member
status, display name, username, custom title, anonymity/member flags and
enabled permission fields when Telegram includes them in the response. The bot
must be able to access the target chat; depending on chat type and privacy
settings Telegram may require the bot to be a member or administrator.
Telegram permission errors such as unknown chats, inaccessible users,
insufficient rights or rate limits are reported back to the admin chat.

Because the command may expose private membership metadata, it is guarded like
the other admin commands:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- the global rate-limit middleware still applies.

### Get chat administrators

The `/getchatadministrators <chat_id>` admin command calls Telegram Bot API
`getChatAdministrators` through aiogram's typed API. It is intended for trusted
operations chats when an administrator needs to audit who currently has
administrator status in a group, supergroup or channel and which rights
Telegram reports for those administrators.

The command takes only the target `chat_id` and returns a concise HTML summary
with the administrator count, user id, display name, username, status, custom
title, anonymity flag and enabled administrator rights when Telegram includes
them. The bot must be able to access the target chat; for groups, supergroups
and channels this usually means the bot is a member, and Telegram may require
administrator status depending on the chat type and privacy settings. Telegram
permission errors such as unknown chats, missing membership, missing
administrator rights or rate limits are reported back to the admin chat. No
special update subscriptions are required because the scenario starts from a
normal command message.

Because the command exposes privileged membership metadata, it is guarded like
the other admin commands:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- the global rate-limit middleware still applies;
- rollback is operational: remove the command chat from
  `TELEGRAM_ADMIN_CHAT_IDS` or revoke the bot's access to the target chat.

### Forum topic icon stickers

The `/forumtopiciconstickers` admin command calls Telegram Bot API
`getForumTopicIconStickers` through an isolated raw Bot API helper because the
project pins `aiogram==3.3.0`. It is intended for trusted operations chats when
a moderator prepares forum-topic automation and needs to inspect which custom
emoji stickers Telegram allows as topic icons before creating or editing topics
in a supergroup.

The Telegram method has no parameters and returns `Sticker` objects. The bot
responds with the number of available stickers and, for each item, the emoji,
`custom_emoji_id` and sticker set name when Telegram includes them. Those
`custom_emoji_id` values can later be used as `icon_custom_emoji_id` in forum
topic management flows. No special update subscription is required because the
scenario starts from a normal command message. Telegram transport, rate-limit
or API errors are reported back to the admin chat.

This command does not call `free-claude-code`, does not mutate chat state and
has no Telegram-side rollback step. To disable the operational surface, remove
the command chat from `TELEGRAM_ADMIN_CHAT_IDS`.

Because the command exposes operational metadata for forum-topic automation, it
is guarded like the other admin commands:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- the global rate-limit middleware still applies.

### Create forum topic

The `/createforumtopic` admin command calls Telegram Bot API
`createForumTopic` through an isolated raw Bot API helper because the project
pins `aiogram==3.3.0`. It is intended for trusted operations chats when a
moderator creates a triage or support topic in a supergroup, separate from the
normal Claude chat flow.

Usage:

```text
/createforumtopic <chat_id> <name> [icon_color=<rgb_int>] [icon_custom_emoji_id=<id>]
```

The topic name is required and limited to 128 characters. The bot must be an
administrator in the target supergroup with the right to manage topics.
`icon_color` is Telegram's RGB integer topic icon color; `icon_custom_emoji_id`
can be discovered with `/forumtopiciconstickers`. No special update
subscription is required because the scenario starts from a normal admin
command message. Telegram transport, rate-limit or API errors are reported
back to the admin chat.

This command does not call `free-claude-code`, mutates only the addressed
supergroup by creating a new forum topic, and is guarded by
`TELEGRAM_ADMIN_CHAT_IDS` with no fallback to `TELEGRAM_ALLOWED_CHAT_IDS`.
Rollback is operational: delete the created topic in Telegram or with a future
forum-topic lifecycle command when available.

### Edit forum topic

The `/editforumtopic` admin command calls Telegram Bot API `editForumTopic`
through an isolated raw Bot API helper because the project pins
`aiogram==3.3.0`. It is intended for trusted operations chats when a moderator
needs to rename a forum topic or set its `icon_custom_emoji_id` in a
supergroup.

Usage:

```text
/editforumtopic <chat_id> <message_thread_id> [name=<text>] [icon_custom_emoji_id=<id>]
```

At least one editable field is required. Topic names are limited to 128
characters. `icon_custom_emoji_id` values can be discovered with
`/forumtopiciconstickers`. No special update subscription is required because
the scenario starts from a normal command message. Telegram transport,
rate-limit or API errors are reported back to the admin chat.

This command does not call `free-claude-code`, mutates only the addressed forum
topic and is guarded by `TELEGRAM_ADMIN_CHAT_IDS` with no fallback to
`TELEGRAM_ALLOWED_CHAT_IDS`. Rollback is operational: run `/editforumtopic`
again with the previous topic name or icon custom emoji id.

### Edit General forum topic

The `/editgeneralforumtopic` admin command calls Telegram Bot API
`editGeneralForumTopic` through an isolated raw Bot API helper because the
project pins `aiogram==3.3.0`. It is intended for trusted operations chats when
a moderator needs to rename the General topic in a forum-enabled supergroup,
separate from the normal Claude chat flow and from non-General topic
management.

Usage:

```text
/editgeneralforumtopic <chat_id> <name>
```

The `name` parameter is required and limited to 128 characters. The bot must be
an administrator in the target supergroup with the right to manage topics. No
special update subscription is required because the scenario starts from a
normal admin command message. Telegram transport, rate-limit or API errors are
reported back to the admin chat.

This command does not call `free-claude-code`, mutates only the General topic
name in the addressed supergroup, and is guarded by `TELEGRAM_ADMIN_CHAT_IDS`
with no fallback to `TELEGRAM_ALLOWED_CHAT_IDS`. Rollback is operational: run
`/editgeneralforumtopic` again with the previous General topic name.

### Close forum topic

The `/closeforumtopic` admin command calls Telegram Bot API `closeForumTopic`
through an isolated raw Bot API helper because the project pins
`aiogram==3.3.0`. It is intended for trusted operations chats when a moderator
needs to close a finished triage or support topic in a supergroup, separate
from the normal Claude chat flow.

Usage:

```text
/closeforumtopic <chat_id> <message_thread_id>
```

The bot must be an administrator in the target supergroup with the right to
manage topics. `message_thread_id` must identify an existing forum topic and
must be greater than zero. No special update subscription is required because
the scenario starts from a normal admin command message. Telegram transport,
rate-limit or API errors are reported back to the admin chat.

This command does not call `free-claude-code`, mutates only the addressed forum
topic and is guarded by `TELEGRAM_ADMIN_CHAT_IDS` with no fallback to
`TELEGRAM_ALLOWED_CHAT_IDS`. Rollback is operational: reopen the topic with
`/reopenforumtopic` after confirming the same `chat_id` and
`message_thread_id`.

### Close General forum topic

The `/closegeneralforumtopic` admin command calls Telegram Bot API
`closeGeneralForumTopic` through an isolated raw Bot API helper because the
project pins `aiogram==3.3.0`. It is intended for trusted operations chats when
a moderator needs to close the General topic in a forum-enabled supergroup,
separate from the normal Claude chat flow and from non-General topic
management.

Usage:

```text
/closegeneralforumtopic <chat_id>
```

The bot must be an administrator in the target supergroup with the right to
manage topics. No special update subscription is required because the scenario
starts from a normal admin command message. Telegram transport, rate-limit or
API errors are reported back to the admin chat.

This command does not call `free-claude-code`, mutates only the General topic
state in the addressed supergroup, and is guarded by `TELEGRAM_ADMIN_CHAT_IDS`
with no fallback to `TELEGRAM_ALLOWED_CHAT_IDS`. Rollback is operational:
reopen the General topic with `/reopengeneralforumtopic` after confirming the
same `chat_id`.

### Reopen forum topic

The `/reopenforumtopic` admin command calls Telegram Bot API
`reopenForumTopic` through an isolated raw Bot API helper because the project
pins `aiogram==3.3.0`. It is intended for trusted operations chats when a
moderator needs to reopen a previously closed triage or support topic in a
supergroup, separate from the normal Claude chat flow.

Usage:

```text
/reopenforumtopic <chat_id> <message_thread_id>
```

The bot must be an administrator in the target supergroup with the right to
manage topics. `message_thread_id` must identify an existing closed forum
topic and must be greater than zero. No special update subscription is
required because the scenario starts from a normal admin command message.
Telegram transport, rate-limit or API errors are reported back to the admin
chat.

This command does not call `free-claude-code`, mutates only the addressed forum
topic and is guarded by `TELEGRAM_ADMIN_CHAT_IDS` with no fallback to
`TELEGRAM_ALLOWED_CHAT_IDS`. Rollback is operational: close the topic again in
Telegram or with a future forum-topic lifecycle command when available.

### Reopen General forum topic

The `/reopengeneralforumtopic` admin command calls Telegram Bot API
`reopenGeneralForumTopic` through an isolated raw Bot API helper because the
project pins `aiogram==3.3.0`. It is intended for trusted operations chats when
a moderator needs to reopen the General topic in a forum-enabled supergroup,
separate from the normal Claude chat flow and from non-General topic
management.

Usage:

```text
/reopengeneralforumtopic <chat_id>
```

The bot must be an administrator in the target supergroup with the right to
manage topics. No special update subscription is required because the scenario
starts from a normal admin command message. Telegram transport, rate-limit or
API errors are reported back to the admin chat.

This command does not call `free-claude-code`, mutates only the General topic
state in the addressed supergroup, and is guarded by `TELEGRAM_ADMIN_CHAT_IDS`
with no fallback to `TELEGRAM_ALLOWED_CHAT_IDS`. Rollback is operational: close
the General topic again with `/closegeneralforumtopic` after confirming the
same `chat_id`.

### Hide General forum topic

The `/hidegeneralforumtopic` admin command calls Telegram Bot API
`hideGeneralForumTopic` through an isolated raw Bot API helper because the
project pins `aiogram==3.3.0`. It is intended for trusted operations chats when
a moderator needs to hide the General topic in a forum-enabled supergroup,
separate from the normal Claude chat flow and from non-General topic
management.

Usage:

```text
/hidegeneralforumtopic <chat_id>
```

The bot must be an administrator in the target supergroup with the right to
manage topics. No special update subscription is required because the scenario
starts from a normal admin command message. Telegram transport, rate-limit or
API errors are reported back to the admin chat.

This command does not call `free-claude-code`, mutates only the General topic
visibility in the addressed supergroup, and is guarded by
`TELEGRAM_ADMIN_CHAT_IDS` with no fallback to `TELEGRAM_ALLOWED_CHAT_IDS`.
Rollback is operational: unhide the General topic with
`/unhidegeneralforumtopic` after confirming the same `chat_id`.

### Unhide General forum topic

The `/unhidegeneralforumtopic` admin command calls Telegram Bot API
`unhideGeneralForumTopic` through an isolated raw Bot API helper because the
project pins `aiogram==3.3.0`. It is intended for trusted operations chats when
a moderator needs to restore the General topic visibility in a forum-enabled
supergroup, separate from the normal Claude chat flow and from non-General
topic management.

Usage:

```text
/unhidegeneralforumtopic <chat_id>
```

The bot must be an administrator in the target supergroup with the right to
manage topics. No special update subscription is required because the scenario
starts from a normal admin command message. Telegram transport, rate-limit or
API errors are reported back to the admin chat.

This command does not call `free-claude-code`, mutates only the General topic
visibility in the addressed supergroup, and is guarded by
`TELEGRAM_ADMIN_CHAT_IDS` with no fallback to `TELEGRAM_ALLOWED_CHAT_IDS`.
Rollback is operational: hide the General topic again with
`/hidegeneralforumtopic` after confirming the same `chat_id`.

### Delete forum topic

The `/deleteforumtopic` admin command calls Telegram Bot API
`deleteForumTopic` through an isolated raw Bot API helper because the project
pins `aiogram==3.3.0`. It is intended for trusted operations chats when a
moderator needs to remove an obsolete triage or support topic in a supergroup,
separate from the normal Claude chat flow.

Usage:

```text
/deleteforumtopic <chat_id> <message_thread_id>
```

The bot must be an administrator in the target supergroup with the right to
manage topics. `message_thread_id` must identify an existing forum topic and
must be greater than zero. No special update subscription is required because
the scenario starts from a normal admin command message. Telegram transport,
rate-limit or API errors are reported back to the admin chat.

This command does not call `free-claude-code`, deletes only the addressed
forum topic and is guarded by `TELEGRAM_ADMIN_CHAT_IDS` with no fallback to
`TELEGRAM_ALLOWED_CHAT_IDS`. Rollback is operational and lossy: recreate the
topic with `/createforumtopic` and move or copy relevant messages if needed.

### Unpin all forum topic messages

The `/unpinallforumtopicmessages` admin command calls Telegram Bot API
`unpinAllForumTopicMessages` through an isolated raw Bot API helper because
the project pins `aiogram==3.3.0`. It is intended for trusted operations chats
when a moderator needs to clear all pinned messages in a specific forum topic
without affecting other topics or the normal Claude chat flow.

Usage:

```text
/unpinallforumtopicmessages <chat_id> <message_thread_id>
```

The bot must be an administrator in the target supergroup with the right to
manage topics. `message_thread_id` must identify an existing forum topic and
must be greater than zero. No special update subscription is required because
the scenario starts from a normal admin command message. Telegram transport,
rate-limit or API errors are reported back to the admin chat.

This command does not call `free-claude-code`, mutates only pinned-message
state in the addressed forum topic and is guarded by `TELEGRAM_ADMIN_CHAT_IDS`
with no fallback to `TELEGRAM_ALLOWED_CHAT_IDS`. Rollback is operational: pin
the required messages again in Telegram or with `/pinchatmessage`.

### Unpin all General forum topic messages

The `/unpinallgeneralforumtopicmessages` admin command calls Telegram Bot API
`unpinAllGeneralForumTopicMessages` through an isolated raw Bot API helper
because the project pins `aiogram==3.3.0`. It is intended for trusted
operations chats when a moderator needs to clear all pinned messages in the
General topic of a forum-enabled supergroup, separate from non-General topics
and the normal Claude chat flow.

Usage:

```text
/unpinallgeneralforumtopicmessages <chat_id>
```

The bot must be an administrator in the target supergroup with the right to
manage topics. The method accepts only `chat_id`; the General topic is implied
by Telegram, so no `message_thread_id` is sent. No special update subscription
is required because the scenario starts from a normal admin command message.
Telegram transport, rate-limit or API errors are reported back to the admin
chat.

This command does not call `free-claude-code`, mutates only pinned-message
state in the General topic and is guarded by `TELEGRAM_ADMIN_CHAT_IDS` with no
fallback to `TELEGRAM_ALLOWED_CHAT_IDS`. Rollback is operational: pin the
required General topic messages again in Telegram or with `/pinchatmessage`.

### Get user personal chat messages

The `/userpersonalchatmessages <user_id> [limit]` admin command calls Telegram
Bot API `getUserPersonalChatMessages` through aiogram's typed API. It is
intended for trusted operations chats when an administrator needs to inspect
recent messages in the personal chat between a known user and the bot.

The command takes the target `user_id` and an optional `limit` from 1 to 100
(default 100). It returns a concise HTML summary with the number of messages
Telegram returned and basic message metadata: message id, personal chat id,
chat type, title when present, and date. Telegram permission errors such as an
unknown user, unavailable personal chat history, restricted access or rate
limits are reported back to the admin chat. No special update subscriptions are
required because the scenario starts from a normal command message.

Because the command can expose private conversation metadata, it is guarded
like the other admin commands:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- the global rate-limit middleware still applies;
- rollback is operational: remove the command chat from
  `TELEGRAM_ADMIN_CHAT_IDS` or revoke the bot's access to the user's personal
  chat.

### Export chat invite link

The `/exportchatinvitelink <chat_id>` admin command calls Telegram Bot API
`exportChatInviteLink` through aiogram's typed API. It is intended for trusted
operations chats when moderators need to rotate and retrieve the primary invite
link for a group, supergroup or channel.

The command takes only the target `chat_id`. When Telegram succeeds, it returns
the new primary invite link and revokes the previously generated primary invite
link. Existing non-primary invite links created separately in Telegram are not
managed by this command.

The bot must already be an administrator in the target chat with
`can_invite_users`. No special update subscription is required because the
scenario is initiated by a normal Telegram message update. Telegram permission
errors such as missing admin rights, unknown chats, unsupported chat types or
insufficient invite-link rights are reported back to the admin chat. Rollback is
manual: create or export another invite link in Telegram's chat administration
UI or rerun the command to rotate the primary link again.

Because the command exposes an access link to a chat, it is guarded like the
other admin commands:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- the global rate-limit middleware still applies.

### Leave chat

The `/leavechat <chat_id> confirm` admin command calls Telegram Bot API
`leaveChat` through aiogram's typed API. It removes the bot from a group,
supergroup or channel where the bot is currently a member. The confirmation
argument is mandatory because the action stops updates from that chat until the
bot is added again.

The method takes only the target `chat_id` and returns `True` on success. It
does not require the bot to hold administrator rights, but the bot must be a
current member of the target chat. No special update subscription is required
because the scenario is initiated by a normal Telegram message update.
Telegram errors such as unknown chats, missing membership, kicks or rate limits
are reported back to the admin chat. Rollback is manual: add the bot to the
chat again and restore any required administrator rights.

Because the command changes bot membership, it is guarded like the other
destructive admin commands:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- the global rate-limit middleware still applies.

### Create chat invite link

The `/createchatinvitelink <chat_id> [name=<text>] [expire_date=<unix_time>] [member_limit=<1-99999>] [creates_join_request=true|false]` admin command calls Telegram Bot API `createChatInviteLink`. It creates an additional invite link for a group, supergroup or channel. The project still pins `aiogram==3.3.0`, so the service uses aiogram's typed `create_chat_invite_link` method when the runtime provides it and falls back to an isolated raw Bot API helper otherwise.

The bot must already be an administrator in the target chat with `can_invite_users`. `member_limit` must be in Telegram's `1..99999` range, and `creates_join_request=true` cannot be combined with `member_limit`. No special update subscription is required because the scenario is initiated by a normal Telegram message update. Telegram permission and validation errors are reported back to the admin chat. Rollback is manual: revoke the created invite link in Telegram chat administration, edit it with `/editchatinvitelink`, or create a replacement link.

Because the command creates an access link to a chat, it is guarded like the other admin commands:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- the global rate-limit middleware still applies.

### Approve chat join request

The `/approvechatjoinrequest <chat_id> <user_id>` admin command calls Telegram Bot API `approveChatJoinRequest`. It approves a user's pending request to join a group, supergroup or channel. The project still pins `aiogram==3.3.0`, so the service uses aiogram's typed `approve_chat_join_request` method when the runtime provides it and falls back to an isolated raw Bot API helper otherwise.

The bot must already be an administrator in the target chat with `can_invite_users`. The command needs a concrete `user_id` from a pending join request; the bot must receive or otherwise know that pending request via Telegram operations outside this command. No special update subscription is required for the command itself because the approval scenario is initiated by a normal Telegram message update from an admin chat. Telegram permission, missing-request and rate-limit errors are reported back to the admin chat. Rollback is manual: remove or ban the user in Telegram chat administration if the request was approved by mistake.

Because the command grants access to a chat, it is guarded like the other admin commands:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- the global rate-limit middleware still applies.

### Decline chat join request

The `/declinechatjoinrequest <chat_id> <user_id>` admin command calls Telegram Bot API `declineChatJoinRequest`. It declines a user's pending request to join a group, supergroup or channel. The project still pins `aiogram==3.3.0`, so the service uses aiogram's typed `decline_chat_join_request` method when the runtime provides it and falls back to an isolated raw Bot API helper otherwise.

The bot must already be an administrator in the target chat with `can_invite_users`. The command needs a concrete `user_id` from a pending join request; the bot must receive or otherwise know that pending request via Telegram operations outside this command. No special update subscription is required for the command itself because the decline scenario is initiated by a normal Telegram message update from an admin chat. Telegram permission, missing-request and rate-limit errors are reported back to the admin chat. Rollback is manual: ask the user to submit a new join request or add them through another invite flow.

Because the command denies access to a chat, it is guarded like the other admin commands:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- the global rate-limit middleware still applies.

### Edit chat invite link

The `/editchatinvitelink <chat_id> <invite_link> [name=<text>] [expire_date=<unix_time>] [member_limit=<1-99999>] [creates_join_request=true|false]` admin command calls Telegram Bot API `editChatInviteLink`. It edits an existing non-primary invite link for a group, supergroup or channel. The project still pins `aiogram==3.3.0`, so the service uses aiogram's typed `edit_chat_invite_link` method when the runtime provides it and falls back to an isolated raw Bot API helper otherwise.

The bot must already be an administrator in the target chat with `can_invite_users`. `member_limit` must be in Telegram's `1..99999` range, and `creates_join_request=true` cannot be combined with `member_limit`. No special update subscription is required because the scenario is initiated by a normal Telegram message update. Telegram permission and validation errors are reported back to the admin chat. Rollback is manual: edit the link again with the previous options, revoke the link in Telegram chat administration, or create a replacement link.

Because the command changes an access link to a chat, it is guarded like the other admin commands:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- the global rate-limit middleware still applies.

### Revoke chat invite link

The `/revokechatinvitelink <chat_id> <invite_link>` admin command calls Telegram Bot API `revokeChatInviteLink`. It revokes an invite link created by the bot for a group, supergroup or channel. If the primary link is revoked, Telegram automatically generates a new primary link. The project still pins `aiogram==3.3.0`, so the service uses aiogram's typed `revoke_chat_invite_link` method when the runtime provides it and falls back to an isolated raw Bot API helper otherwise.

The bot must already be an administrator in the target chat with `can_invite_users`. The command accepts only `chat_id` and `invite_link`; no special update subscription is required because the scenario is initiated by a normal Telegram message update. Telegram permission and validation errors are reported back to the admin chat. Rollback is manual: create a replacement link with `/createchatinvitelink`, export a replacement primary link with `/exportchatinvitelink`, or restore access through Telegram chat administration.

Because the command removes an access link to a chat, it is guarded like the other admin commands:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- the global rate-limit middleware still applies.

### Create chat subscription invite link

The `/createchatsubscriptioninvitelink <chat_id> <subscription_price> [name=<text>] [subscription_period=2592000]` admin command calls Telegram Bot API `createChatSubscriptionInviteLink`. It creates a paid subscription invite link for a supergroup or channel. The project still pins `aiogram==3.3.0`, so the service uses aiogram's typed `create_chat_subscription_invite_link` method when the runtime provides it and falls back to an isolated raw Bot API helper otherwise.

The bot must already be an administrator in the target chat with `can_invite_users`. `subscription_price` is validated locally in Telegram's `1..10000` Stars range, `name` must be 0-32 characters, and Telegram currently requires `subscription_period=2592000` seconds. No special update subscription is required because the scenario is initiated by a normal Telegram message update. Telegram permission, validation and rate-limit errors are reported back to the admin chat. Rollback is manual: revoke the created subscription invite link in Telegram chat administration, edit its name with `/editchatsubscriptioninvitelink`, or create a replacement subscription link.

Because the command creates a paid access link to a chat, it is guarded like the other admin commands:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- the global rate-limit middleware still applies.

### Edit chat subscription invite link

The `/editchatsubscriptioninvitelink <chat_id> <invite_link> [name=<text>]` admin command calls Telegram Bot API `editChatSubscriptionInviteLink`. It edits a subscription invite link created by the bot for a supergroup or channel. The project still pins `aiogram==3.3.0`, so the service uses aiogram's typed `edit_chat_subscription_invite_link` method when the runtime provides it and falls back to an isolated raw Bot API helper otherwise.

The bot must already be an administrator in the target chat with `can_invite_users`. Telegram only allows changing the optional link `name`, which must be 0-32 characters. No special update subscription is required because the scenario is initiated by a normal Telegram message update. Telegram permission and validation errors are reported back to the admin chat. Rollback is manual: edit the link again with the previous name, revoke the link in Telegram chat administration, or create a replacement subscription link.

Because the command changes a paid access link to a chat, it is guarded like the other admin commands:

- it is only available to chats listed in `TELEGRAM_ADMIN_CHAT_IDS` and does
  **not** fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if `TELEGRAM_ADMIN_CHAT_IDS`
  is empty, the command is disabled;
- the global rate-limit middleware still applies.

### Group privacy mode

When the bot is mentioned in a group chat (e.g., `@YourBot hello`) or a user replies to a bot message, it can avoid shared group history. In this mode:
- The bot only sees the message where it was mentioned.
- No prior conversation history is used.
- The bot responds only to that message, ensuring privacy.

In private chats, the bot maintains full conversation history.

### Media Support

- **Images**: Send a photo; the bot will send it to Claude for multimodal analysis.
- **Documents**: Send a document (PDF, TXT, DOCX). The bot extracts text and includes it in the context.
- **Voice messages**: Send a voice note; the bot transcribes it using Whisper (if installed) and processes the text.

## Testing

Run unit tests:

```bash
pytest tests/unit
```

Integration tests (requires running bot and proxy) are in `tests/integration`.

## Functionality Analysis

See [docs/functionality-analysis.md](docs/functionality-analysis.md) for the
current feature inventory, architecture notes, test coverage, known gaps, and
recommended next steps, including Telegram Bot API method coverage.
For the per-method issue-style implementation backlog, see
[docs/telegram-bot-api-implementation-guide.md](docs/telegram-bot-api-implementation-guide.md).
The generated GitHub issue index is available in
[docs/telegram-bot-api-issue-index.md](docs/telegram-bot-api-issue-index.md).

## Project Structure

```
telegram-claude-agent/
├── bot/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app + aiogram dispatcher
│   ├── config.py               # Pydantic settings
│   ├── middlewares/
│   │   ├── logging.py          # Structured logging
│   │   └── rate_limit.py       # Rate limiting per user
│   ├── handlers/
│   │   ├── commands.py         # /start, /help, /model, /settings, /webhook, /deletewebhook, /logout, /close, /forward, /forwards, /copy, /copies, /photo, /audio, /livephoto, /document, /video, /videonote, /animation, /sticker, /getstickerset, /setstickerkeywords, /setstickersettitle, /setstickersetthumbnail, /setcustomemojithumbnail, /deletestickerset, /voice, /paidmedia, /location, /venue, /poll, /contact, /dice, /chataction, /messagedraft, /checklist, /setmycommands, /mediagroup, /clear
│   │   ├── chat.py             # Text and media message handler (shows typing… while processing)
│   │   └── inline.py           # Inline query handler
│   ├── services/
│   │   ├── claude_proxy.py     # Client for free-claude-code API
│   │   ├── webhook_delete.py   # Telegram webhook lifecycle operations
│   │   ├── webhook_info.py     # Telegram webhook diagnostics formatting
│   │   ├── log_out.py          # Telegram logOut lifecycle helper
│   │   ├── close.py            # Telegram close lifecycle helper
│   │   ├── forward_message.py  # Telegram forwardMessage relay helper
│   │   ├── forward_messages.py # Telegram forwardMessages batch relay helper
│   │   ├── copy_message.py     # Telegram copyMessage relay helper
│   │   ├── copy_messages.py    # Telegram copyMessages batch relay helper
│   │   ├── send_photo.py       # Telegram sendPhoto outbound helper
│   │   ├── send_audio.py       # Telegram sendAudio outbound helper
│   │   ├── send_live_photo.py  # Telegram sendLivePhoto raw Bot API helper
│   │   ├── send_document.py    # Telegram sendDocument outbound helper
│   │   ├── send_video.py       # Telegram sendVideo outbound helper
│   │   ├── send_video_note.py  # Telegram sendVideoNote outbound helper
│   │   ├── send_animation.py   # Telegram sendAnimation outbound helper
│   │   ├── send_sticker.py     # Telegram sendSticker outbound helper
│   │   ├── get_sticker_set.py  # Telegram getStickerSet raw Bot API helper
│   │   ├── create_new_sticker_set.py # Telegram createNewStickerSet raw helper
│   │   ├── set_sticker_mask_position.py # Telegram setStickerMaskPosition raw helper
│   │   ├── set_sticker_keywords.py # Telegram setStickerKeywords raw helper
│   │   ├── set_sticker_set_title.py # Telegram setStickerSetTitle raw helper
│   │   ├── set_sticker_set_thumbnail.py # Telegram setStickerSetThumbnail raw helper
│   │   ├── set_custom_emoji_sticker_set_thumbnail.py # Telegram setCustomEmojiStickerSetThumbnail raw helper
│   │   ├── delete_sticker_set.py # Telegram deleteStickerSet raw helper
│   │   ├── send_voice.py       # Telegram sendVoice outbound helper
│   │   ├── send_paid_media.py  # Telegram sendPaidMedia raw Bot API helper
│   │   ├── send_location.py    # Telegram sendLocation outbound helper
│   │   ├── send_venue.py       # Telegram sendVenue outbound helper
│   │   ├── send_poll.py        # Telegram sendPoll outbound helper
│   │   ├── send_contact.py     # Telegram sendContact outbound helper
│   │   ├── send_dice.py        # Telegram sendDice outbound helper
│   │   ├── send_chat_action.py # Telegram sendChatAction outbound helper (typing…)
│   │   ├── send_checklist.py   # Telegram sendChecklist raw Bot API helper
│   │   ├── send_message_draft.py # Telegram sendMessageDraft raw Bot API helper
│   │   └── send_media_group.py # Telegram sendMediaGroup outbound helper
│   └── utils/
│       ├── storage.py          # In-memory conversation storage
│       └── media.py            # Transcription, document extraction
├── tests/
│   ├── unit/
│   │   ├── test_config.py
│   │   ├── test_storage.py
│   │   └── test_claude_proxy.py
│   └── integration/
│       └── test_bot.py
├── requirements.txt
├── .env.example
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## API Compatibility

The `ClaudeProxyClient` is designed to work with the Anthropic Messages API format, which is compatible with free-claude-code. Supported endpoints:
- `POST /v1/messages` – send a message (streaming supported)
- `GET /v1/models` – list available models
- `POST /v1/messages/count_tokens` – token counting

## Security Considerations

- Always set `API_SECRET_TOKEN` when using webhook mode to verify that updates are genuinely from Telegram.
- Use HTTPS for your webhook URL.
- Keep your `FREE_CLAUDE_AUTH_TOKEN` and `TELEGRAM_BOT_TOKEN` secret; do not commit them to version control.
- The `TELEGRAM_ALLOWED_CHAT_IDS` setting can restrict operation to specific chats.
- The `/webhook` diagnostics command can expose webhook URL and delivery errors, and `/deletewebhook` changes update delivery state, so restrict both with `TELEGRAM_ADMIN_CHAT_IDS`.
- The `/logout` command is destructive (it logs the bot out of the cloud Bot API for 10 minutes), so it requires `TELEGRAM_ADMIN_CHAT_IDS` and explicit `/logout confirm`.
- The `/close` command is destructive (it closes the running bot instance on the current Bot API server), so it requires `TELEGRAM_ADMIN_CHAT_IDS` and explicit `/close confirm`.
- The `/forward` command relays a message from another chat into the admin chat, so it requires `TELEGRAM_ADMIN_CHAT_IDS` and protects the forwarded copy from re-forwarding by default.
- The `/forwards` command relays a batch of messages from another chat into the admin chat (preserving album grouping), so it requires `TELEGRAM_ADMIN_CHAT_IDS` and protects the forwarded copies from re-forwarding by default.
- The `/copy` command relays a message from another chat into the admin chat without a link to the original sender, so it requires `TELEGRAM_ADMIN_CHAT_IDS` and protects the copied message from re-forwarding by default.
- The `/copies` command relays a batch of messages from another chat into the admin chat without a link to the original sender (preserving album grouping), so it requires `TELEGRAM_ADMIN_CHAT_IDS` and protects the copied messages from re-forwarding by default.
- The `/photo` command makes the bot post an arbitrary image into the chat as a photo, so it requires `TELEGRAM_ADMIN_CHAT_IDS` and is unavailable when that list is empty.
- The `/audio` command makes the bot post an arbitrary audio file into the chat as a music track, so it requires `TELEGRAM_ADMIN_CHAT_IDS` and is unavailable when that list is empty.
- The `/livephoto` command makes the bot post an arbitrary live photo (video + cover) into the chat, so it requires `TELEGRAM_ADMIN_CHAT_IDS` and is unavailable when that list is empty.
- The `/document` command makes the bot post an arbitrary file into the chat as a document, so it requires `TELEGRAM_ADMIN_CHAT_IDS` and is unavailable when that list is empty.
- The `/video` command makes the bot post an arbitrary video into the chat as a playable video, so it requires `TELEGRAM_ADMIN_CHAT_IDS` and is unavailable when that list is empty.
- The `/videonote` command makes the bot post an arbitrary video note (rounded square video message) into the chat, so it requires `TELEGRAM_ADMIN_CHAT_IDS` and is unavailable when that list is empty.
- The `/animation` command makes the bot post an arbitrary animation (GIF or soundless video) into the chat as a playable looping clip, so it requires `TELEGRAM_ADMIN_CHAT_IDS` and is unavailable when that list is empty.
- The `/sticker` command makes the bot post an arbitrary sticker or custom emoji into the chat, so it requires `TELEGRAM_ADMIN_CHAT_IDS` and is unavailable when that list is empty.
- The `/voice` command makes the bot post an arbitrary voice message into the chat as a playable audio clip, so it requires `TELEGRAM_ADMIN_CHAT_IDS` and is unavailable when that list is empty.
- The `/paidmedia` command makes the bot post arbitrary monetized media priced in Telegram Stars into the chat, so it requires `TELEGRAM_ADMIN_CHAT_IDS` and is unavailable when that list is empty.
- The `/location` command makes the bot post an arbitrary point on the map into the chat as a location, so it requires `TELEGRAM_ADMIN_CHAT_IDS` and is unavailable when that list is empty; coordinates are kept out of the structured logs.
- The `/venue` command makes the bot post an arbitrary venue (a named place with a title and an address) into the chat, so it requires `TELEGRAM_ADMIN_CHAT_IDS` and is unavailable when that list is empty; the coordinates, title and address are kept out of the structured logs.
- The `/poll` command makes the bot post an arbitrary native poll into the chat, so it requires `TELEGRAM_ADMIN_CHAT_IDS` and is unavailable when that list is empty; the question and the answer options are kept out of the structured logs.
- The `/contact` command makes the bot post an arbitrary phone contact into the chat, so it requires `TELEGRAM_ADMIN_CHAT_IDS` and is unavailable when that list is empty; the phone number and the contact's name are kept out of the structured logs.
- The `/dice` command makes the bot post an animated dice into the chat, so it requires `TELEGRAM_ADMIN_CHAT_IDS` and is unavailable when that list is empty.
- The `/chataction` command makes the bot show a chat action in the chat, so it requires `TELEGRAM_ADMIN_CHAT_IDS` and is unavailable when that list is empty; the automatic `typing…` indicator shown while processing a request is independent of this command and is controlled by `TELEGRAM_CHAT_ACTION_ENABLED`.
- The `/messagedraft` command makes the bot post an ephemeral message draft into the (private) chat, so it requires `TELEGRAM_ADMIN_CHAT_IDS` and is unavailable when that list is empty; the draft text is kept out of the structured logs. The automatic draft-based streaming preview is independent of this command and is controlled by `TELEGRAM_MESSAGE_DRAFT_ENABLED`.
- The `/checklist` command makes the bot post an arbitrary checklist into the chat on behalf of a connected business account, so it requires `TELEGRAM_ADMIN_CHAT_IDS` and is unavailable when that list is empty; the title and task texts are kept out of the structured logs.
- The `/businessconnection` command fetches business connection owner/lifecycle metadata by `business_connection_id`, so it requires `TELEGRAM_ADMIN_CHAT_IDS`, is unavailable when that list is empty, and keeps returned owner fields out of structured logs.
- The `/businessgifts` command fetches owned gifts of a connected business account by `business_connection_id`, so it requires `TELEGRAM_ADMIN_CHAT_IDS`, is unavailable when that list is empty, and logs only the connection id, item count, next-offset presence and error shape.
- The `/convertgiftstars` command converts an owned gift of a connected business account to Telegram Stars, so it requires `TELEGRAM_ADMIN_CHAT_IDS`, explicit `confirm`, is unavailable when that list is empty, and logs only the connection id, owned gift id and error shape.
- The `/upgradegift` command upgrades an owned gift of a connected business account with Telegram Stars, so it requires `TELEGRAM_ADMIN_CHAT_IDS`, explicit `confirm`, is unavailable when that list is empty, and logs only the connection id, owned gift id, optional detail flag and error shape.
- The `/setbusinessaccountname` command changes connected business account profile metadata, so it requires `TELEGRAM_ADMIN_CHAT_IDS`, is unavailable when that list is empty, and keeps name values out of structured logs.
- The `/setbusinessaccountgiftsettings` command changes connected business account incoming gift privacy settings, so it requires `TELEGRAM_ADMIN_CHAT_IDS`, is unavailable when that list is empty, and logs only the connection id, gift button flag and enabled-type count.
- The `/managedbottoken` command returns a live managed-bot token, so it requires `TELEGRAM_ADMIN_CHAT_IDS`, is unavailable when that list is empty, and keeps the token itself out of structured logs.
- The `/managedbotaccess` command returns managed-bot access allowlist metadata, so it requires `TELEGRAM_ADMIN_CHAT_IDS`, is unavailable when that list is empty, and keeps returned user objects out of structured logs.
- The `/replacemanagedbottoken` command rotates and returns a live managed-bot token, so it requires `TELEGRAM_ADMIN_CHAT_IDS`, explicit `confirm`, is unavailable when that list is empty, and keeps token values out of structured logs.
- The `/mediagroup` command makes the bot post an arbitrary album of 2-10 media items into the chat, so it requires `TELEGRAM_ADMIN_CHAT_IDS` and is unavailable when that list is empty.
- The `/banchatmember` command removes a user from a target chat and can revoke their previous messages, so it requires `TELEGRAM_ADMIN_CHAT_IDS`, is unavailable when that list is empty, and also requires the bot to have `can_restrict_members` in the target chat.
- The `/banchatsenderchat` command blocks a channel identity from posting as a sender chat in a target supergroup or channel, so it requires `TELEGRAM_ADMIN_CHAT_IDS`, is unavailable when that list is empty, and also requires the bot to have `can_restrict_members` in the target chat.
- The `/unbanchatmember` command restores access to a target chat, so it requires `TELEGRAM_ADMIN_CHAT_IDS`, is unavailable when that list is empty, and also requires the bot to have `can_restrict_members` in the target chat.
- The `/restrictchatmember` command changes a user's permissions in a target group or supergroup, so it requires `TELEGRAM_ADMIN_CHAT_IDS`, is unavailable when that list is empty, and also requires the bot to have `can_restrict_members` in the target chat.
- The `/setchatpermissions` command changes default permissions for all non-administrator members in a target group or supergroup, so it requires `TELEGRAM_ADMIN_CHAT_IDS`, is unavailable when that list is empty, and also requires the bot to have `can_restrict_members` in the target chat.
- The `/setchatphoto` command changes the visible photo of a target group or supergroup from a local file, so it requires `TELEGRAM_ADMIN_CHAT_IDS`, is unavailable when that list is empty, and also requires the bot to have the right to change chat information in the target chat.
- The `/deletechatphoto` command removes the current photo from a target group or supergroup, so it requires `TELEGRAM_ADMIN_CHAT_IDS`, is unavailable when that list is empty, and also requires the bot to have the right to change chat information in the target chat.
- The `/promotechatmember` command changes a user's administrator privileges in a target chat, so it requires `TELEGRAM_ADMIN_CHAT_IDS`, is unavailable when that list is empty, and also requires the bot to have `can_promote_members` in the target chat.
- The `/exportchatinvitelink` command rotates and exposes the primary invite link for a target chat, so it requires `TELEGRAM_ADMIN_CHAT_IDS`, is unavailable when that list is empty, and also requires the bot to have `can_invite_users` in the target chat.
- The `/approvechatjoinrequest` command approves a user's pending request to enter a target chat, so it requires `TELEGRAM_ADMIN_CHAT_IDS`, is unavailable when that list is empty, and also requires the bot to have `can_invite_users` in the target chat.
- The `/declinechatjoinrequest` command declines a user's pending request to enter a target chat, so it requires `TELEGRAM_ADMIN_CHAT_IDS`, is unavailable when that list is empty, and also requires the bot to have `can_invite_users` in the target chat.
- The `/createchatinvitelink` command creates and exposes an additional invite link for a target chat, so it requires `TELEGRAM_ADMIN_CHAT_IDS`, is unavailable when that list is empty, and also requires the bot to have `can_invite_users` in the target chat.
- The `/editchatinvitelink` command changes an existing non-primary invite link for a target chat, so it requires `TELEGRAM_ADMIN_CHAT_IDS`, is unavailable when that list is empty, and also requires the bot to have `can_invite_users` in the target chat.
- The `/revokechatinvitelink` command revokes an invite link created by the bot for a target chat, so it requires `TELEGRAM_ADMIN_CHAT_IDS`, is unavailable when that list is empty, and also requires the bot to have `can_invite_users` in the target chat.
- The `/createchatsubscriptioninvitelink` command creates and exposes a paid subscription invite link for a target chat, so it requires `TELEGRAM_ADMIN_CHAT_IDS`, is unavailable when that list is empty, and also requires the bot to have `can_invite_users` in the target chat.
- The `/editchatsubscriptioninvitelink` command changes an existing subscription invite link for a target chat, so it requires `TELEGRAM_ADMIN_CHAT_IDS`, is unavailable when that list is empty, and also requires the bot to have `can_invite_users` in the target chat.
- Rate limiting helps prevent abuse.

## Limitations & Future Work

- Storage is in-memory; restarting the bot clears conversation history. For persistence, consider Redis or a database.
- Inline query results are minimal; can be expanded.
- No built-in admin panel or metrics.
- Most Telegram Bot API methods are not yet implemented; see the functionality analysis for the current method matrix.
- The Telegram Bot API implementation guide breaks the missing methods into
  per-method issue drafts with labels, stages, scope, and acceptance criteria.
- The Telegram Bot API issue index links those method drafts to the actual
  GitHub issues created in this repository.
- Official Telegram Guest Mode answers are supported for incoming messages that
  expose `Message.guest_query_id`; broader guest-specific update routing can be
  expanded as aiogram gains typed Bot API 10.0 support.
- Bot-to-Bot communication is not supported.
- The transcription service requires the optional `openai-whisper` package and may be slow for longer audio; consider using a faster service like NVIDIA NIM.

## Claude Code Development

For developers using the Claude Code CLI, see [CLAUDE.md](CLAUDE.md) for setup, commands, and environment details.

Contributions are welcome!

## License

MIT
