# Повторный аудит логики приложения, 2026-06-12

Исходная задача: [#387](https://github.com/labtgbot/telegram-claude-agent/issues/387).

## Область проверки

Проверены основные runtime paths Telegram Claude Agent:

- bootstrap FastAPI/aiogram, webhook/polling lifecycle и конфигурация;
- chat pipeline, Guest Mode, streaming replies, media handling и history storage;
- free-claude-code proxy client;
- admin/callback authorization helpers;
- Docker/compose deployment path;
- unit/integration test coverage around the audited paths;
- закрытые audit issues/PRs после предыдущего аудита.

Предыдущий audit sweep зафиксирован в
[`docs/audit/code-audit-2026-06.md`](code-audit-2026-06.md). Связанные задачи
[#347](https://github.com/labtgbot/telegram-claude-agent/issues/347) -
[#364](https://github.com/labtgbot/telegram-claude-agent/issues/364) закрыты, а
соответствующие PRs смержены. Повторный проход сфокусирован на оставшихся
поведенческих, security и coverage gaps, которые не были вынесены в отдельные
задачи.

## Созданные задачи

| Issue | Приоритет | Область | Кратко |
| --- | --- | --- | --- |
| [#389](https://github.com/labtgbot/telegram-claude-agent/issues/389) | P2 | proxy-client | `ClaudeProxyClient` включает `stream=true`, но использует buffered `AsyncClient.post()` вместо настоящего streaming transport. |
| [#390](https://github.com/labtgbot/telegram-claude-agent/issues/390) | P1 | interactive/core-runtime | Guest Mode не проходит через `answerGuestQuery` при включенном streaming path. |
| [#391](https://github.com/labtgbot/telegram-claude-agent/issues/391) | P2 | core-runtime | Edit-based streaming вызывает `edit_text` на каждый delta без throttling/debounce. |
| [#392](https://github.com/labtgbot/telegram-claude-agent/issues/392) | P2 | config-deploy | Основной `docker-compose.yml` не передает часть documented security/runtime env, включая allowlist/admin settings. |
| [#393](https://github.com/labtgbot/telegram-claude-agent/issues/393) | P4 | config-deploy | `LOG_LEVEL` объявлен и документирован, но не применяется при настройке логирования. |
| [#394](https://github.com/labtgbot/telegram-claude-agent/issues/394) | P3 | config-deploy | Integration tests всегда skipped из-за `skipif(True)` и не включаются через `INTEGRATION_TEST=1`. |
| [#395](https://github.com/labtgbot/telegram-claude-agent/issues/395) | P4 | proxy-client | `test_list_models_openai_format` является no-op и не проверяет OpenAI-compatible `data[]` branch. |
| [#396](https://github.com/labtgbot/telegram-claude-agent/issues/396) | P2 | core-runtime/interactive | Admin-команды авторизуются только по `chat_id`; group admin chat дает доступ всем участникам чата. |
| [#397](https://github.com/labtgbot/telegram-claude-agent/issues/397) | P4 | config-deploy/storage | `RATE_LIMIT_REQUESTS_PER_MINUTE <= 0` принимается конфигурацией и блокирует все запросы. |

Все созданные задачи получили `kind:audit`, stage `S2-implementation` и
соответствующие area/priority labels.

## Локальная проверка

Проверки запускались в Docker/Python 3.11, потому что локальная системная среда
использует Python 3.14 и не содержит `pytest`/`ruff`.

- `pytest tests/unit`: 2216 passed, 1 warning.
- `ruff check .`: passed.
- `pip-audit --requirement requirements.txt --progress-spinner off`: no known vulnerabilities found.
- `docker build --tag telegram-claude-agent:ci .`: passed.

Логи сохранены во временных файлах:

- `/tmp/issue387-docker-pytest.log`
- `/tmp/issue387-docker-ruff.log`
- `/tmp/issue387-docker-pip-audit.log`
- `/tmp/issue387-docker-build.log`

## Ограничения

Интеграционные тесты не запускались против live proxy/bot окружения. Во время
аудита отдельно создана задача [#394](https://github.com/labtgbot/telegram-claude-agent/issues/394),
потому что текущий opt-in mechanism для `tests/integration/` фактически
отключен безусловным `skipif(True)`.
