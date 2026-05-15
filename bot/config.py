from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List, Optional

class Settings(BaseSettings):
    free_claude_base_url: str
    free_claude_auth_token: str
    free_claude_default_model: str
    free_claude_timeout_seconds: int = 120
    free_claude_streaming_enabled: bool = True

    telegram_bot_token: str
    telegram_webhook_url: Optional[str] = None
    telegram_guest_mode_enabled: bool = True
    telegram_allowed_chat_ids: List[int] = []

    api_secret_token: Optional[str] = None
    rate_limit_requests_per_minute: int = 60

    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False

    @field_validator('telegram_allowed_chat_ids', mode='before')
    @classmethod
    def parse_chat_ids(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return []
            return [int(x.strip()) for x in v.split(',') if x.strip()]
        return v

# Global settings instance
settings = Settings()