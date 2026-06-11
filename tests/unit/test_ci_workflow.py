from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"


def _load_workflow() -> dict:
    assert WORKFLOW.exists(), "CI workflow must exist at .github/workflows/ci.yml"
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def _job_commands(workflow: dict, job_name: str) -> str:
    job = workflow["jobs"][job_name]
    return "\n".join(str(step.get("run", "")) for step in job["steps"])


def test_ci_workflow_runs_on_pull_requests_and_main_pushes():
    workflow = _load_workflow()

    triggers = workflow["on"]
    assert "pull_request" in triggers
    assert triggers["push"]["branches"] == ["main"]


def test_ci_workflow_runs_lint_tests_security_and_docker_build():
    workflow = _load_workflow()

    assert set(workflow["jobs"]) == {"lint", "test", "security", "docker-build"}

    assert "ruff check ." in _job_commands(workflow, "lint")

    test_commands = _job_commands(workflow, "test")
    assert "pytest" in test_commands
    assert "--cov=bot" in test_commands

    security_commands = _job_commands(workflow, "security")
    assert "pip-audit" in security_commands
    assert "--requirement requirements.txt" in security_commands

    docker_commands = _job_commands(workflow, "docker-build")
    assert "docker build" in docker_commands
