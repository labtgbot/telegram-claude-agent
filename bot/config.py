import re
from pathlib import Path
from typing import List, Optional

from pydantic import AnyHttpUrl, TypeAdapter, ValidationError, ValidationInfo
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Telegram's allowed alphabet for the webhook secret token: 1-256 characters
# from A-Z, a-z, 0-9, underscore and hyphen.
# https://core.telegram.org/bots/api#setwebhook
_SECRET_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{1,256}$")
# Minimum length we recommend (and enforce) for a usable secret token.
_SECRET_TOKEN_MIN_LENGTH = 16
DEFAULT_TELEGRAM_MEDIA_DOWNLOAD_MAX_BYTES = 8 * 1024 * 1024
_HTTP_URL_ADAPTER = TypeAdapter(AnyHttpUrl)
_ID_LIST_ENV_NAMES = {
    "telegram_allowed_chat_ids": "TELEGRAM_ALLOWED_CHAT_IDS",
    "telegram_admin_chat_ids": "TELEGRAM_ADMIN_CHAT_IDS",
    "telegram_admin_user_ids": "TELEGRAM_ADMIN_USER_IDS",
}
LOG_LEVEL_NAMES = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
_LOG_LEVEL_NAME_SET = set(LOG_LEVEL_NAMES)
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def _parse_id_list(raw: str, source_name: str = "chat id list") -> List[int]:
    raw = raw.strip()
    if not raw:
        return []

    ids = []
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        try:
            ids.append(int(token))
        except ValueError as exc:
            raise ValueError(
                f"{source_name} must be a comma-separated list of integer IDs; "
                f"invalid token: {token!r}."
            ) from exc
    return ids


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILE, case_sensitive=False)

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
    telegram_admin_user_ids: str = ""
    telegram_chat_action_enabled: bool = True
    telegram_message_draft_enabled: bool = False
    telegram_media_download_max_bytes: int = DEFAULT_TELEGRAM_MEDIA_DOWNLOAD_MAX_BYTES
    telegram_bot_name: Optional[str] = None
    telegram_bot_name_language_code: Optional[str] = None
    telegram_bot_short_description: Optional[str] = None
    telegram_bot_short_description_language_code: Optional[str] = None
    telegram_bot_description: Optional[str] = None
    telegram_bot_description_language_code: Optional[str] = None
    telegram_bot_default_administrator_rights: Optional[str] = None
    telegram_bot_default_administrator_rights_for_channels: Optional[bool] = None

    api_secret_token: Optional[str] = None
    rate_limit_requests_per_minute: int = 60

    log_level: str = "INFO"

    @field_validator("free_claude_base_url")
    @classmethod
    def _validate_free_claude_base_url(cls, value: str) -> str:
        try:
            _HTTP_URL_ADAPTER.validate_python(value)
        except ValidationError as exc:
            raise ValueError(
                "FREE_CLAUDE_BASE_URL must be an http(s) URL with a host."
            ) from exc
        return value

    @field_validator("telegram_webhook_url")
    @classmethod
    def _validate_telegram_webhook_url(cls, value: Optional[str]) -> Optional[str]:
        if value is None or value == "":
            return value
        try:
            _HTTP_URL_ADAPTER.validate_python(value)
        except ValidationError as exc:
            raise ValueError(
                "TELEGRAM_WEBHOOK_URL must be an http(s) URL with a host."
            ) from exc
        return value

    @field_validator(
        "telegram_allowed_chat_ids",
        "telegram_admin_chat_ids",
        "telegram_admin_user_ids",
    )
    @classmethod
    def _validate_chat_id_list(cls, value: str, info: ValidationInfo) -> str:
        source_name = _ID_LIST_ENV_NAMES.get(info.field_name or "", "ID list")
        _parse_id_list(value, source_name)
        return value

    @field_validator("api_secret_token")
    @classmethod
    def _validate_api_secret_token(cls, value: Optional[str]) -> Optional[str]:
        # Allow the token to stay unset (polling deployments do not need it),
        # but if it is provided it must satisfy Telegram's constraints so that
        # ``set_webhook`` does not silently reject it.
        if value is None or value == "":
            return value
        if not _SECRET_TOKEN_RE.match(value):
            raise ValueError(
                "API_SECRET_TOKEN must be 1-256 characters long and contain "
                "only A-Z, a-z, 0-9, underscore (_) and hyphen (-)."
            )
        if len(value) < _SECRET_TOKEN_MIN_LENGTH:
            raise ValueError(
                "API_SECRET_TOKEN must be at least "
                f"{_SECRET_TOKEN_MIN_LENGTH} characters long for security."
            )
        return value

    @field_validator("telegram_media_download_max_bytes")
    @classmethod
    def _validate_telegram_media_download_max_bytes(cls, value: int) -> int:
        if value < 1:
            raise ValueError("TELEGRAM_MEDIA_DOWNLOAD_MAX_BYTES must be at least 1 byte.")
        return value

    @field_validator("rate_limit_requests_per_minute")
    @classmethod
    def _validate_rate_limit_requests_per_minute(cls, value: int) -> int:
        if value < 1:
            raise ValueError(
                "RATE_LIMIT_REQUESTS_PER_MINUTE must be a positive integer greater than 0."
            )
        return value

    @field_validator("log_level", mode="before")
    @classmethod
    def _validate_log_level(cls, value: str) -> str:
        normalized = str(value).strip().upper()
        if normalized not in _LOG_LEVEL_NAME_SET:
            allowed = ", ".join(LOG_LEVEL_NAMES)
            raise ValueError(f"LOG_LEVEL must be one of: {allowed}.")
        return normalized

    @model_validator(mode="after")
    def _require_secret_token_in_webhook_mode(self) -> "Settings":
        # Fail fast: a configured webhook URL turns ``/webhook`` into a public
        # endpoint, so a secret token is mandatory to authenticate Telegram.
        if self.telegram_webhook_url and not self.api_secret_token:
            raise ValueError(
                "API_SECRET_TOKEN is required when TELEGRAM_WEBHOOK_URL is set: "
                "the webhook endpoint must verify Telegram's secret token to "
                "reject forged updates. Set a strong random API_SECRET_TOKEN "
                f"(at least {_SECRET_TOKEN_MIN_LENGTH} characters)."
            )
        return self

    @property
    def allowed_chat_ids(self) -> List[int]:
        return _parse_id_list(self.telegram_allowed_chat_ids, "TELEGRAM_ALLOWED_CHAT_IDS")

    @property
    def admin_chat_ids(self) -> List[int]:
        return _parse_id_list(self.telegram_admin_chat_ids, "TELEGRAM_ADMIN_CHAT_IDS")

    @property
    def admin_user_ids(self) -> List[int]:
        return _parse_id_list(self.telegram_admin_user_ids, "TELEGRAM_ADMIN_USER_IDS")

# Global settings instance
settings = Settings()
