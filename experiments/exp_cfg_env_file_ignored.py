"""
EXPERIMENT: Does `model_config = ConfigDict(env_file=".env", ...)` actually make
pydantic-settings read a `.env` file?

Hypothesis: bot/config.py uses `ConfigDict` (from pydantic) instead of
`SettingsConfigDict` (from pydantic_settings). `ConfigDict` is a plain TypedDict
for pydantic's *model* config; pydantic-settings only recognises the
`env_file` / `env_prefix` / etc. keys when they live in a `SettingsConfigDict`
(it reads `model_config` keys like `env_file` through its own settings config).

If the hypothesis holds, a value present ONLY in `.env` (and absent from the
process environment) will NOT be picked up -> required fields raise
ValidationError, and overrides in `.env` are silently ignored.

We compare the project's Settings (ConfigDict) against an identical class that
uses SettingsConfigDict, in an isolated temp directory containing a `.env`.
"""
import os
import sys
import tempfile
from pathlib import Path

from pydantic import ConfigDict
from pydantic_settings import BaseSettings, SettingsConfigDict


ENV_CONTENTS = (
    "FREE_CLAUDE_BASE_URL=http://from-dotenv.example\n"
    "FREE_CLAUDE_AUTH_TOKEN=dotenv_auth\n"
    "FREE_CLAUDE_DEFAULT_MODEL=dotenv_model\n"
    "TELEGRAM_BOT_TOKEN=123456:DOTENVtoken_abcdefghijklmnopqrstuvwx\n"
    "RATE_LIMIT_REQUESTS_PER_MINUTE=999\n"
)

REQUIRED = (
    "free_claude_base_url",
    "free_claude_auth_token",
    "free_claude_default_model",
    "telegram_bot_token",
)


class SettingsConfigDictVariant(BaseSettings):
    """Correct variant: uses SettingsConfigDict."""
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    free_claude_base_url: str
    free_claude_auth_token: str
    free_claude_default_model: str
    telegram_bot_token: str
    rate_limit_requests_per_minute: int = 60


class ConfigDictVariant(BaseSettings):
    """Project variant: uses ConfigDict (same as bot/config.py)."""
    model_config = ConfigDict(env_file=".env", case_sensitive=False)

    free_claude_base_url: str
    free_claude_auth_token: str
    free_claude_default_model: str
    telegram_bot_token: str
    rate_limit_requests_per_minute: int = 60


def _clear_required_env():
    for name in (
        "FREE_CLAUDE_BASE_URL",
        "FREE_CLAUDE_AUTH_TOKEN",
        "FREE_CLAUDE_DEFAULT_MODEL",
        "TELEGRAM_BOT_TOKEN",
        "RATE_LIMIT_REQUESTS_PER_MINUTE",
    ):
        os.environ.pop(name, None)


def main():
    tmp = Path(tempfile.mkdtemp(prefix="exp_cfg_"))
    (tmp / ".env").write_text(ENV_CONTENTS)
    os.chdir(tmp)  # so the relative ".env" path resolves here
    _clear_required_env()

    print(f"[setup] cwd={os.getcwd()}")
    print(f"[setup] .env exists={ (tmp / '.env').exists() }")
    print("[setup] FREE_CLAUDE_* / TELEGRAM_BOT_TOKEN are NOT in process env\n")

    # --- Correct variant -------------------------------------------------
    print("=== SettingsConfigDict variant (the CORRECT API) ===")
    try:
        s = SettingsConfigDictVariant()
        print("  instantiated OK")
        print(f"  free_claude_base_url = {s.free_claude_base_url!r}")
        print(f"  rate_limit_requests_per_minute = {s.rate_limit_requests_per_minute!r}")
        correct_reads_env = s.free_claude_base_url == "http://from-dotenv.example"
    except Exception as exc:
        print(f"  RAISED {type(exc).__name__}: {str(exc).splitlines()[0]}")
        correct_reads_env = False

    print()

    # --- Project variant -------------------------------------------------
    print("=== ConfigDict variant (what bot/config.py uses) ===")
    project_reads_env = False
    try:
        s = ConfigDictVariant()
        print("  instantiated OK")
        print(f"  free_claude_base_url = {s.free_claude_base_url!r}")
        print(f"  rate_limit_requests_per_minute = {s.rate_limit_requests_per_minute!r}")
        project_reads_env = s.free_claude_base_url == "http://from-dotenv.example"
    except Exception as exc:
        first = str(exc).splitlines()[0]
        print(f"  RAISED {type(exc).__name__}: {first}")
        # Count how many required fields are reported missing
        missing = [f for f in REQUIRED if f in str(exc)]
        print(f"  -> required fields still missing despite .env present: {missing}")

    print()

    # --- Inspect what pydantic-settings sees as its config ---------------
    print("=== model_config introspection ===")
    print(f"  ConfigDictVariant.model_config         = {dict(ConfigDictVariant.model_config)}")
    # pydantic-settings stores its effective settings config separately:
    scd_cfg = getattr(ConfigDictVariant, "model_config", {})
    print(f"  -> 'env_file' key present in dict       = {'env_file' in scd_cfg}")
    # The settings sources read env_file from the *settings* config; show the resolved value
    try:
        from pydantic_settings.sources import DotEnvSettingsSource
        src = DotEnvSettingsSource(ConfigDictVariant)
        print(f"  DotEnvSettingsSource.env_file (ConfigDict)        = {src.env_file!r}")
        src2 = DotEnvSettingsSource(SettingsConfigDictVariant)
        print(f"  DotEnvSettingsSource.env_file (SettingsConfigDict)= {src2.env_file!r}")
    except Exception as exc:
        print(f"  (introspection of DotEnvSettingsSource failed: {exc})")

    print()
    print("=== VERDICT ===")
    print(f"  SettingsConfigDict reads .env : {correct_reads_env}")
    print(f"  ConfigDict (project) reads .env: {project_reads_env}")
    if correct_reads_env and not project_reads_env:
        print("  CONFIRMED BUG: ConfigDict does NOT read .env; SettingsConfigDict does.")
        return 0
    print("  Hypothesis NOT confirmed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
