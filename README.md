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
- `/copy` – Copy a message from another chat into this chat without a link to the original sender (admin only).
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
is the job of `forwardMessages`, which is tracked separately.

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
job of `copyMessages`, which is tracked separately.

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
│   │   ├── commands.py         # /start, /help, /model, /settings, /webhook, /logout, /close, /forward, /copy, /clear
│   │   ├── chat.py             # Text and media message handler
│   │   └── inline.py           # Inline query handler
│   ├── services/
│   │   ├── claude_proxy.py     # Client for free-claude-code API
│   │   ├── webhook_info.py     # Telegram webhook diagnostics formatting
│   │   ├── log_out.py          # Telegram logOut lifecycle helper
│   │   ├── close.py            # Telegram close lifecycle helper
│   │   ├── forward_message.py  # Telegram forwardMessage relay helper
│   │   └── copy_message.py     # Telegram copyMessage relay helper
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
- The `/copy` command relays a message from another chat into the admin chat without a link to the original sender, so it requires `TELEGRAM_ADMIN_CHAT_IDS` and protects the copied message from re-forwarding by default.
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
