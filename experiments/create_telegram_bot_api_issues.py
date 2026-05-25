#!/usr/bin/env python3
"""Create GitHub issues from the Telegram Bot API implementation guide."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


GUIDE_PATH = Path("docs/telegram-bot-api-implementation-guide.md")
REPORT_PATH = Path("docs/telegram-bot-api-issue-index.md")

STAGE_DESCRIPTIONS = {
    "S1-spec": (
        "сверить сигнатуру метода, типы, "
        "ограничения, права бота, required update types "
        "и поддержку в текущем aiogram==3.3.0"
    ),
    "S2-design": (
        "описать пользовательский или "
        "админский сценарий, "
        "настройки, privacy/security impact, rollback "
        "и связь с free-claude-code"
    ),
    "S3-implementation": (
        "добавить handler/service wrapper, структурные логи, "
        "обработку ошибок Telegram и rate-limit/allowlist checks"
    ),
    "S4-tests": (
        "добавить unit tests с моками Telegram Bot API; "
        "integration tests делать opt-in, если нужен "
        "реальный bot token или chat id"
    ),
    "S5-docs": (
        "обновить README, functionality analysis, примеры конфигурации "
        "и operational notes"
    ),
}

LABELS: dict[str, tuple[str, str]] = {
    "telegram-api": ("0E8A16", "Backlog item for Telegram Bot API coverage."),
    "bot-api-10.0": ("1D76DB", "Method exists in Telegram Bot API 10.0 snapshot."),
    "kind:feature": ("A2EEEF", "New feature or capability."),
    "priority:P0": ("B60205", "Foundational method for the next Telegram API layer."),
    "priority:P1": ("D93F0B", "High user impact for the Claude bot."),
    "priority:P2": ("FBCA04", "Important for groups, administration or interactivity."),
    "priority:P3": ("C5DEF5", "Platform expansion or advanced capability."),
    "priority:P4": ("EDEDED", "Domain-specific tail or niche capability."),
    "stage:S1-spec": ("5319E7", "Initial specification and compatibility stage."),
    "area:lifecycle": ("0052CC", "Webhook, polling and operational diagnostics."),
    "area:message-relay": ("006B75", "Forwarding and copying messages."),
    "area:outbound-media": ("C2E0C6", "Rich outbound messages and reactions."),
    "area:user-context": ("BFDADC", "Telegram user context methods."),
    "area:chat-admin": ("D4C5F9", "Groups, permissions, moderation and invite links."),
    "area:forum-topics": ("5319E7", "Forum topic lifecycle and management."),
    "area:interactive": ("FBCA04", "Callbacks, inline flows, Guest Mode and boosts."),
    "area:managed-bots": ("1D76DB", "Business connections and managed bots."),
    "area:bot-profile": ("C5DEF5", "Bot commands, profile and default admin rights."),
    "area:gifts-verification": ("F9D0C4", "Gifts, verification and premium scenarios."),
    "area:business-account": ("D93F0B", "Business account actions, gifts and Stars."),
    "area:stories": ("FEF2C0", "Telegram stories methods."),
    "area:webapp": ("BFD4F2", "Web Apps and prepared messages/buttons."),
    "area:message-management": ("FAD8C7", "Editing, deleting and suggested posts."),
    "area:stickers": ("D4C5F9", "Stickers and custom emoji."),
    "area:payments-stars": ("B60205", "Payments, invoices and Telegram Stars."),
    "area:passport-games": ("E99695", "Telegram Passport and games."),
}


@dataclass(frozen=True)
class MethodIssue:
    botapi_id: str
    method: str
    title: str
    docs_url: str
    labels: tuple[str, ...]
    stages: tuple[str, ...]
    scope: str
    acceptance: tuple[str, ...]


TRANSIENT_ERROR_MARKERS = (
    "secondary rate limit",
    "rate limit",
    "temporarily unavailable",
    "timeout",
    "timed out",
    "502",
    "503",
    "504",
)


def run_gh(args: list[str], *, json_output: bool = True, attempts: int = 1) -> Any:
    for attempt in range(1, attempts + 1):
        result = subprocess.run(
            ["gh", *args],
            text=True,
            capture_output=True,
        )
        if result.returncode == 0:
            break

        combined = f"{result.stdout}\n{result.stderr}".lower()
        transient = any(marker in combined for marker in TRANSIENT_ERROR_MARKERS)
        if attempt >= attempts or not transient:
            command = " ".join(["gh", *args[:4], "..."])
            raise RuntimeError(
                f"{command} failed with exit code {result.returncode}\n"
                f"stdout:\n{result.stdout}\n"
                f"stderr:\n{result.stderr}"
            )

        delay = min(120, 10 * 2 ** (attempt - 1))
        print(
            f"Transient gh error on attempt {attempt}/{attempts}; "
            f"retrying in {delay}s: {result.stderr.strip()}",
            file=sys.stderr,
            flush=True,
        )
        time.sleep(delay)
    else:
        raise RuntimeError("unreachable gh retry state")

    if not json_output:
        return result.stdout
    return json.loads(result.stdout)


def parse_backlog(guide_path: Path) -> list[MethodIssue]:
    text = guide_path.read_text(encoding="utf-8")
    header_re = re.compile(
        r"^#### (?P<id>BOTAPI-\d+): `(?P<method>[^`]+)`\n"
        r"(?P<body>.*?)(?=^#### BOTAPI-\d+: `|^### |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    issues: list[MethodIssue] = []

    for match in header_re.finditer(text):
        body = match.group("body")
        title = required_line(body, "Title").strip("`")
        docs_url = required_line(body, "Official docs")
        labels = tuple(re.findall(r"`([^`]+)`", required_line(body, "Labels")))
        stages = tuple(part.strip(" `") for part in required_line(body, "Stages").split("->"))
        scope = required_line(body, "Scope")
        acceptance = tuple(parse_acceptance(body))
        issues.append(
            MethodIssue(
                botapi_id=match.group("id"),
                method=match.group("method"),
                title=title,
                docs_url=docs_url,
                labels=labels,
                stages=stages,
                scope=scope,
                acceptance=acceptance,
            )
        )

    if len(issues) != 169:
        raise RuntimeError(f"Expected 169 method cards, got {len(issues)}")

    return issues


def required_line(block: str, key: str) -> str:
    pattern = re.compile(rf"^- {re.escape(key)}: (?P<value>.*)$", re.MULTILINE)
    match = pattern.search(block)
    if not match:
        raise RuntimeError(f"Missing {key!r} in card:\n{block[:500]}")
    return match.group("value").strip()


def parse_acceptance(block: str) -> list[str]:
    marker = "- Acceptance criteria:\n"
    if marker not in block:
        raise RuntimeError(f"Missing acceptance criteria in card:\n{block[:500]}")
    acceptance_block = block.split(marker, 1)[1]
    criteria: list[str] = []
    current: list[str] = []
    for line in acceptance_block.splitlines():
        if line.startswith("  - "):
            if current:
                criteria.append(" ".join(current).strip())
            current = [line[4:].strip()]
            continue
        if current and line.startswith("    "):
            current.append(line.strip())
    if current:
        criteria.append(" ".join(current).strip())
    if not criteria:
        raise RuntimeError(f"Empty acceptance criteria in card:\n{block[:500]}")
    return criteria


def fetch_existing_labels(repo: str) -> set[str]:
    labels = run_gh(
        [
            "label",
            "list",
            "--repo",
            repo,
            "--limit",
            "500",
            "--json",
            "name",
        ]
    )
    return {label["name"] for label in labels}


def ensure_labels(repo: str, required_labels: set[str], *, apply: bool) -> list[str]:
    existing = fetch_existing_labels(repo)
    missing = sorted(required_labels - existing)
    unknown = [label for label in missing if label not in LABELS]
    if unknown:
        raise RuntimeError(f"No local label definition for: {', '.join(unknown)}")

    if not apply:
        return missing

    for label in missing:
        color, description = LABELS[label]
        run_gh(
            [
                "label",
                "create",
                label,
                "--repo",
                repo,
                "--color",
                color,
                "--description",
                description,
            ],
            json_output=False,
        )
    return missing


def fetch_existing_issues(repo: str) -> dict[str, dict[str, Any]]:
    issues = run_gh(
        [
            "issue",
            "list",
            "--repo",
            repo,
            "--state",
            "all",
            "--limit",
            "1000",
            "--json",
            "number,title,url,state,labels",
        ]
    )
    return {issue["title"]: issue for issue in issues}


def issue_body(issue: MethodIssue) -> str:
    stages = "\n".join(
        f"- [ ] `{stage}`: {STAGE_DESCRIPTIONS.get(stage, 'выполнить этап')}"
        for stage in issue.stages
    )
    labels = ", ".join(f"`{label}`" for label in issue.labels)
    acceptance = "\n".join(f"- [ ] {item}" for item in issue.acceptance)
    return f"""<!-- telegram-bot-api-method: {issue.method} -->
<!-- telegram-bot-api-id: {issue.botapi_id} -->
<!-- generated-from: docs/telegram-bot-api-implementation-guide.md -->

## Контекст

Метод `{issue.method}` пока не интегрирован в `telegram-claude-agent`.
Нужно довести поддержку этого метода
Telegram Bot API до отдельного проверяемого сценария,
не смешивая его с несвязанными методами.

## Official docs

{issue.docs_url}

## Tags

{labels}

## Scope

{issue.scope}

## Steps

{stages}

## Acceptance criteria

{acceptance}

## Notes

- Реализация должна использовать typed aiogram API
  или изолированный raw Bot API helper, если текущий
  `aiogram==3.3.0` не поддерживает метод.
- Перед внедрением нужно проверить права бота,
  privacy implications, ограничения Telegram
  и required update types.
- После завершения обновить `docs/functionality-analysis.md` и при
  необходимости `README.md`.
- Родительская задача: #5. Планирующий PR: #6.
"""


def create_issue(repo: str, issue: MethodIssue) -> dict[str, Any]:
    args = [
        "api",
        f"repos/{repo}/issues",
        "--method",
        "POST",
        "-f",
        f"title={issue.title}",
        "-f",
        f"body={issue_body(issue)}",
    ]
    for label in issue.labels:
        args.extend(["-f", f"labels[]={label}"])
    result = run_gh(args, attempts=6)
    return {
        "number": result["number"],
        "title": result["title"],
        "url": result["html_url"],
        "state": result["state"],
        "labels": [{"name": label} for label in issue.labels],
    }


def write_report(report_path: Path, rows: list[tuple[MethodIssue, dict[str, Any]]]) -> None:
    lines = [
        "# Telegram Bot API GitHub issue index",
        "",
        "Снимок состояния: 2026-05-25.",
        "Этот индекс связывает `BOTAPI-###` карточки из",
        "[telegram-bot-api-implementation-guide.md](telegram-bot-api-implementation-guide.md)",
        "с реальными GitHub issues в этом репозитории.",
        "",
        f"Всего issues для неинтегрированных методов: {len(rows)}.",
        "",
        "| ID | Method | GitHub issue | Area | Priority | Stage |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for method_issue, github_issue in rows:
        labels = {label["name"] for label in github_issue.get("labels", [])}
        area = next((label for label in method_issue.labels if label.startswith("area:")), "")
        priority = next(
            (label for label in method_issue.labels if label.startswith("priority:")), ""
        )
        stage = next((label for label in method_issue.labels if label.startswith("stage:")), "")
        label_warning = "" if set(method_issue.labels).issubset(labels) else " *(labels pending)*"
        lines.append(
            f"| {method_issue.botapi_id} | `{method_issue.method}` | "
            f"[#{github_issue['number']}]({github_issue['url']}){label_warning} | "
            f"`{area}` | `{priority}` | `{stage}` |"
        )
    lines.append("")
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default="labtgbot/telegram-claude-agent")
    parser.add_argument("--guide", type=Path, default=GUIDE_PATH)
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--issue-delay", type=float, default=1.0)
    args = parser.parse_args()

    method_issues = parse_backlog(args.guide)
    required_labels = {label for issue in method_issues for label in issue.labels}
    missing_labels = ensure_labels(args.repo, required_labels, apply=args.apply)
    existing_issues = fetch_existing_issues(args.repo)

    rows: list[tuple[MethodIssue, dict[str, Any]]] = []
    created = 0
    reused = 0
    for method_issue in method_issues:
        github_issue = existing_issues.get(method_issue.title)
        if github_issue:
            reused += 1
        elif args.apply:
            github_issue = create_issue(args.repo, method_issue)
            created += 1
            print(
                f"created #{github_issue['number']} {method_issue.botapi_id} {method_issue.method}",
                flush=True,
            )
            time.sleep(args.issue_delay)
        else:
            github_issue = {
                "number": "DRY-RUN",
                "title": method_issue.title,
                "url": "https://github.com/labtgbot/telegram-claude-agent/issues",
                "state": "DRY-RUN",
                "labels": [{"name": label} for label in method_issue.labels],
            }
        rows.append((method_issue, github_issue))

    if args.apply:
        write_report(args.report, rows)

    summary = {
        "apply": args.apply,
        "cards": len(method_issues),
        "missing_labels": missing_labels,
        "created_issues": created,
        "reused_issues": reused,
        "report": str(args.report) if args.apply else None,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
