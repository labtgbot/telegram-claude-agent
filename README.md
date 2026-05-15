# Telegram Claude Agent

A professional Telegram bot agent that integrates with [free-claude-code](https://github.com/labtgbot/free-claude-code), providing access to Claude Code capabilities via the Telegram Bot API.

## Features

- Connect to a locally or remotely deployed free-claude-code instance
- Support for streaming responses with real-time updates
- Guest Mode for temporary interactions in group chats without adding the bot
- Handle media: images, documents (PDF, TXT, DOCX), voice messages (with Whisper transcription)
- Core commands: /start, /help, /model, /settings, /clear
- Built-in rate limiting and security (webhook secret token)
- Structured logging with structlog
- Optional Redis caching (not implemented, but architecture ready)
- Easy deployment with Docker and docker-compose

## Tech Stack

- **Bot framework**: aiogram 3.x (asynchronous, supports Telegram Bot API 10.0)
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
git clone https://github.com/your-org/telegram-claude-agent.git
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
- `TELEGRAM_GUEST_MODE_ENABLED` – enable guest mode restrictions in group chats (`true`/`false`).
- `TELEGRAM_ALLOWED_CHAT_IDS` – optional comma-separated list of chat IDs to restrict operation.
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
- `/clear` – Clear your conversation history.

### Guest Mode

When the bot is mentioned in a group chat (e.g., `@YourBot hello`), it automatically activates Guest Mode. In this mode:
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
│   │   ├── commands.py         # /start, /help, /model, /settings, /clear
│   │   ├── chat.py             # Text and media message handler
│   │   └── inline.py           # Inline query handler
│   ├── services/
│   │   └── claude_proxy.py     # Client for free-claude-code API
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
- Rate limiting helps prevent abuse.

## Limitations & Future Work

- Storage is in-memory; restarting the bot clears conversation history. For persistence, consider Redis or a database.
- Inline query results are minimal; can be expanded.
- No built-in admin panel or metrics.
- Advanced Telegram Bot API 10.0 features (Polls 2.0, Message Effects, Custom AI Styles, Scheduled Messages) are not yet implemented.
- Bot-to-Bot communication is not supported.
- The transcription service requires the optional `openai-whisper` package and may be slow for longer audio; consider using a faster service like NVIDIA NIM.

Contributions are welcome!

## License

MIT