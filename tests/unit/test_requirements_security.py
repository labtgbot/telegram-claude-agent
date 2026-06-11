import re
from pathlib import Path

import pytest


REQUIREMENTS = Path(__file__).resolve().parents[2] / "requirements.txt"
PINNED_VERSION = re.compile(
    r"^[A-Za-z0-9_.-]+(?:\[[A-Za-z0-9_,.-]+\])?==[A-Za-z0-9_.!+*-]+(?:; .+)?$"
)
PINNED_URL = re.compile(
    r"^[A-Za-z0-9_.-]+ @ "
    r"https://github\.com/aiogram/aiogram/archive/[0-9a-f]{40}\.tar\.gz"
    r"#sha256=[0-9a-f]{64}$"
)


def _active_requirements() -> list[str]:
    return [
        line.strip()
        for line in REQUIREMENTS.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def _requirement_name(line: str) -> str:
    if " @ " in line:
        name = line.split(" @ ", 1)[0]
    else:
        name = line.split("==", 1)[0]
    return name.split("[", 1)[0].lower().replace("_", "-")


def _requirements_by_name() -> dict[str, str]:
    return {_requirement_name(line): line for line in _active_requirements()}


def _version_tuple(requirement: str) -> tuple[int, ...]:
    version = requirement.split("==", 1)[1].split(";", 1)[0]
    return tuple(int(part) for part in version.split(".") if part.isdigit())


@pytest.mark.parametrize("requirement", _active_requirements())
def test_active_requirements_are_pinned(requirement: str):
    assert PINNED_VERSION.match(requirement) or PINNED_URL.match(requirement)


def test_known_vulnerable_dependencies_are_not_reintroduced():
    requirements = _requirements_by_name()

    assert "pypdf2" not in requirements
    assert "pypdf" in requirements
    assert _version_tuple(requirements["python-multipart"]) >= (0, 0, 32)
    assert _version_tuple(requirements["aiohttp"]) >= (3, 14, 0)
    assert _version_tuple(requirements["fastapi"]) >= (0, 109, 1)
    assert _version_tuple(requirements["pillow"]) >= (12, 2, 0)
