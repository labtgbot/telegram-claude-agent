# Полный аудит логики приложения, 2026-06-14

Исходная задача: [#407](https://github.com/labtgbot/telegram-claude-agent/issues/407).

## Область проверки

Проведён сквозной разбор всей рантайм-логики Telegram Claude Agent с упором на
поведение в проде, надёжность стриминга, безопасность и корректность рендеринга
ответов. Конкретно проверены:

- bootstrap FastAPI/aiogram: lifespan, регистрация middleware, polling-супервизор,
  webhook/polling lifecycle и обработка системных сигналов;
- chat pipeline: streaming replies, edit-based preview, разбиение длинных ответов,
  HTML/Markdown рендеринг (`md_to_html`) и plain-text фоллбэки;
- Guest Mode (`answerGuestQuery`) на streaming- и non-streaming-путях;
- free-claude-code proxy client: парсинг SSE, обработка mid-stream ошибок Anthropic,
  завершение стрима;
- хранилище истории и пользовательских настроек (`MemoryStorage`, TTL-вытеснение);
- callback- и inline-хендлеры, их авторизация относительно `allowed_chat_ids`;
- media handling: извлечение текста из документов, lazy-загрузка whisper-модели;
- конфигурация (`pydantic-settings`, чтение `.env`), webhook secret token;
- покрытие аудируемых путей юнит-/интеграционными тестами;
- закрытые audit issues/PRs предыдущих проходов, чтобы не дублировать находки.

Предыдущие audit sweeps зафиксированы в
[`docs/audit/code-audit-2026-06.md`](code-audit-2026-06.md) (задачи
[#347](https://github.com/labtgbot/telegram-claude-agent/issues/347)–[#364](https://github.com/labtgbot/telegram-claude-agent/issues/364),
эпик [#365](https://github.com/labtgbot/telegram-claude-agent/issues/365)) и
[`docs/audit/code-audit-2026-06-12.md`](code-audit-2026-06-12.md) (задача
[#387](https://github.com/labtgbot/telegram-claude-agent/issues/387), issues
[#389](https://github.com/labtgbot/telegram-claude-agent/issues/389)–[#397](https://github.com/labtgbot/telegram-claude-agent/issues/397)).
Все они закрыты, соответствующие PRs смержены. Текущий проход сфокусирован на
оставшихся поведенческих, security и reliability дефектах, ранее не вынесенных в
отдельные задачи.

Каждая находка эмпирически воспроизведена отдельным скриптом в
[`experiments/`](../../experiments); скрипты приложены к репозиторию и
прогоняются на CI (`ruff check .` покрывает и эту директорию).

## Созданные задачи

Создано 18 задач ([#409](https://github.com/labtgbot/telegram-claude-agent/issues/409)–[#426](https://github.com/labtgbot/telegram-claude-agent/issues/426)).
Все получили `kind:audit`, stage `S2-implementation`, профильные `kind:*`,
`area:*` и `priority:*` labels.

| Issue | Приоритет | Область | Кратко |
| --- | --- | --- | --- |
| [#409](https://github.com/labtgbot/telegram-claude-agent/issues/409) | P1 | core-runtime, storage | Middleware зарегистрированы на `dp.update`, поэтому `RateLimitMiddleware`/`LoggingMiddleware` ветвятся по `isinstance(event, Message)`, который для `Update` всегда `False` → rate limiting и логирование сообщений не работают в проде. |
| [#410](https://github.com/labtgbot/telegram-claude-agent/issues/410) | P1 | core-runtime | Бот по умолчанию шлёт `parse_mode=HTML`; plain-text фоллбэки и стрим-превью вызывают `answer()`/`edit_text()` без `parse_mode=None`, поэтому повторно резолвятся в HTML и падают с тем же 400 → сообщение теряется. |
| [#411](https://github.com/labtgbot/telegram-claude-agent/issues/411) | P2 | core-runtime | `md_to_html` независимыми проходами `_MD_BOLD`/`_MD_ITALIC` даёт перекрывающиеся теги для `***x***` (`<b><i>x</b></i>`) и манглит одиночные `*` в математике/glob/списках → Telegram 400. |
| [#412](https://github.com/labtgbot/telegram-claude-agent/issues/412) | P2 | proxy-client, core-runtime | Anthropic шлёт mid-stream `{"type":"error"}` поверх HTTP 200; `_stream_response` распознаёт только `[DONE]`/`message_stop`, error-событие игнорируется → усечённый ответ выдаётся как полный. |
| [#413](https://github.com/labtgbot/telegram-claude-agent/issues/413) | P2 | interactive, core-runtime | Guest Mode отправляет ответ через `answerGuestQuery` без `parse_mode` → гость видит сырую HTML-разметку вместо форматирования. |
| [#414](https://github.com/labtgbot/telegram-claude-agent/issues/414) | P2 | lifecycle, core-runtime | `start_polling(handle_signals=True)` по умолчанию перехватывает SIGTERM/SIGINT у uvicorn, а супервизор перезапускает polling на сигнал → graceful shutdown сломан. |
| [#415](https://github.com/labtgbot/telegram-claude-agent/issues/415) | P2 | storage, core-runtime | У истории (ключ `(chat_id,user_id)`) и настроек (ключ `user_id`) независимые TTL-часы последнего доступа → активный чат вытесняет выбранную пользователем модель. |
| [#416](https://github.com/labtgbot/telegram-claude-agent/issues/416) | P3 | lifecycle, core-runtime | `start_polling(skip_updates=True)` в aiogram 3 не существует как параметр: протекает в `**kwargs`→`workflow_data`, backlog не сбрасывается; нужен `delete_webhook(drop_pending_updates=True)`. |
| [#417](https://github.com/labtgbot/telegram-claude-agent/issues/417) | P3 | lifecycle, core-runtime | `await on_startup()` вызывается вне `try/finally` lifespan → при частичном старте `on_shutdown`-очистка пропускается. |
| [#418](https://github.com/labtgbot/telegram-claude-agent/issues/418) | P3 | interactive, core-runtime | Callback- и inline-хендлеры не проверяют `allowed_chat_ids`, который применяет chat pipeline → обход allowlist через смену модели/инлайн-режим. |
| [#419](https://github.com/labtgbot/telegram-claude-agent/issues/419) | P3 | core-runtime | Извлечение текста из документа сверяет MIME строго (`== "text/plain"`) и отвергает валидный `text/plain; charset=utf-8`. |
| [#420](https://github.com/labtgbot/telegram-claude-agent/issues/420) | P4 | lifecycle | Webhook secret token сравнивается оператором `!=` вместо `secrets.compare_digest` (не constant-time; на реальной длине токена практически не эксплуатируется — hardening). |
| [#421](https://github.com/labtgbot/telegram-claude-agent/issues/421) | P4 | core-runtime | Сбой mid-stream показывает одну и ту же ошибку дважды: как отредактированный плейсхолдер и как новое сообщение из внешнего `except`. |
| [#422](https://github.com/labtgbot/telegram-claude-agent/issues/422) | P4 | proxy-client | SSE-парсер хрупок к spec-легальным фреймам (`data:` без пробела, многострочный `data:`) → потенциальная потеря/некорректный разбор событий. |
| [#423](https://github.com/labtgbot/telegram-claude-agent/issues/423) | P4 | interactive | Имя модели из `callback_data` эхо-выводится без экранирования при `parse_mode=HTML` → битый рендер/инъекция тегов при подменённом callback. |
| [#424](https://github.com/labtgbot/telegram-claude-agent/issues/424) | P4 | core-runtime | Ленивый кэш whisper-модели (`_transcribe_sync`) не потокобезопасен → двойная загрузка модели при конкурентном холодном старте. |
| [#425](https://github.com/labtgbot/telegram-claude-agent/issues/425) | P4 | lifecycle, config-deploy | Хардненинг webhook lifecycle: `set_webhook` без `drop_pending_updates` и без try/except, `on_shutdown` не вызывает `delete_webhook` → backlog на redeploy и «висящий» webhook к мёртвому эндпоинту. |
| [#426](https://github.com/labtgbot/telegram-claude-agent/issues/426) | P4 | config-deploy | `env_file=".env"` задан относительным путём → при запуске не из корня проекта (systemd `WorkingDirectory`, `python -m bot` из другого cwd) `.env` молча игнорируется: краш на старте или тихая подмена настроек дефолтами. |

### Распределение по приоритетам

- **P1 (2):** [#409](https://github.com/labtgbot/telegram-claude-agent/issues/409), [#410](https://github.com/labtgbot/telegram-claude-agent/issues/410) — функции, заявленные как работающие, не работают в проде (rate limiting/логирование, доставка отформатированного ответа).
- **P2 (5):** [#411](https://github.com/labtgbot/telegram-claude-agent/issues/411), [#412](https://github.com/labtgbot/telegram-claude-agent/issues/412), [#413](https://github.com/labtgbot/telegram-claude-agent/issues/413), [#414](https://github.com/labtgbot/telegram-claude-agent/issues/414), [#415](https://github.com/labtgbot/telegram-claude-agent/issues/415) — заметная деградация UX/надёжности на реальных сценариях.
- **P3 (4):** [#416](https://github.com/labtgbot/telegram-claude-agent/issues/416), [#417](https://github.com/labtgbot/telegram-claude-agent/issues/417), [#418](https://github.com/labtgbot/telegram-claude-agent/issues/418), [#419](https://github.com/labtgbot/telegram-claude-agent/issues/419) — корректность жизненного цикла, авторизация второстепенных входов, edge-cases.
- **P4 (7):** [#420](https://github.com/labtgbot/telegram-claude-agent/issues/420), [#421](https://github.com/labtgbot/telegram-claude-agent/issues/421), [#422](https://github.com/labtgbot/telegram-claude-agent/issues/422), [#423](https://github.com/labtgbot/telegram-claude-agent/issues/423), [#424](https://github.com/labtgbot/telegram-claude-agent/issues/424), [#425](https://github.com/labtgbot/telegram-claude-agent/issues/425), [#426](https://github.com/labtgbot/telegram-claude-agent/issues/426) — hardening и устойчивость к редким/враждебным условиям.

## Проверенные гипотезы без отдельной задачи

Часть подозрений при разборе оказалась ложноположительными — задачи по ним
**не** заводились, чтобы не загрязнять трекер:

- **Чтение `.env` через `ConfigDict(env_file=...)`.** Возникло подозрение, что
  `model_config = ConfigDict(env_file=".env")` (вместо `SettingsConfigDict`) не
  подхватывается `pydantic-settings` и `.env` игнорируется полностью. Проверка
  показала: `BaseSettings.__init_subclass__` мёржит переданный `ConfigDict` в
  `SettingsConfigDict`, поэтому `env_file` **действительно** применяется и `.env`
  читается (когда лежит в cwd). Воспроизведение —
  [`experiments/exp_cfg_env_file_ignored.py`](../../experiments/exp_cfg_env_file_ignored.py).
  Подтверждённый false positive, исключён из списка задач. **Важно:** это не
  отменяет реальную хрупкость относительного пути к `.env`, которая вынесена
  отдельной задачей [#426](https://github.com/labtgbot/telegram-claude-agent/issues/426).

- **Timing-атака на webhook secret token.** Сравнение через `!=`
  ([#420](https://github.com/labtgbot/telegram-claude-agent/issues/420))
  не является constant-time, однако микробенчмарк
  ([`experiments/exp_cfg_token_timing.py`](../../experiments/exp_cfg_token_timing.py))
  показал, что на реальной длине Telegram-токена (≤256 байт) сигнал раннего
  выхода тонет в фиксированных накладных расходах и по сети не измерим. Поэтому
  задача заведена как **hardening (P4)**, а не как эксплуатируемая уязвимость, —
  чтобы не завышать severity.

- **Повторный `bot.session.close()`.** `start_polling` по умолчанию
  (`close_bot_session=True`) закрывает сессию, а `on_shutdown` закрывает её
  повторно. Проверка
  ([`experiments/exp_cfg_session_close_and_webhook.py`](../../experiments/exp_cfg_session_close_and_webhook.py))
  подтвердила: повторное закрытие `AiohttpSession` безопасно (исключения нет).
  Самостоятельной задачи не требует; асимметрия webhook-lifecycle вынесена в
  [#425](https://github.com/labtgbot/telegram-claude-agent/issues/425).

- **Краш `LoggingMiddleware` на `from_user == None`.**
  [`experiments/exp_proxy_logging_mw_none_user.py`](../../experiments/exp_proxy_logging_mw_none_user.py)
  показывает `AttributeError: 'NoneType' object has no attribute 'id'` при
  обращении к `event.from_user.id`. В текущем проде это **не срабатывает**:
  из-за [#409](https://github.com/labtgbot/telegram-claude-agent/issues/409)
  middleware получает `Update`, ветка `isinstance(event, Message)` ложна и
  `from_user` не читается. Дефект **латентный** — оживёт ровно при фиксе #409,
  поэтому вынесен не отдельной задачей, а явной scope-заметкой внутри #409
  (добавить guard `from_user is None`), чтобы фикс не поменял no-op на краш.

## Локальная проверка

Проверки прогонялись в Python 3.11 venv (CI-конфигурация), потому что системная
среда использует Python 3.14 без нужных зависимостей.

- `ruff check .`: **All checks passed!** (включая директорию `experiments/`).
- `pytest --cov=bot --cov-report=term-missing`: **2254 passed, 2 skipped**,
  1 warning; покрытие `bot` — **94%**.
- `pip-audit --requirement requirements.txt --progress-spinner off`:
  **No known vulnerabilities found**.

Команды соответствуют джобам `lint`/`test`/`security` из
[`.github/workflows/ci.yml`](../../.github/workflows/ci.yml); вывод
воспроизводится локально на той же конфигурации. Сырые логи прогонов в
репозиторий не коммитятся (директория логов исключена `.gitignore`).

## Ограничения

- Изменения поведения приложения в этом PR **не вносятся**: PR docs-only
  (audit-документ + воспроизводящие скрипты в `experiments/`). Исправления
  выполняются отдельными PR по созданным задачам на стадии `S2-implementation`.
- Интеграционные тесты против live proxy/bot не запускались; механизм opt-in для
  `tests/integration/` остаётся отключённым (зафиксировано ранее в
  [#394](https://github.com/labtgbot/telegram-claude-agent/issues/394)).
- Severity находок указана консервативно: где практическая эксплуатируемость
  ограничена (например, [#420](https://github.com/labtgbot/telegram-claude-agent/issues/420)),
  это явно отмечено в теле задачи и приоритет занижен до hardening.
