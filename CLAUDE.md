# CLAUDE.md

This file provides project-specific guidance for Claude Code when working with the telegram-claude-agent repository.

## Project Overview

Telegram Claude Agent is a professional Telegram bot that integrates with free-claude-code, providing access to Claude Code capabilities via the Telegram Bot API.

### Key Features
- Streaming responses with real-time updates
- Guest Mode for group chats
- Media support: images, PDFs, TXT, DOCX, voice messages
- Rate limiting and security features
- Docker deployment ready

## Repository Structure

```
telegram-claude-agent/
├── bot/
│   ├── main.py            # FastAPI app + aiogram dispatcher
│   ├── config.py          # Pydantic settings
│   ├── handlers/          # Command and message handlers
│   ├── middlewares/       # Logging, rate limiting
│   ├── services/          # Claude proxy client
│   └── utils/             # Storage, media processing
├── tests/
│   ├── unit/
│   └── integration/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## Quick Start

### Prerequisites
- Python 3.11+
- Telegram bot token (from @BotFather)
- Running free-claude-code instance (default: http://localhost:8082)

### Setup
```bash
# Clone and install
git clone https://github.com/labtgbot/telegram-claude-agent.git
cd telegram-claude-agent
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Configuration
Copy `.env.example` to `.env` and fill in the required values. At minimum:

```env
FREE_CLAUDE_BASE_URL=http://localhost:8082
FREE_CLAUDE_AUTH_TOKEN=your_proxy_auth_token
TELEGRAM_BOT_TOKEN=your_bot_token
API_SECRET_TOKEN=random_secret
```

### Running

Development (with auto-reload):
```bash
uvicorn bot.main:app --reload --port 8000
```

Production with Docker:
```bash
docker-compose up -d
```

## Development Commands

### Testing
```bash
# Unit tests
pytest tests/unit

# Integration tests (requires running bot and proxy)
pytest tests/integration
```

### Linting/Formatting
No formal linting setup yet. Consider adding Ruff or Black for consistency.

## Environment Variables Reference

| Variable                              | Description                                      | Required |
|----------------------------------------|--------------------------------------------------|----------|
| `FREE_CLAUDE_BASE_URL`                 | free-claude-code proxy URL                      | Yes      |
| `FREE_CLAUDE_AUTH_TOKEN`               | Authentication for proxy                        | Yes      |
| `FREE_CLAUDE_DEFAULT_MODEL`            | Default model ID                                | No       |
| `FREE_CLAUDE_TIMEOUT_SECONDS`          | HTTP timeout (default 120)                      | No       |
| `FREE_CLAUDE_STREAMING_ENABLED`        | Enable streaming (true/false)                   | No       |
| `TELEGRAM_BOT_TOKEN`                   | Telegram bot token                              | Yes      |
| `TELEGRAM_WEBHOOK_URL`                 | Public HTTPS URL for webhook mode               | No       |
| `TELEGRAM_GUEST_MODE_ENABLED`          | Enable guest mode in groups (true/false)       | No       |
| `TELEGRAM_ALLOWED_CHAT_IDS`            | Comma-separated whitelist of chat IDs           | No       |
| `TELEGRAM_ADMIN_CHAT_IDS`              | Comma-separated admin chat IDs for /webhook, /logout, /close, /forward, /forwards, /copy, /copies, /photo, /audio & /livephoto | No |
| `API_SECRET_TOKEN`                     | Webhook verification secret                     | Yes      |
| `RATE_LIMIT_REQUESTS_PER_MINUTE`       | Rate limit (default 60)                         | No       |
| `LOG_LEVEL`                            | Logging level (default INFO)                    | No       |

## Docker Notes

- **Bot service**: Builds from Dockerfile, exposes port 8000
- **free-claude-code dependency**: Uses ghcr.io/labtgbot/free-claude-code:latest
- The docker-compose setup includes both services for local development

### Useful Docker Commands
```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down

# Rebuild after code changes
docker-compose build --no-cache
docker-compose up -d
```

## Testing Strategy

- **Unit tests**: Located in `tests/unit/`, cover config, storage, and proxy client logic
- **Integration tests**: In `tests/integration/`, require both bot and proxy running
- Run with `pytest` or `pytest -v` for verbosity

## Known Issues & Gotchas

1. **In-memory storage**: Conversation history is lost on restart. For persistence, Redis or database integration is needed.
2. **Voice transcription**: Requires `openai-whisper` (optional) and may need ffmpeg. Can be slow for longer audio.
3. **Webhook mode**: Requires a publicly accessible HTTPS URL. Use a reverse proxy (nginx, Traefik) in production.
4. **free-claude-code**: Ensure the proxy instance is running before starting the bot. The default port is 8082.

## Claude Code Specific Notes

When working on this project, you may want to:

- **Test handlers**: Mock aiogram and httpx objects. See existing unit tests for patterns.
- **Add features**: Follow existing module structure. Place new handlers in `bot/handlers/`, services in `bot/services/`.
- **Modify API calls**: The `ClaudeProxyClient` in `bot/services/claude_proxy.py` is the sole interface to free-claude-code.
- **Configuration changes**: Update `bot/config.py` (Settings class) if adding new environment variables.

## Resources

- [free-claude-code](https://github.com/labtgbot/free-claude-code) - The proxy server this bot integrates with
- [aiogram documentation](https://docs.aiogram.dev/) - Async Telegram bot framework
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [Anthropic Messages API](https://docs.anthropic.com/en/api/messages) - API format compatibility reference

---

Last updated: 2025-05-15
