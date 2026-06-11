import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _read_text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _dockerignore_patterns() -> set[str]:
    return {
        line.strip()
        for line in _read_text(".dockerignore").splitlines()
        if line.strip() and not line.strip().startswith("#")
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
