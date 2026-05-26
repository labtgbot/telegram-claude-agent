from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import List, Optional


def _parse_id_list(raw: str) -> List[int]:
    raw = raw.strip()
    if not raw:
        return []
    return [int(x.strip()) for x in raw.split(',') if x.strip()]

class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", case_sensitive=False)

    free_claude_base_url: str
    free_claude_auth_token: str
    free_claude_default_model: str
    free_claude_timeout_seconds: int = 120
    free_claude_streaming_enabled: bool = True

    telegram_bot_token: str
    telegram_webhook_url: Optional[str] = None
    telegram_guest_mode_enabled: bool = True
    telegram_allowed_chat_ids: str = ""
    telegram_admin_chat_ids: str = ""
    telegram_chat_action_enabled: bool = True

    api_secret_token: Optional[str] = None
    rate_limit_requests_per_minute: int = 60

    log_level: str = "INFO"

    @property
    def allowed_chat_ids(self) -> List[int]:
        return _parse_id_list(self.telegram_allowed_chat_ids)

    @property
    def admin_chat_ids(self) -> List[int]:
        return _parse_id_list(self.telegram_admin_chat_ids)

# Global settings instance
settings = Settings()
