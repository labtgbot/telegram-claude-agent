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
- `/model` – Show current model and list available models. Use `/model <model_id>` to switch.
- `/settings` – Display your current settings.
- `/webhook` – Show webhook diagnostics for allowed admin chats.
- `/deletewebhook [drop_pending_updates=true|false]` – Delete the webhook for
  allowed admin chats; pending updates are kept by default.
- `/logout` – Log the bot out of the cloud Bot API server (admin only, requires confirmation).
- `/close` – Close the bot instance on the current Bot API server (admin only, requires confirmation).
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
- `/voice` – Send a voice message into this chat as a playable audio clip (shown as a waveform) via a URL or file_id (admin only).
- `/paidmedia` – Send a paid photo into this chat that users must pay for with Telegram Stars to access, via a URL or file_id (admin only).
- `/location` – Send a point on the map into this chat as a real Telegram location via latitude and longitude (admin only).
- `/venue` – Send a venue (a named place with a title and an address pinned on the map) into this chat via latitude and longitude (admin only).
- `/poll` – Send a native poll (an interactive question with 2-10 tappable answer options) into this chat (admin only).
- `/contact` – Send a phone contact (a name with a phone number that can be saved to the address book) into this chat (admin only).
- `/dice` – Send an animated dice (an emoji that shows a random value) into this chat (admin only).
- `/chataction` – Show a chat action (a transient status such as `typing…`) in this chat (admin only).
- `/messagedraft` – Stream an ephemeral message draft (a ~30-second preview shown above the input field) into this private chat (admin only).
- `/checklist` – Send a checklist (a titled list of 1-30 tasks) into this chat on behalf of a connected business account (admin only).
- `/mediagroup` – Send 2-10 media items into this chat as a single album (media group) via URLs or file_ids (admin only).
- `/banchatmember <chat_id> <user_id> [until_date_unix] [revoke=true|false]` – Ban a user from a group, supergroup, or channel where the bot has `can_restrict_members` (admin only).
- `/banchatsenderchat <chat_id> <sender_chat_id>` – Ban a channel chat from sending messages as itself into a supergroup or channel where the bot has `can_restrict_members` (admin only).
- `/unbanchatmember <chat_id> <user_id> [only_if_banned=true|false]` – Unban a user from a group, supergroup, or channel where the bot has `can_restrict_members` (admin only).
- `/restrictchatmember <chat_id> <user_id> <mute|readonly|unrestrict> [until_date_unix] [independent=true|false]` – Restrict or restore a group/supergroup member where the bot has `can_restrict_members` (admin only).
- `/setchatpermissions <chat_id> <closed|text|media|open> [independent=true|false]` – Set default group/supergroup member permissions where the bot has `can_restrict_members` (admin only).
- `/pinchatmessage <chat_id> <message_id> [silent|loud]` – Pin a message where the bot has `can_pin_messages` in groups/supergroups or `can_edit_messages` in channels (admin only).
- `/unpinchatmessage <chat_id> [message_id]` – Unpin a specific or most recent pinned message where the bot has `can_pin_messages` in groups/supergroups or `can_edit_messages` in channels (admin only).
- `/unpinallchatmessages <chat_id>` – Unpin all pinned messages where the bot has `can_pin_messages` in groups/supergroups or `can_edit_messages` in channels (admin only).
- `/setchatphoto <chat_id> <photo_path>` – Set a new group/supergroup photo from a local file where the bot can change chat information (admin only).
- `/deletechatphoto <chat_id>` – Delete the current group/supergroup photo where the bot can change chat information (admin only).
- `/setchatdescription <chat_id> [description]` – Set or clear a group,
  supergroup, or channel description where the bot can change chat information
  (admin only).
- `/promotechatmember <chat_id> <user_id> <moderator|manager|demote>` – Promote or demote a group, supergroup, or channel member where the bot has `can_promote_members` (admin only).
- `/approvechatjoinrequest <chat_id> <user_id>` – Approve a pending join request where the bot has `can_invite_users` (admin only).
- `/declinechatjoinrequest <chat_id> <user_id>` – Decline a pending join request where the bot has `can_invite_users` (admin only).
- `/exportchatinvitelink <chat_id>` – Export a new primary invite link for a group, supergroup, or channel where the bot has `can_invite_users` (admin only).
- `/leavechat <chat_id> confirm` – Make the bot leave a group, supergroup, or channel (admin only, requires confirmation).
- `/createchatinvitelink <chat_id> [name=<text>] [expire_date=<unix_time>] [member_limit=<1-99999>] [creates_join_request=true|false]` – Create an additional invite link where the bot has `can_invite_users` (admin only).
- `/editchatinvitelink <chat_id> <invite_link> [name=<text>] [expire_date=<unix_time>] [member_limit=<1-99999>] [creates_join_request=true|false]` – Edit an existing non-primary invite link where the bot has `can_invite_users` (admin only).
- `/revokechatinvitelink <chat_id> <invite_link>` – Revoke an invite link created by the bot where the bot has `can_invite_users` (admin only).
- `/createchatsubscriptioninvitelink <chat_id> <subscription_price> [name=<text>] [subscription_period=2592000]` – Create a paid subscription invite link where the bot has `can_invite_users` (admin only).
- `/editchatsubscriptioninvitelink <chat_id> <invite_link> [name=<text>]` – Edit an existing subscription invite link where the bot has `can_invite_users` (admin only).
- `/clear` – Clear your conversation history.

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
│   │   ├── commands.py         # /start, /help, /model, /settings, /webhook, /deletewebhook, /logout, /close, /forward, /forwards, /copy, /copies, /photo, /audio, /livephoto, /document, /video, /videonote, /animation, /voice, /paidmedia, /location, /venue, /poll, /contact, /dice, /chataction, /messagedraft, /checklist, /mediagroup, /clear
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
- Official Telegram Guest Mode (`guest_message`/`answerGuestQuery`) is not yet implemented.
- Bot-to-Bot communication is not supported.
- The transcription service requires the optional `openai-whisper` package and may be slow for longer audio; consider using a faster service like NVIDIA NIM.

## Claude Code Development

For developers using the Claude Code CLI, see [CLAUDE.md](CLAUDE.md) for setup, commands, and environment details.

Contributions are welcome!

## License

MIT
