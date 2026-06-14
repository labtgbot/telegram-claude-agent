# Воспроизводящие эксперименты аудита (#407)

Скрипты `exp_*.py` в этой директории — минимальные воспроизводящие примеры для
находок сквозного аудита логики приложения (задача
[#407](https://github.com/labtgbot/telegram-claude-agent/issues/407)). Каждый
подтверждает конкретный дефект против **реального** кода `bot/` (без правок
поведения приложения). Сводка — в
[`docs/audit/code-audit-2026-06-14.md`](../docs/audit/code-audit-2026-06-14.md).

## Как запускать

Нужны те же переменные окружения, что и в `tests/conftest.py` (иначе
`bot.config` падает на импорте):

```bash
export FREE_CLAUDE_BASE_URL=http://localhost:8082
export FREE_CLAUDE_AUTH_TOKEN=testtoken
export FREE_CLAUDE_DEFAULT_MODEL=claude-3-haiku-20240307
export TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
unset TELEGRAM_ALLOWED_CHATS TELEGRAM_ALLOWED_CHAT_IDS
export PYTHONPATH=.

python experiments/exp_real_middlewares.py
```

Скрипты автономны (стандартная библиотека + зависимости проекта), не сетевые и
безопасны для повтора. Это **не** pytest-тесты: `pytest` их не собирает
(`testpaths = ["tests"]`), но `ruff check .` директорию покрывает.

## Карта «находка → скрипты»

★ — основной воспроизводящий скрипт находки; остальные подтверждают смежные грани.

| Issue | Приоритет | Скрипты |
| --- | --- | --- |
| [#409](https://github.com/labtgbot/telegram-claude-agent/issues/409) Middleware на `dp.update` — rate limit/логи не работают | P1 | ★ `exp_real_middlewares.py`, `exp_middleware_event_type.py`, `exp_proxy_logging_mw_update_type.py`, `exp_proxy_logging_mw_none_user.py` (латентный `from_user=None`) |
| [#410](https://github.com/labtgbot/telegram-claude-agent/issues/410) Plain-text/стрим-превью повторно резолвят HTML → потеря | P1 | ★ `exp_md_fallback_e2e.py`, `exp_md_fallback_path.py`, `exp_edit_parse_mode.py`, `exp_md_stream_edit_fallback.py` |
| [#411](https://github.com/labtgbot/telegram-claude-agent/issues/411) `md_to_html`: перекрывающиеся теги + мангление `*` | P2 | ★ `exp_md_triplestar_telegram.py`, `exp_proxy_md_bad_nesting.py`, `exp_md_crosstag.py`, `exp_md_italic_invalid.py`, `exp_md_italic_mangle.py`, `exp_md_unbalanced.py`, `exp_proxy_md_html_injection.py` |
| [#412](https://github.com/labtgbot/telegram-claude-agent/issues/412) Mid-stream ошибки Anthropic проглатываются | P2 | ★ `exp_proxy_sse_error_event.py`, `exp_proxy_stream_hang_no_stop.py` |
| [#413](https://github.com/labtgbot/telegram-claude-agent/issues/413) Guest Mode HTML через `answerGuestQuery` | P2 | ★ `exp_proxy_guest_html_plaintext.py`, `exp_proxy_guest_routing.py` |
| [#414](https://github.com/labtgbot/telegram-claude-agent/issues/414) Graceful shutdown: polling перехватывает сигналы | P2 | ★ `exp_cfg_signal_handlers.py`, `exp_cfg_supervisor_restart_on_signal.py` |
| [#415](https://github.com/labtgbot/telegram-claude-agent/issues/415) Модель вытесняется по TTL (рассинхрон часов) | P2 | ★ `exp_stor_settings_eviction_realflow.py`, `exp_stor_settings_eviction.py`, `exp_stor_settings_eviction_chatpath.py`, `exp_stor_ttl_ordering.py` |
| [#416](https://github.com/labtgbot/telegram-claude-agent/issues/416) `skip_updates=True` игнорируется aiogram 3 | P3 | ★ `exp_cfg_skip_updates.py` |
| [#417](https://github.com/labtgbot/telegram-claude-agent/issues/417) `on_startup` вне lifespan `try/finally` | P3 | ★ `exp_cfg_lifespan_startup_failure.py` |
| [#418](https://github.com/labtgbot/telegram-claude-agent/issues/418) Callback/inline обходят allowlist | P3 | ★ `exp_stor_callback_no_authz.py`, `exp_stor_inline_no_authz.py`, `exp_proxy_admin_callback_chatid.py`, `exp_proxy_admin_userid_none.py` |
| [#419](https://github.com/labtgbot/telegram-claude-agent/issues/419) Документ `text/plain; charset=…` отвергается | P3 | ★ `exp_stor_media_mime.py` |
| [#420](https://github.com/labtgbot/telegram-claude-agent/issues/420) Webhook token: `!=` вместо `compare_digest` | P4 | ★ `exp_cfg_token_timing.py` |
| [#421](https://github.com/labtgbot/telegram-claude-agent/issues/421) Сбой стриминга показывает ошибку дважды | P4 | ★ `exp_proxy_double_error_report.py` |
| [#422](https://github.com/labtgbot/telegram-claude-agent/issues/422) SSE-парсер хрупок к spec-легальным фреймам | P4 | ★ `exp_proxy_sse_multiline_and_nospace.py` |
| [#423](https://github.com/labtgbot/telegram-claude-agent/issues/423) Неэкранированный HTML-эхо имени модели | P4 | ★ `exp_stor_callback_html_echo.py` |
| [#424](https://github.com/labtgbot/telegram-claude-agent/issues/424) Whisper lazy-cache не потокобезопасен | P4 | ★ `exp_stor_whisper_model_race.py` |
| [#425](https://github.com/labtgbot/telegram-claude-agent/issues/425) Хардненинг webhook lifecycle | P4 | ★ `exp_cfg_session_close_and_webhook.py` |
| [#426](https://github.com/labtgbot/telegram-claude-agent/issues/426) `env_file` относительным путём | P4 | ★ `exp_cfg_env_and_aliases.py` |

## Проверено и признано чистым (без задачи)

Скрипты, опровергнувшие подозрение или показавшие, что в shipped-конфигурации
дефект не проявляется:

| Скрипт | Вывод |
| --- | --- |
| `exp_cfg_env_file_ignored.py` | `ConfigDict(env_file=...)` **применяется** (мёржится в `SettingsConfigDict`), `.env` читается. False positive. Отдельная реальная хрупкость относительного пути — [#426](https://github.com/labtgbot/telegram-claude-agent/issues/426). |
| `exp_md_split_nested.py` | `_split_for_telegram` корректно переоткрывает теги на вложенных спанах — `RESULT: ok`. |
| `exp_md_split_textloss.py` | Видимый текст не теряется и не дублируется на границах чанков — `text preserved: True`. |
| `exp_proxy_split_progress.py` | Сплиттер всегда завершается, нет over-limit/unbalanced (кроме легитимного случая атомарного токена длиннее лимита). |
| `exp_stor_history_trim_structure.py` | Осиротевший лидирующий `assistant` возникает только при **нечётном** `max_history`; приложение использует хардкод `max_history=20` (чётный) с атомарным добавлением пар → история всегда начинается с `user`. Не проявляется. |
