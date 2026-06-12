import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
DOCUMENTED_APP_ENVIRONMENT_KEYS = {
    "FREE_CLAUDE_BASE_URL",
    "FREE_CLAUDE_AUTH_TOKEN",
    "FREE_CLAUDE_DEFAULT_MODEL",
    "FREE_CLAUDE_TIMEOUT_SECONDS",
    "FREE_CLAUDE_STREAMING_ENABLED",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_WEBHOOK_URL",
    "TELEGRAM_GUEST_MODE_ENABLED",
    "TELEGRAM_ALLOWED_CHAT_IDS",
    "TELEGRAM_ADMIN_CHAT_IDS",
    "TELEGRAM_CHAT_ACTION_ENABLED",
    "TELEGRAM_MESSAGE_DRAFT_ENABLED",
    "TELEGRAM_MEDIA_DOWNLOAD_MAX_BYTES",
    "TELEGRAM_BOT_NAME",
    "TELEGRAM_BOT_NAME_LANGUAGE_CODE",
    "TELEGRAM_BOT_SHORT_DESCRIPTION",
    "TELEGRAM_BOT_SHORT_DESCRIPTION_LANGUAGE_CODE",
    "TELEGRAM_BOT_DESCRIPTION",
    "TELEGRAM_BOT_DESCRIPTION_LANGUAGE_CODE",
    "TELEGRAM_BOT_DEFAULT_ADMINISTRATOR_RIGHTS",
    "TELEGRAM_BOT_DEFAULT_ADMINISTRATOR_RIGHTS_FOR_CHANNELS",
    "API_SECRET_TOKEN",
    "RATE_LIMIT_REQUESTS_PER_MINUTE",
    "LOG_LEVEL",
}
OPTIONAL_STARTUP_SYNC_ENVIRONMENT_KEYS = {
    "TELEGRAM_BOT_NAME",
    "TELEGRAM_BOT_NAME_LANGUAGE_CODE",
    "TELEGRAM_BOT_SHORT_DESCRIPTION",
    "TELEGRAM_BOT_SHORT_DESCRIPTION_LANGUAGE_CODE",
    "TELEGRAM_BOT_DESCRIPTION",
    "TELEGRAM_BOT_DESCRIPTION_LANGUAGE_CODE",
    "TELEGRAM_BOT_DEFAULT_ADMINISTRATOR_RIGHTS",
    "TELEGRAM_BOT_DEFAULT_ADMINISTRATOR_RIGHTS_FOR_CHANNELS",
}
ENV_DECLARATION_RE = re.compile(r"^\s*#?\s*([A-Z][A-Z0-9_]*)=")
ACTIVE_ENV_DECLARATION_RE = re.compile(r"^\s*([A-Z][A-Z0-9_]*)=")


def _read_text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _dockerignore_patterns() -> set[str]:
    return {
        line.strip()
        for line in _read_text(".dockerignore").splitlines()
        if line.strip() and not line.strip().startswith("#")
    }


def _compose_environment_entries(path: str, service_name: str) -> dict[str, str | None]:
    compose = yaml.safe_load(_read_text(path))
    environment = compose["services"][service_name]["environment"]
    if isinstance(environment, dict):
        return environment

    entries = {}
    for entry in environment:
        key, separator, value = entry.partition("=")
        entries[key] = value if separator else None
    return entries


def _compose_environment_keys(path: str, service_name: str) -> set[str]:
    return set(_compose_environment_entries(path, service_name))


def _env_example_keys() -> set[str]:
    return {
        match.group(1)
        for line in _read_text(".env.example").splitlines()
        if (match := ENV_DECLARATION_RE.match(line))
    }


def _active_env_example_keys() -> set[str]:
    return {
        match.group(1)
        for line in _read_text(".env.example").splitlines()
        if (match := ACTIVE_ENV_DECLARATION_RE.match(line))
    }


def test_dockerfile_runs_as_non_root_with_healthcheck_and_pinned_base_image():
    dockerfile = _read_text("Dockerfile")

    assert dockerfile.startswith("FROM python:3.11-slim@sha256:")
    assert re.search(
        r"^RUN addgroup --system app && adduser --system --ingroup app app$",
        dockerfile,
        re.M,
    )
    assert re.search(r"^COPY --chown=app:app \. \.$", dockerfile, re.M)
    assert re.search(r"^USER app$", dockerfile, re.M)
    assert "HEALTHCHECK" in dockerfile
    assert "http://127.0.0.1:8000/health" in dockerfile


def test_dockerignore_excludes_vcs_tests_docs_and_local_secrets():
    patterns = _dockerignore_patterns()

    assert ".git" in patterns
    assert "tests/" in patterns
    assert "docs/" in patterns
    assert ".env" in patterns
    assert ".env.local" in patterns
    assert ".env.*.local" in patterns


def test_compose_avoids_latest_proxy_image_and_sets_resource_limits():
    compose = _read_text("docker-compose.yml")

    assert "ghcr.io/labtgbot/free-claude-code:latest" not in compose
    assert "${FREE_CLAUDE_CODE_IMAGE:?" in compose
    assert compose.count("resources:") == 2
    assert compose.count("limits:") == 2
    assert compose.count("cpus:") >= 2
    assert compose.count("memory:") >= 2


def test_env_example_documents_all_app_runtime_settings():
    assert DOCUMENTED_APP_ENVIRONMENT_KEYS <= _env_example_keys()


def test_compose_passes_documented_app_runtime_settings():
    assert DOCUMENTED_APP_ENVIRONMENT_KEYS <= _compose_environment_keys(
        "docker-compose.yml",
        "telegram-bot-agent",
    )


def test_startup_sync_settings_are_opt_in_for_compose_deployments():
    assert OPTIONAL_STARTUP_SYNC_ENVIRONMENT_KEYS.isdisjoint(_active_env_example_keys())

    environment = _compose_environment_entries("docker-compose.yml", "telegram-bot-agent")
    for key in OPTIONAL_STARTUP_SYNC_ENVIRONMENT_KEYS:
        assert environment[key] is None
