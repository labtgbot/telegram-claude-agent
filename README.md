# Telegram Claude Agent

**Repository:** https://github.com/labtgbot/telegram-claude-agent

A professional Telegram bot agent that integrates with [free-claude-code](https://github.com/labtgbot/free-claude-code), providing access to Claude Code capabilities via the Telegram Bot API.

## Features

- Connect to a locally or remotely deployed free-claude-code instance
- Support for streaming responses with real-time updates
- Group privacy mode for mention/reply interactions without shared history
- Handle media: images, documents (PDF, TXT, DOCX), voice messages (with Whisper transcription)
- Core commands: /start, /help, /model, /settings, /clear
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
TELEGRAM_ADMIN_CHAT_IDS=  # optional diagnostics command allowlist

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
- `TELEGRAM_ADMIN_CHAT_IDS` – optional comma-separated list of chat IDs allowed to run admin diagnostics commands. If empty, diagnostics fall back to `TELEGRAM_ALLOWED_CHAT_IDS`; if both are empty, diagnostics commands are disabled.
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
- `/clear` – Clear your conversation history.

### Webhook diagnostics

The restricted `/webhook` command calls Telegram Bot API `getWebhookInfo`
through aiogram's typed API. It requires no Telegram method parameters and
shows the current webhook status, webhook URL, pending update count,
`allowed_updates`, certificate flag, connection limit, and the latest delivery
or synchronization error reported by Telegram.

Use `TELEGRAM_ADMIN_CHAT_IDS` to restrict this operational output to private
admin chats or trusted operations groups. If `TELEGRAM_ADMIN_CHAT_IDS` is empty,
the command falls back to `TELEGRAM_ALLOWED_CHAT_IDS`. If both lists are empty,
the diagnostics command is disabled. The global rate-limit middleware still
applies to the command.

When the bot is running in long polling mode, Telegram returns webhook info with
an empty `url`, which the command displays as disabled. This command does not
change webhook state; rollback is simply removing the command allowlist or
stopping use of `/webhook`.

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
│   │   ├── commands.py         # /start, /help, /model, /settings, /webhook, /logout, /close, /forward, /forwards, /copy, /copies, /photo, /audio, /livephoto, /document, /video, /videonote, /animation, /voice, /paidmedia, /location, /clear
│   │   ├── chat.py             # Text and media message handler
│   │   └── inline.py           # Inline query handler
│   ├── services/
│   │   ├── claude_proxy.py     # Client for free-claude-code API
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
│   │   └── send_location.py    # Telegram sendLocation outbound helper
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
- The `/webhook` diagnostics command can expose webhook URL and delivery errors, so restrict it with `TELEGRAM_ADMIN_CHAT_IDS`.
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
