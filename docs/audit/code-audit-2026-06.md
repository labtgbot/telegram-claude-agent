# Code Audit — Telegram Claude Agent

**Date:** 2026-06-01
**Scope:** Full review of the application logic, as requested in [#345](https://github.com/labtgbot/telegram-claude-agent/issues/345).
**Tracking epic:** [#365](https://github.com/labtgbot/telegram-claude-agent/issues/365) · **Milestone:** *Code Audit & Hardening*

This document records the methodology, scope, and findings of a full-logic audit of the bot. Every finding is filed as a standalone GitHub issue with `kind:*`, `area:*`, `priority:*`, and `stage:*` labels so the team can implement the fixes step by step. This PR adds **only documentation** — no behaviour changes — so each fix can be reviewed and shipped independently from its own issue.

## Methodology

- Read the core runtime end-to-end: `bot/main.py`, `bot/config.py`, `bot/handlers/{chat,commands,callbacks,inline}.py`, `bot/middlewares/{logging,rate_limit}.py`, `bot/utils/{storage,media}.py`, and the key services (`claude_proxy.py`, `answer_guest_query.py`, `send_chat_action.py`, `send_message_draft.py`).
- Sampled the ~170 thin `bot/services/*` Telegram API wrappers for systemic patterns.
- Reviewed deployment & supply chain: `Dockerfile`, `docker-compose*.yml`, `requirements.txt`, `pyproject.toml`, `.env.example`, `.gitignore`, and CI configuration.
- Each finding was verified against the current `main` with `file:line` references and quoted code. Speculative or stylistic items were dropped.

## Severity / priority scale

Findings reuse the repository's existing `priority:P1`–`priority:P4` labels (P1 = highest impact). `kind:*` denotes the nature of the finding (`bug`, `security`, `reliability`, `tech-debt`).

## Findings summary

| # | Issue | Area | Kind | Priority |
|---|-------|------|------|----------|
| 1 | [#347](https://github.com/labtgbot/telegram-claude-agent/issues/347) Unauthenticated webhook when `API_SECRET_TOKEN` unset | core-runtime / lifecycle | security | P1 |
| 2 | [#348](https://github.com/labtgbot/telegram-claude-agent/issues/348) Per-user model selection is ignored | core-runtime / interactive | bug | P1 |
| 3 | [#349](https://github.com/labtgbot/telegram-claude-agent/issues/349) Streaming with empty output stuck on placeholder | core-runtime | bug | P2 |
| 4 | [#350](https://github.com/labtgbot/telegram-claude-agent/issues/350) Message splitting breaks rendered HTML | core-runtime | bug | P2 |
| 5 | [#351](https://github.com/labtgbot/telegram-claude-agent/issues/351) Streaming proxy response never closed | proxy-client | reliability | P2 |
| 6 | [#352](https://github.com/labtgbot/telegram-claude-agent/issues/352) Unbounded in-memory growth | storage | reliability | P2 |
| 7 | [#353](https://github.com/labtgbot/telegram-claude-agent/issues/353) History stores/resends full base64 images | core-runtime | reliability | P3 |
| 8 | [#354](https://github.com/labtgbot/telegram-claude-agent/issues/354) Polling task unsupervised; silent failures | lifecycle / core-runtime | reliability | P2 |
| 9 | [#355](https://github.com/labtgbot/telegram-claude-agent/issues/355) Media downloads have no size limit | core-runtime | reliability / security | P3 |
| 10 | [#356](https://github.com/labtgbot/telegram-claude-agent/issues/356) Internal exception text leaked to users | core-runtime | security | P3 |
| 11 | [#357](https://github.com/labtgbot/telegram-claude-agent/issues/357) Deprecated FastAPI/aiogram APIs | core-runtime | tech-debt | P3 |
| 12 | [#358](https://github.com/labtgbot/telegram-claude-agent/issues/358) Container/runtime hardening | config-deploy | tech-debt / security | P3 |
| 13 | [#359](https://github.com/labtgbot/telegram-claude-agent/issues/359) Outdated/unaudited dependencies | config-deploy | security / tech-debt | P2 |
| 14 | [#360](https://github.com/labtgbot/telegram-claude-agent/issues/360) No CI pipeline | config-deploy | tech-debt | P2 |
| 15 | [#361](https://github.com/labtgbot/telegram-claude-agent/issues/361) Config robustness (id-list crash, base_url) | config-deploy | bug | P4 |
| 16 | [#362](https://github.com/labtgbot/telegram-claude-agent/issues/362) Dead/incorrect `count_tokens` | proxy-client | tech-debt | P4 |
| 17 | [#363](https://github.com/labtgbot/telegram-claude-agent/issues/363) Duplicate authorization guards | core-runtime | tech-debt | P4 |
| 18 | [#364](https://github.com/labtgbot/telegram-claude-agent/issues/364) `keep_chat_action` retries forever | outbound-media | reliability | P4 |

## Highlights

### Security
- **Unauthenticated webhook ([#347](https://github.com/labtgbot/telegram-claude-agent/issues/347)).** `bot/main.py:123-135` only checks the Telegram secret token when `api_secret_token` is truthy, and `bot/config.py:37` makes it optional. A deployment that omits it exposes an open `/webhook` that feeds forged updates into the dispatcher.
- **Error-message disclosure ([#356](https://github.com/labtgbot/telegram-claude-agent/issues/356)).** Handlers echo raw exception text (`f"❌ Error: {exc}"`) to users, which can include the internal proxy URL.
- **Supply chain ([#359](https://github.com/labtgbot/telegram-claude-agent/issues/359)).** Addressed by pinning runtime/test/transitive dependencies, replacing EOL `PyPDF2` with `pypdf`, and bumping vulnerable multipart/media/web dependencies.

### Correctness
- **Model selection is a no-op ([#348](https://github.com/labtgbot/telegram-claude-agent/issues/348)).** `/model` and the inline buttons persist a per-user model that the chat pipeline never reads — every request uses `settings.free_claude_default_model`.
- **Streaming edge cases ([#349](https://github.com/labtgbot/telegram-claude-agent/issues/349), [#350](https://github.com/labtgbot/telegram-claude-agent/issues/350)).** Empty model output leaves the `"…"` placeholder with no fallback; length-based splitting can cut rendered HTML mid-tag and fall back to truncated plaintext.

### Reliability
- Streaming responses are not explicitly closed ([#351](https://github.com/labtgbot/telegram-claude-agent/issues/351)); in-memory maps for history and rate limiting grow without eviction ([#352](https://github.com/labtgbot/telegram-claude-agent/issues/352)); base64 images are retained and replayed in history ([#353](https://github.com/labtgbot/telegram-claude-agent/issues/353)); the polling task is unsupervised ([#354](https://github.com/labtgbot/telegram-claude-agent/issues/354)); media downloads are unbounded ([#355](https://github.com/labtgbot/telegram-claude-agent/issues/355)).

### Tech debt
- Deprecated framework APIs ([#357](https://github.com/labtgbot/telegram-claude-agent/issues/357)), Docker/compose hardening ([#358](https://github.com/labtgbot/telegram-claude-agent/issues/358)), missing CI ([#360](https://github.com/labtgbot/telegram-claude-agent/issues/360)), config validation ([#361](https://github.com/labtgbot/telegram-claude-agent/issues/361)), dead `count_tokens` ([#362](https://github.com/labtgbot/telegram-claude-agent/issues/362)), and duplicated guards ([#363](https://github.com/labtgbot/telegram-claude-agent/issues/363)).

## Recommended sequencing

1. **P1 first:** close the webhook auth gap (#347) and fix model selection (#348).
2. **Add the safety net:** stand up CI (#360) and audit/bump dependencies (#359) so subsequent fixes are guarded against regression.
3. **P2 correctness/reliability:** #349, #350, #351, #352, #354.
4. **P3:** #353, #355, #356, #357, #358.
5. **P4 cleanup:** #361, #362, #363, #364.

## What this PR contains

Only this document. The audit is intentionally non-destructive: it produces a verified backlog (issues #347–#365) rather than touching application code, so each fix lands through its own focused, testable change.
