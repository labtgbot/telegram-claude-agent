# Telegram Bot API implementation guide

Снимок состояния: 2026-05-25. Guide подготовлен по официальной
документации Telegram Bot API: https://core.telegram.org/bots/api.
На момент снимка страница описывает Bot API 10.0 от 2026-05-08.

Цель документа: превратить пробелы покрытия Telegram Bot API в backlog
полноценных GitHub issues. Каждая карточка ниже рассчитана на создание
отдельного issue: у нее есть заголовок, labels, stages, scope и acceptance
criteria. Это не означает, что все методы нужно внедрять одним PR; наоборот,
каждый метод должен входить отдельным небольшим изменением или частью
узкого epic, если Telegram требует общий service layer.

Карточки из этого guide заведены как реальные GitHub issues в репозитории.
Индекс соответствия `BOTAPI-###` -> issue находится в
[telegram-bot-api-issue-index.md](telegram-bot-api-issue-index.md).

## Текущее покрытие

Всего методов Bot API в официальной документации: 176.
Фактически интегрировано в проекте: 8.
Остается для backlog: 168. Карточка BOTAPI-002 сохранена ниже как
реализованная, чтобы не менять стабильную нумерацию method backlog.

Интегрированные методы:

- `getUpdates`
- `setWebhook`
- `getWebhookInfo`
- `getMe`
- `sendMessage`
- `getFile`
- `editMessageText`
- `answerInlineQuery`

`getUpdates` используется через aiogram long polling, `setWebhook` - при
startup webhook mode, `sendMessage`/`editMessageText`/`getFile`/
`answerInlineQuery` вызываются через aiogram helpers. Остальные методы ниже
пока не имеют отдельного сценария, handler, service wrapper или тестов.

## Общие labels

Базовые labels для каждого будущего issue:

- `telegram-api`
- `bot-api-10.0`
- `kind:feature`
- один `area:*` label из карточки
- один `priority:*` label из карточки
- текущий `stage:*` label, который меняется по мере выполнения

Stage labels:

- `stage:S1-spec` - сверить сигнатуру метода, типы, ограничения, права бота,
  required update types и поддержку в текущем `aiogram==3.3.0`; если wrapper
  отсутствует, решить: raw Bot API call или отдельный PR на upgrade aiogram.
- `stage:S2-design` - описать пользовательский/админский сценарий, настройки,
  privacy/security impact, rollback и связь с `free-claude-code`.
- `stage:S3-implementation` - добавить handler/service wrapper, структурные
  логи, обработку ошибок Telegram и rate-limit/allowlist checks.
- `stage:S4-tests` - добавить unit tests с моками Telegram Bot API;
  integration tests делать opt-in, если нужен реальный bot token или chat id.
- `stage:S5-docs` - обновить README, functionality analysis, примеры
  конфигурации и operational notes.

Общий Definition of Done для каждого метода:

- есть один понятный entrypoint: команда, handler, startup job, service helper
  или internal API, а не случайный вызов в середине обработчика;
- права Telegram, privacy implications и ограничения метода явно отражены в
  issue и документации;
- happy path, отказ Telegram API, validation error и отсутствие прав покрыты
  тестами или явно помечены как blocked-by-real-telegram integration;
- sensitive values вроде bot tokens, payment payloads и business data не
  попадают в логи;
- `docs/functionality-analysis.md` обновлен после завершения метода.

## Рекомендуемые milestones

1. Foundation: lifecycle diagnostics, `sendChatAction`, command sync,
   callback settings и official Guest Mode.
2. Rich Claude UX: outbound media, message drafts, safe message management и
   полноценные inline/callback flows.
3. Group power tools: chat admin, moderation, invite links, join requests и
   forum topics.
4. Platform expansion: Web Apps, business accounts, managed bots, payments,
   gifts, Stars и stories.
5. Domain-specific tail: stickers/custom emoji, Telegram Passport и games.

## Issue backlog by method

### Lifecycle и диагностика

Area label: `area:lifecycle`. Priority baseline: `priority:P0`
(P0: фундаментальный метод для следующего слоя Telegram API).

#### BOTAPI-001: `deleteWebhook`

- Title: `telegram-api: реализовать deleteWebhook`
- Official docs: https://core.telegram.org/bots/api#deletewebhook
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:lifecycle`, `priority:P0`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить явный способ удалить webhook с опциональным drop_pending_updates перед переходом на polling или local Bot API.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.
#### BOTAPI-002: `getWebhookInfo`

- Title: `telegram-api: реализовать getWebhookInfo`
- Status: implemented in PR #176 as restricted `/webhook` diagnostics.
- Official docs: https://core.telegram.org/bots/api#getwebhookinfo
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:lifecycle`, `priority:P0`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить диагностику webhook status, pending_update_count, allowed_updates и последней ошибки доставки.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-003: `logOut`

- Title: `telegram-api: реализовать logOut`
- Status: implemented in PR #178 as restricted `/logout` command with confirmation.
- Official docs: https://core.telegram.org/bots/api#logout
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:lifecycle`, `priority:P0`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Описать и реализовать защищенный ops-flow выхода из cloud Bot API перед запуском local Bot API server.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-004: `close`

- Title: `telegram-api: реализовать close`
- Status: implemented in PR #179 as restricted `/close` command with confirmation.
- Official docs: https://core.telegram.org/bots/api#close
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:lifecycle`, `priority:P0`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Описать и реализовать безопасное закрытие локального bot instance при миграции между серверами.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

### Пересылка и копирование сообщений

Area label: `area:message-relay`. Priority baseline: `priority:P2`
(P2: важно для групп, администрирования или интерактивности).

#### BOTAPI-005: `forwardMessage`

- Title: `telegram-api: реализовать forwardMessage`
- Status: implemented in PR #180 as restricted admin `/forward` relay command.
- Official docs: https://core.telegram.org/bots/api#forwardmessage
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:message-relay`, `priority:P2`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `forwardMessage` в область: управляемую пересылку или копирование сообщений между чатами с учетом protected content и album grouping. Определить конкретный сценарий: админский сценарий для поддержки/модерации или внутренний сервисный helper.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-006: `forwardMessages`

- Title: `telegram-api: реализовать forwardMessages`
- Status: implemented in PR #182 as restricted admin `/forwards` batch relay command.
- Official docs: https://core.telegram.org/bots/api#forwardmessages
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:message-relay`, `priority:P2`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `forwardMessages` в область: управляемую пересылку или копирование сообщений между чатами с учетом protected content и album grouping. Определить конкретный сценарий: админский сценарий для поддержки/модерации или внутренний сервисный helper.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-007: `copyMessage`

- Title: `telegram-api: реализовать copyMessage`
- Status: implemented in PR #181 as restricted admin `/copy` relay command.
- Official docs: https://core.telegram.org/bots/api#copymessage
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:message-relay`, `priority:P2`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `copyMessage` в область: управляемую пересылку или копирование сообщений между чатами с учетом protected content и album grouping. Определить конкретный сценарий: админский сценарий для поддержки/модерации или внутренний сервисный helper.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-008: `copyMessages`

- Title: `telegram-api: реализовать copyMessages`
- Status: implemented in PR #184 as restricted admin `/copies` batch relay command.
- Official docs: https://core.telegram.org/bots/api#copymessages
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:message-relay`, `priority:P2`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `copyMessages` в область: управляемую пересылку или копирование сообщений между чатами с учетом protected content и album grouping. Определить конкретный сценарий: админский сценарий для поддержки/модерации или внутренний сервисный helper.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

### Rich outbound messaging и реакции

Area label: `area:outbound-media`. Priority baseline: `priority:P1`
(P1: высокий пользовательский эффект для Claude-бота).

#### BOTAPI-009: `sendPhoto`

- Title: `telegram-api: реализовать sendPhoto`
- Official docs: https://core.telegram.org/bots/api#sendphoto
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:outbound-media`, `priority:P1`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Отправлять сгенерированные/полученные изображения как фото, а не только текстовую интерпретацию.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-010: `sendLivePhoto`

- Title: `telegram-api: реализовать sendLivePhoto`
- Official docs: https://core.telegram.org/bots/api#sendlivephoto
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:outbound-media`, `priority:P1`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `sendLivePhoto` в область: исходящие ответы бота за пределами plain text, включая typing/draft feedback, медиа, polls, checklist и reactions. Определить конкретный сценарий: расширение chat handler или отдельный response builder, который выбирает Telegram output по результату Claude/proxy.
- Method note: Новый метод Bot API 10.0; aiogram 3.3.0 не имеет typed wrapper.
- Status: implemented in PR #186 as restricted admin `/livephoto` outbound media command via an isolated raw Bot API helper.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-011: `sendAudio`

- Title: `telegram-api: реализовать sendAudio`
- Official docs: https://core.telegram.org/bots/api#sendaudio
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:outbound-media`, `priority:P1`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `sendAudio` в область: исходящие ответы бота за пределами plain text, включая typing/draft feedback, медиа, polls, checklist и reactions. Определить конкретный сценарий: расширение chat handler или отдельный response builder, который выбирает Telegram output по результату Claude/proxy.
- Status: implemented in PR #185 as restricted admin `/audio` outbound media command.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-012: `sendDocument`

- Title: `telegram-api: реализовать sendDocument`
- Official docs: https://core.telegram.org/bots/api#senddocument
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:outbound-media`, `priority:P1`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Возвращать большие текстовые, PDF или исходные артефакты как document, когда sendMessage не подходит.
- Status: implemented in PR #187 as restricted admin `/document` outbound media command.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-013: `sendVideo`

- Title: `telegram-api: реализовать sendVideo`
- Official docs: https://core.telegram.org/bots/api#sendvideo
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:outbound-media`, `priority:P1`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `sendVideo` в область: исходящие ответы бота за пределами plain text, включая typing/draft feedback, медиа, polls, checklist и reactions. Определить конкретный сценарий: расширение chat handler или отдельный response builder, который выбирает Telegram output по результату Claude/proxy.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-014: `sendAnimation`

- Title: `telegram-api: реализовать sendAnimation`
- Official docs: https://core.telegram.org/bots/api#sendanimation
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:outbound-media`, `priority:P1`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `sendAnimation` в область: исходящие ответы бота за пределами plain text, включая typing/draft feedback, медиа, polls, checklist и reactions. Определить конкретный сценарий: расширение chat handler или отдельный response builder, который выбирает Telegram output по результату Claude/proxy.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-015: `sendVoice`

- Title: `telegram-api: реализовать sendVoice`
- Official docs: https://core.telegram.org/bots/api#sendvoice
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:outbound-media`, `priority:P1`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `sendVoice` в область: исходящие ответы бота за пределами plain text, включая typing/draft feedback, медиа, polls, checklist и reactions. Определить конкретный сценарий: расширение chat handler или отдельный response builder, который выбирает Telegram output по результату Claude/proxy.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-016: `sendVideoNote`

- Title: `telegram-api: реализовать sendVideoNote`
- Official docs: https://core.telegram.org/bots/api#sendvideonote
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:outbound-media`, `priority:P1`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `sendVideoNote` в область: исходящие ответы бота за пределами plain text, включая typing/draft feedback, медиа, polls, checklist и reactions. Определить конкретный сценарий: расширение chat handler или отдельный response builder, который выбирает Telegram output по результату Claude/proxy.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-017: `sendPaidMedia`

- Title: `telegram-api: реализовать sendPaidMedia`
- Official docs: https://core.telegram.org/bots/api#sendpaidmedia
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:outbound-media`, `priority:P1`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `sendPaidMedia` в область: исходящие ответы бота за пределами plain text, включая typing/draft feedback, медиа, polls, checklist и reactions. Определить конкретный сценарий: расширение chat handler или отдельный response builder, который выбирает Telegram output по результату Claude/proxy.
- Method note: Требует отдельного решения по paid content, payload, цене и доступу к purchased_paid_media updates.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-018: `sendMediaGroup`

- Title: `telegram-api: реализовать sendMediaGroup`
- Official docs: https://core.telegram.org/bots/api#sendmediagroup
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:outbound-media`, `priority:P1`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Поддержать album responses для нескольких изображений/документов с единым caption strategy.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-019: `sendLocation`

- Title: `telegram-api: реализовать sendLocation`
- Official docs: https://core.telegram.org/bots/api#sendlocation
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:outbound-media`, `priority:P1`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `sendLocation` в область: исходящие ответы бота за пределами plain text, включая typing/draft feedback, медиа, polls, checklist и reactions. Определить конкретный сценарий: расширение chat handler или отдельный response builder, который выбирает Telegram output по результату Claude/proxy.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-020: `sendVenue`

- Title: `telegram-api: реализовать sendVenue`
- Official docs: https://core.telegram.org/bots/api#sendvenue
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:outbound-media`, `priority:P1`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `sendVenue` в область: исходящие ответы бота за пределами plain text, включая typing/draft feedback, медиа, polls, checklist и reactions. Определить конкретный сценарий: расширение chat handler или отдельный response builder, который выбирает Telegram output по результату Claude/proxy.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-021: `sendContact`

- Title: `telegram-api: реализовать sendContact`
- Official docs: https://core.telegram.org/bots/api#sendcontact
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:outbound-media`, `priority:P1`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `sendContact` в область: исходящие ответы бота за пределами plain text, включая typing/draft feedback, медиа, polls, checklist и reactions. Определить конкретный сценарий: расширение chat handler или отдельный response builder, который выбирает Telegram output по результату Claude/proxy.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-022: `sendPoll`

- Title: `telegram-api: реализовать sendPoll`
- Official docs: https://core.telegram.org/bots/api#sendpoll
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:outbound-media`, `priority:P1`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `sendPoll` в область: исходящие ответы бота за пределами plain text, включая typing/draft feedback, медиа, polls, checklist и reactions. Определить конкретный сценарий: расширение chat handler или отдельный response builder, который выбирает Telegram output по результату Claude/proxy.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-023: `sendChecklist`

- Title: `telegram-api: реализовать sendChecklist`
- Official docs: https://core.telegram.org/bots/api#sendchecklist
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:outbound-media`, `priority:P1`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `sendChecklist` в область: исходящие ответы бота за пределами plain text, включая typing/draft feedback, медиа, polls, checklist и reactions. Определить конкретный сценарий: расширение chat handler или отдельный response builder, который выбирает Telegram output по результату Claude/proxy.
- Method note: Учитывать, что метод относится к connected business account и не должен включаться в обычный чат без business-mode.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-024: `sendDice`

- Title: `telegram-api: реализовать sendDice`
- Official docs: https://core.telegram.org/bots/api#senddice
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:outbound-media`, `priority:P1`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `sendDice` в область: исходящие ответы бота за пределами plain text, включая typing/draft feedback, медиа, polls, checklist и reactions. Определить конкретный сценарий: расширение chat handler или отдельный response builder, который выбирает Telegram output по результату Claude/proxy.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-025: `sendMessageDraft`

- Title: `telegram-api: реализовать sendMessageDraft`
- Official docs: https://core.telegram.org/bots/api#sendmessagedraft
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:outbound-media`, `priority:P1`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Использовать ephemeral draft preview как альтернативу частым editMessageText во время генерации ответа.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-026: `sendChatAction`

- Title: `telegram-api: реализовать sendChatAction`
- Official docs: https://core.telegram.org/bots/api#sendchataction
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:outbound-media`, `priority:P1`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Показывать typing/upload action, пока Claude/proxy обрабатывает заметно долгий запрос.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-027: `setMessageReaction`

- Title: `telegram-api: реализовать setMessageReaction`
- Official docs: https://core.telegram.org/bots/api#setmessagereaction
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:outbound-media`, `priority:P1`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `setMessageReaction` в область: исходящие ответы бота за пределами plain text, включая typing/draft feedback, медиа, polls, checklist и reactions. Определить конкретный сценарий: расширение chat handler или отдельный response builder, который выбирает Telegram output по результату Claude/proxy.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

### Пользовательский контекст

Area label: `area:user-context`. Priority baseline: `priority:P3`
(P3: требует отдельного product/security решения).

#### BOTAPI-028: `getUserProfilePhotos`

- Title: `telegram-api: реализовать getUserProfilePhotos`
- Official docs: https://core.telegram.org/bots/api#getuserprofilephotos
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:user-context`, `priority:P3`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `getUserProfilePhotos` в область: доступ к дополнительному пользовательскому контексту и осторожные действия от имени бота в отношении статуса пользователя. Определить конкретный сценарий: явно включаемая capability с privacy notice и allowlist, без скрытого сбора профилей.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-029: `getUserProfileAudios`

- Title: `telegram-api: реализовать getUserProfileAudios`
- Official docs: https://core.telegram.org/bots/api#getuserprofileaudios
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:user-context`, `priority:P3`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `getUserProfileAudios` в область: доступ к дополнительному пользовательскому контексту и осторожные действия от имени бота в отношении статуса пользователя. Определить конкретный сценарий: явно включаемая capability с privacy notice и allowlist, без скрытого сбора профилей.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-030: `setUserEmojiStatus`

- Title: `telegram-api: реализовать setUserEmojiStatus`
- Official docs: https://core.telegram.org/bots/api#setuseremojistatus
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:user-context`, `priority:P3`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `setUserEmojiStatus` в область: доступ к дополнительному пользовательскому контексту и осторожные действия от имени бота в отношении статуса пользователя. Определить конкретный сценарий: явно включаемая capability с privacy notice и allowlist, без скрытого сбора профилей.
- Method note: Проверить ограничения Telegram Premium/business capabilities перед включением.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

### Чаты, права и модерация

Area label: `area:chat-admin`. Priority baseline: `priority:P2`
(P2: важно для групп, администрирования или интерактивности).

#### BOTAPI-031: `banChatMember`

- Title: `telegram-api: реализовать banChatMember`
- Official docs: https://core.telegram.org/bots/api#banchatmember
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:chat-admin`, `priority:P2`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `banChatMember` в область: администрирование групп/супергрупп, invite links, join requests, закрепы, права участников и metadata чатов. Определить конкретный сценарий: админские команды с проверкой прав инициатора и конфигурационным deny-by-default режимом.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-032: `unbanChatMember`

- Title: `telegram-api: реализовать unbanChatMember`
- Official docs: https://core.telegram.org/bots/api#unbanchatmember
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:chat-admin`, `priority:P2`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `unbanChatMember` в область: администрирование групп/супергрупп, invite links, join requests, закрепы, права участников и metadata чатов. Определить конкретный сценарий: админские команды с проверкой прав инициатора и конфигурационным deny-by-default режимом.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-033: `restrictChatMember`

- Title: `telegram-api: реализовать restrictChatMember`
- Official docs: https://core.telegram.org/bots/api#restrictchatmember
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:chat-admin`, `priority:P2`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `restrictChatMember` в область: администрирование групп/супергрупп, invite links, join requests, закрепы, права участников и metadata чатов. Определить конкретный сценарий: админские команды с проверкой прав инициатора и конфигурационным deny-by-default режимом.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-034: `promoteChatMember`

- Title: `telegram-api: реализовать promoteChatMember`
- Official docs: https://core.telegram.org/bots/api#promotechatmember
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:chat-admin`, `priority:P2`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `promoteChatMember` в область: администрирование групп/супергрупп, invite links, join requests, закрепы, права участников и metadata чатов. Определить конкретный сценарий: админские команды с проверкой прав инициатора и конфигурационным deny-by-default режимом.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-035: `setChatAdministratorCustomTitle`

- Title: `telegram-api: реализовать setChatAdministratorCustomTitle`
- Official docs: https://core.telegram.org/bots/api#setchatadministratorcustomtitle
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:chat-admin`, `priority:P2`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `setChatAdministratorCustomTitle` в область: администрирование групп/супергрупп, invite links, join requests, закрепы, права участников и metadata чатов. Определить конкретный сценарий: админские команды с проверкой прав инициатора и конфигурационным deny-by-default режимом.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-036: `setChatMemberTag`

- Title: `telegram-api: реализовать setChatMemberTag`
- Official docs: https://core.telegram.org/bots/api#setchatmembertag
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:chat-admin`, `priority:P2`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `setChatMemberTag` в область: администрирование групп/супергрупп, invite links, join requests, закрепы, права участников и metadata чатов. Определить конкретный сценарий: админские команды с проверкой прав инициатора и конфигурационным deny-by-default режимом.
- Method note: Новый слой tags из Bot API 9.5; требуется проверка can_manage_tags/can_edit_tag.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-037: `banChatSenderChat`

- Title: `telegram-api: реализовать banChatSenderChat`
- Official docs: https://core.telegram.org/bots/api#banchatsenderchat
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:chat-admin`, `priority:P2`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `banChatSenderChat` в область: администрирование групп/супергрупп, invite links, join requests, закрепы, права участников и metadata чатов. Определить конкретный сценарий: админские команды с проверкой прав инициатора и конфигурационным deny-by-default режимом.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-038: `unbanChatSenderChat`

- Title: `telegram-api: реализовать unbanChatSenderChat`
- Official docs: https://core.telegram.org/bots/api#unbanchatsenderchat
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:chat-admin`, `priority:P2`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `unbanChatSenderChat` в область: администрирование групп/супергрупп, invite links, join requests, закрепы, права участников и metadata чатов. Определить конкретный сценарий: админские команды с проверкой прав инициатора и конфигурационным deny-by-default режимом.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-039: `setChatPermissions`

- Title: `telegram-api: реализовать setChatPermissions`
- Official docs: https://core.telegram.org/bots/api#setchatpermissions
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:chat-admin`, `priority:P2`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `setChatPermissions` в область: администрирование групп/супергрупп, invite links, join requests, закрепы, права участников и metadata чатов. Определить конкретный сценарий: админские команды с проверкой прав инициатора и конфигурационным deny-by-default режимом.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-040: `exportChatInviteLink`

- Title: `telegram-api: реализовать exportChatInviteLink`
- Official docs: https://core.telegram.org/bots/api#exportchatinvitelink
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:chat-admin`, `priority:P2`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `exportChatInviteLink` в область: администрирование групп/супергрупп, invite links, join requests, закрепы, права участников и metadata чатов. Определить конкретный сценарий: админские команды с проверкой прав инициатора и конфигурационным deny-by-default режимом.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-041: `createChatInviteLink`

- Title: `telegram-api: реализовать createChatInviteLink`
- Official docs: https://core.telegram.org/bots/api#createchatinvitelink
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:chat-admin`, `priority:P2`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `createChatInviteLink` в область: администрирование групп/супергрупп, invite links, join requests, закрепы, права участников и metadata чатов. Определить конкретный сценарий: админские команды с проверкой прав инициатора и конфигурационным deny-by-default режимом.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-042: `editChatInviteLink`

- Title: `telegram-api: реализовать editChatInviteLink`
- Official docs: https://core.telegram.org/bots/api#editchatinvitelink
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:chat-admin`, `priority:P2`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `editChatInviteLink` в область: администрирование групп/супергрупп, invite links, join requests, закрепы, права участников и metadata чатов. Определить конкретный сценарий: админские команды с проверкой прав инициатора и конфигурационным deny-by-default режимом.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-043: `createChatSubscriptionInviteLink`

- Title: `telegram-api: реализовать createChatSubscriptionInviteLink`
- Official docs: https://core.telegram.org/bots/api#createchatsubscriptioninvitelink
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:chat-admin`, `priority:P2`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `createChatSubscriptionInviteLink` в область: администрирование групп/супергрупп, invite links, join requests, закрепы, права участников и metadata чатов. Определить конкретный сценарий: админские команды с проверкой прав инициатора и конфигурационным deny-by-default режимом.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-044: `editChatSubscriptionInviteLink`

- Title: `telegram-api: реализовать editChatSubscriptionInviteLink`
- Official docs: https://core.telegram.org/bots/api#editchatsubscriptioninvitelink
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:chat-admin`, `priority:P2`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `editChatSubscriptionInviteLink` в область: администрирование групп/супергрупп, invite links, join requests, закрепы, права участников и metadata чатов. Определить конкретный сценарий: админские команды с проверкой прав инициатора и конфигурационным deny-by-default режимом.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-045: `revokeChatInviteLink`

- Title: `telegram-api: реализовать revokeChatInviteLink`
- Official docs: https://core.telegram.org/bots/api#revokechatinvitelink
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:chat-admin`, `priority:P2`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `revokeChatInviteLink` в область: администрирование групп/супергрупп, invite links, join requests, закрепы, права участников и metadata чатов. Определить конкретный сценарий: админские команды с проверкой прав инициатора и конфигурационным deny-by-default режимом.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-046: `approveChatJoinRequest`

- Title: `telegram-api: реализовать approveChatJoinRequest`
- Official docs: https://core.telegram.org/bots/api#approvechatjoinrequest
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:chat-admin`, `priority:P2`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `approveChatJoinRequest` в область: администрирование групп/супергрупп, invite links, join requests, закрепы, права участников и metadata чатов. Определить конкретный сценарий: админские команды с проверкой прав инициатора и конфигурационным deny-by-default режимом.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-047: `declineChatJoinRequest`

- Title: `telegram-api: реализовать declineChatJoinRequest`
- Official docs: https://core.telegram.org/bots/api#declinechatjoinrequest
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:chat-admin`, `priority:P2`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `declineChatJoinRequest` в область: администрирование групп/супергрупп, invite links, join requests, закрепы, права участников и metadata чатов. Определить конкретный сценарий: админские команды с проверкой прав инициатора и конфигурационным deny-by-default режимом.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-048: `setChatPhoto`

- Title: `telegram-api: реализовать setChatPhoto`
- Official docs: https://core.telegram.org/bots/api#setchatphoto
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:chat-admin`, `priority:P2`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `setChatPhoto` в область: администрирование групп/супергрупп, invite links, join requests, закрепы, права участников и metadata чатов. Определить конкретный сценарий: админские команды с проверкой прав инициатора и конфигурационным deny-by-default режимом.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-049: `deleteChatPhoto`

- Title: `telegram-api: реализовать deleteChatPhoto`
- Official docs: https://core.telegram.org/bots/api#deletechatphoto
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:chat-admin`, `priority:P2`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `deleteChatPhoto` в область: администрирование групп/супергрупп, invite links, join requests, закрепы, права участников и metadata чатов. Определить конкретный сценарий: админские команды с проверкой прав инициатора и конфигурационным deny-by-default режимом.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-050: `setChatTitle`

- Title: `telegram-api: реализовать setChatTitle`
- Official docs: https://core.telegram.org/bots/api#setchattitle
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:chat-admin`, `priority:P2`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `setChatTitle` в область: администрирование групп/супергрупп, invite links, join requests, закрепы, права участников и metadata чатов. Определить конкретный сценарий: админские команды с проверкой прав инициатора и конфигурационным deny-by-default режимом.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-051: `setChatDescription`

- Title: `telegram-api: реализовать setChatDescription`
- Official docs: https://core.telegram.org/bots/api#setchatdescription
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:chat-admin`, `priority:P2`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `setChatDescription` в область: администрирование групп/супергрупп, invite links, join requests, закрепы, права участников и metadata чатов. Определить конкретный сценарий: админские команды с проверкой прав инициатора и конфигурационным deny-by-default режимом.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-052: `pinChatMessage`

- Title: `telegram-api: реализовать pinChatMessage`
- Official docs: https://core.telegram.org/bots/api#pinchatmessage
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:chat-admin`, `priority:P2`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `pinChatMessage` в область: администрирование групп/супергрупп, invite links, join requests, закрепы, права участников и metadata чатов. Определить конкретный сценарий: админские команды с проверкой прав инициатора и конфигурационным deny-by-default режимом.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-053: `unpinChatMessage`

- Title: `telegram-api: реализовать unpinChatMessage`
- Official docs: https://core.telegram.org/bots/api#unpinchatmessage
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:chat-admin`, `priority:P2`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `unpinChatMessage` в область: администрирование групп/супергрупп, invite links, join requests, закрепы, права участников и metadata чатов. Определить конкретный сценарий: админские команды с проверкой прав инициатора и конфигурационным deny-by-default режимом.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-054: `unpinAllChatMessages`

- Title: `telegram-api: реализовать unpinAllChatMessages`
- Official docs: https://core.telegram.org/bots/api#unpinallchatmessages
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:chat-admin`, `priority:P2`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `unpinAllChatMessages` в область: администрирование групп/супергрупп, invite links, join requests, закрепы, права участников и metadata чатов. Определить конкретный сценарий: админские команды с проверкой прав инициатора и конфигурационным deny-by-default режимом.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-055: `leaveChat`

- Title: `telegram-api: реализовать leaveChat`
- Official docs: https://core.telegram.org/bots/api#leavechat
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:chat-admin`, `priority:P2`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `leaveChat` в область: администрирование групп/супергрупп, invite links, join requests, закрепы, права участников и metadata чатов. Определить конкретный сценарий: админские команды с проверкой прав инициатора и конфигурационным deny-by-default режимом.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-056: `getChat`

- Title: `telegram-api: реализовать getChat`
- Official docs: https://core.telegram.org/bots/api#getchat
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:chat-admin`, `priority:P2`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `getChat` в область: администрирование групп/супергрупп, invite links, join requests, закрепы, права участников и metadata чатов. Определить конкретный сценарий: админские команды с проверкой прав инициатора и конфигурационным deny-by-default режимом.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-057: `getChatAdministrators`

- Title: `telegram-api: реализовать getChatAdministrators`
- Official docs: https://core.telegram.org/bots/api#getchatadministrators
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:chat-admin`, `priority:P2`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `getChatAdministrators` в область: администрирование групп/супергрупп, invite links, join requests, закрепы, права участников и metadata чатов. Определить конкретный сценарий: админские команды с проверкой прав инициатора и конфигурационным deny-by-default режимом.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-058: `getChatMemberCount`

- Title: `telegram-api: реализовать getChatMemberCount`
- Official docs: https://core.telegram.org/bots/api#getchatmembercount
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:chat-admin`, `priority:P2`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `getChatMemberCount` в область: администрирование групп/супергрупп, invite links, join requests, закрепы, права участников и metadata чатов. Определить конкретный сценарий: админские команды с проверкой прав инициатора и конфигурационным deny-by-default режимом.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-059: `getChatMember`

- Title: `telegram-api: реализовать getChatMember`
- Official docs: https://core.telegram.org/bots/api#getchatmember
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:chat-admin`, `priority:P2`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `getChatMember` в область: администрирование групп/супергрупп, invite links, join requests, закрепы, права участников и metadata чатов. Определить конкретный сценарий: админские команды с проверкой прав инициатора и конфигурационным deny-by-default режимом.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-060: `getUserPersonalChatMessages`

- Title: `telegram-api: реализовать getUserPersonalChatMessages`
- Official docs: https://core.telegram.org/bots/api#getuserpersonalchatmessages
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:chat-admin`, `priority:P2`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `getUserPersonalChatMessages` в область: администрирование групп/супергрупп, invite links, join requests, закрепы, права участников и metadata чатов. Определить конкретный сценарий: админские команды с проверкой прав инициатора и конфигурационным deny-by-default режимом.
- Method note: Новый метод Bot API 10.0; проверить privacy expectations и хранение полученных сообщений.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-061: `setChatStickerSet`

- Title: `telegram-api: реализовать setChatStickerSet`
- Official docs: https://core.telegram.org/bots/api#setchatstickerset
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:chat-admin`, `priority:P2`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `setChatStickerSet` в область: администрирование групп/супергрупп, invite links, join requests, закрепы, права участников и metadata чатов. Определить конкретный сценарий: админские команды с проверкой прав инициатора и конфигурационным deny-by-default режимом.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-062: `deleteChatStickerSet`

- Title: `telegram-api: реализовать deleteChatStickerSet`
- Official docs: https://core.telegram.org/bots/api#deletechatstickerset
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:chat-admin`, `priority:P2`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `deleteChatStickerSet` в область: администрирование групп/супергрупп, invite links, join requests, закрепы, права участников и metadata чатов. Определить конкретный сценарий: админские команды с проверкой прав инициатора и конфигурационным deny-by-default режимом.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

### Forum topics

Area label: `area:forum-topics`. Priority baseline: `priority:P2`
(P2: важно для групп, администрирования или интерактивности).

#### BOTAPI-063: `getForumTopicIconStickers`

- Title: `telegram-api: реализовать getForumTopicIconStickers`
- Official docs: https://core.telegram.org/bots/api#getforumtopiciconstickers
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:forum-topics`, `priority:P2`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `getForumTopicIconStickers` в область: управление forum topics и general topic в супергруппах, где бот имеет админские права. Определить конкретный сценарий: команды модератора или автоматизация triage тем, отделенная от обычного Claude-чата.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-064: `createForumTopic`

- Title: `telegram-api: реализовать createForumTopic`
- Official docs: https://core.telegram.org/bots/api#createforumtopic
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:forum-topics`, `priority:P2`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `createForumTopic` в область: управление forum topics и general topic в супергруппах, где бот имеет админские права. Определить конкретный сценарий: команды модератора или автоматизация triage тем, отделенная от обычного Claude-чата.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-065: `editForumTopic`

- Title: `telegram-api: реализовать editForumTopic`
- Official docs: https://core.telegram.org/bots/api#editforumtopic
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:forum-topics`, `priority:P2`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `editForumTopic` в область: управление forum topics и general topic в супергруппах, где бот имеет админские права. Определить конкретный сценарий: команды модератора или автоматизация triage тем, отделенная от обычного Claude-чата.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-066: `closeForumTopic`

- Title: `telegram-api: реализовать closeForumTopic`
- Official docs: https://core.telegram.org/bots/api#closeforumtopic
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:forum-topics`, `priority:P2`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `closeForumTopic` в область: управление forum topics и general topic в супергруппах, где бот имеет админские права. Определить конкретный сценарий: команды модератора или автоматизация triage тем, отделенная от обычного Claude-чата.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-067: `reopenForumTopic`

- Title: `telegram-api: реализовать reopenForumTopic`
- Official docs: https://core.telegram.org/bots/api#reopenforumtopic
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:forum-topics`, `priority:P2`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `reopenForumTopic` в область: управление forum topics и general topic в супергруппах, где бот имеет админские права. Определить конкретный сценарий: команды модератора или автоматизация triage тем, отделенная от обычного Claude-чата.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-068: `deleteForumTopic`

- Title: `telegram-api: реализовать deleteForumTopic`
- Official docs: https://core.telegram.org/bots/api#deleteforumtopic
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:forum-topics`, `priority:P2`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `deleteForumTopic` в область: управление forum topics и general topic в супергруппах, где бот имеет админские права. Определить конкретный сценарий: команды модератора или автоматизация triage тем, отделенная от обычного Claude-чата.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-069: `unpinAllForumTopicMessages`

- Title: `telegram-api: реализовать unpinAllForumTopicMessages`
- Official docs: https://core.telegram.org/bots/api#unpinallforumtopicmessages
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:forum-topics`, `priority:P2`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `unpinAllForumTopicMessages` в область: управление forum topics и general topic в супергруппах, где бот имеет админские права. Определить конкретный сценарий: команды модератора или автоматизация triage тем, отделенная от обычного Claude-чата.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-070: `editGeneralForumTopic`

- Title: `telegram-api: реализовать editGeneralForumTopic`
- Official docs: https://core.telegram.org/bots/api#editgeneralforumtopic
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:forum-topics`, `priority:P2`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `editGeneralForumTopic` в область: управление forum topics и general topic в супергруппах, где бот имеет админские права. Определить конкретный сценарий: команды модератора или автоматизация triage тем, отделенная от обычного Claude-чата.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-071: `closeGeneralForumTopic`

- Title: `telegram-api: реализовать closeGeneralForumTopic`
- Official docs: https://core.telegram.org/bots/api#closegeneralforumtopic
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:forum-topics`, `priority:P2`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `closeGeneralForumTopic` в область: управление forum topics и general topic в супергруппах, где бот имеет админские права. Определить конкретный сценарий: команды модератора или автоматизация triage тем, отделенная от обычного Claude-чата.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-072: `reopenGeneralForumTopic`

- Title: `telegram-api: реализовать reopenGeneralForumTopic`
- Official docs: https://core.telegram.org/bots/api#reopengeneralforumtopic
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:forum-topics`, `priority:P2`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `reopenGeneralForumTopic` в область: управление forum topics и general topic в супергруппах, где бот имеет админские права. Определить конкретный сценарий: команды модератора или автоматизация triage тем, отделенная от обычного Claude-чата.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-073: `hideGeneralForumTopic`

- Title: `telegram-api: реализовать hideGeneralForumTopic`
- Official docs: https://core.telegram.org/bots/api#hidegeneralforumtopic
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:forum-topics`, `priority:P2`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `hideGeneralForumTopic` в область: управление forum topics и general topic в супергруппах, где бот имеет админские права. Определить конкретный сценарий: команды модератора или автоматизация triage тем, отделенная от обычного Claude-чата.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-074: `unhideGeneralForumTopic`

- Title: `telegram-api: реализовать unhideGeneralForumTopic`
- Official docs: https://core.telegram.org/bots/api#unhidegeneralforumtopic
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:forum-topics`, `priority:P2`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `unhideGeneralForumTopic` в область: управление forum topics и general topic в супергруппах, где бот имеет админские права. Определить конкретный сценарий: команды модератора или автоматизация triage тем, отделенная от обычного Claude-чата.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-075: `unpinAllGeneralForumTopicMessages`

- Title: `telegram-api: реализовать unpinAllGeneralForumTopicMessages`
- Official docs: https://core.telegram.org/bots/api#unpinallgeneralforumtopicmessages
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:forum-topics`, `priority:P2`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `unpinAllGeneralForumTopicMessages` в область: управление forum topics и general topic в супергруппах, где бот имеет админские права. Определить конкретный сценарий: команды модератора или автоматизация triage тем, отделенная от обычного Claude-чата.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

### Интерактивность, Guest Mode и boosts

Area label: `area:interactive`. Priority baseline: `priority:P0`
(P0: фундаментальный метод для следующего слоя Telegram API).

#### BOTAPI-076: `answerCallbackQuery`

- Title: `telegram-api: реализовать answerCallbackQuery`
- Official docs: https://core.telegram.org/bots/api#answercallbackquery
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:interactive`, `priority:P0`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить callback_query handlers для inline keyboards настроек, модели, очистки истории и подтверждений admin-действий.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-077: `answerGuestQuery`

- Title: `telegram-api: реализовать answerGuestQuery`
- Official docs: https://core.telegram.org/bots/api#answerguestquery
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:interactive`, `priority:P0`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Реализовать официальный Guest Mode: принимать guest_message, использовать Message.guest_query_id и отвечать через answerGuestQuery без членства бота в чате.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-078: `getUserChatBoosts`

- Title: `telegram-api: реализовать getUserChatBoosts`
- Official docs: https://core.telegram.org/bots/api#getuserchatboosts
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:interactive`, `priority:P0`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `getUserChatBoosts` в область: inline keyboards/callbacks, официальный Telegram Guest Mode и чтение chat boost контекста. Определить конкретный сценарий: handler для callback/guest/boost flows с понятной связью с настройками модели и group privacy.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

### Business connection и managed bots

Area label: `area:managed-bots`. Priority baseline: `priority:P3`
(P3: требует отдельного product/security решения).

#### BOTAPI-079: `getBusinessConnection`

- Title: `telegram-api: реализовать getBusinessConnection`
- Official docs: https://core.telegram.org/bots/api#getbusinessconnection
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:managed-bots`, `priority:P3`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `getBusinessConnection` в область: интеграцию business connection и управляемых ботов с учетом token lifecycle и прав владельца. Определить конкретный сценарий: отдельный защищенный admin surface; по умолчанию выключено из-за чувствительности токенов.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-080: `getManagedBotToken`

- Title: `telegram-api: реализовать getManagedBotToken`
- Official docs: https://core.telegram.org/bots/api#getmanagedbottoken
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:managed-bots`, `priority:P3`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `getManagedBotToken` в область: интеграцию business connection и управляемых ботов с учетом token lifecycle и прав владельца. Определить конкретный сценарий: отдельный защищенный admin surface; по умолчанию выключено из-за чувствительности токенов.
- Method note: Чувствительный token-returning метод; запрещать логирование результата.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-081: `replaceManagedBotToken`

- Title: `telegram-api: реализовать replaceManagedBotToken`
- Official docs: https://core.telegram.org/bots/api#replacemanagedbottoken
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:managed-bots`, `priority:P3`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `replaceManagedBotToken` в область: интеграцию business connection и управляемых ботов с учетом token lifecycle и прав владельца. Определить конкретный сценарий: отдельный защищенный admin surface; по умолчанию выключено из-за чувствительности токенов.
- Method note: Чувствительный token rotation; нужен explicit confirmation и secret storage plan.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-082: `getManagedBotAccessSettings`

- Title: `telegram-api: реализовать getManagedBotAccessSettings`
- Official docs: https://core.telegram.org/bots/api#getmanagedbotaccesssettings
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:managed-bots`, `priority:P3`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `getManagedBotAccessSettings` в область: интеграцию business connection и управляемых ботов с учетом token lifecycle и прав владельца. Определить конкретный сценарий: отдельный защищенный admin surface; по умолчанию выключено из-за чувствительности токенов.
- Method note: Новый метод Bot API 10.0; изолировать от обычного bot token lifecycle.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-083: `setManagedBotAccessSettings`

- Title: `telegram-api: реализовать setManagedBotAccessSettings`
- Official docs: https://core.telegram.org/bots/api#setmanagedbotaccesssettings
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:managed-bots`, `priority:P3`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `setManagedBotAccessSettings` в область: интеграцию business connection и управляемых ботов с учетом token lifecycle и прав владельца. Определить конкретный сценарий: отдельный защищенный admin surface; по умолчанию выключено из-за чувствительности токенов.
- Method note: Новый метод Bot API 10.0; требуются строгие admin checks и rollback plan.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

### Команды, профиль и default права бота

Area label: `area:bot-profile`. Priority baseline: `priority:P1`
(P1: высокий пользовательский эффект для Claude-бота).

#### BOTAPI-084: `setMyCommands`

- Title: `telegram-api: реализовать setMyCommands`
- Official docs: https://core.telegram.org/bots/api#setmycommands
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:bot-profile`, `priority:P1`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Синхронизировать команды /start, /help, /model, /settings, /clear и будущие admin-команды при startup или admin sync.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-085: `deleteMyCommands`

- Title: `telegram-api: реализовать deleteMyCommands`
- Official docs: https://core.telegram.org/bots/api#deletemycommands
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:bot-profile`, `priority:P1`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить безопасную очистку command menu по scope/language перед повторной синхронизацией.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-086: `getMyCommands`

- Title: `telegram-api: реализовать getMyCommands`
- Official docs: https://core.telegram.org/bots/api#getmycommands
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:bot-profile`, `priority:P1`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить проверку фактического command menu и диагностику расхождения с ожидаемой конфигурацией.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-087: `setMyName`

- Title: `telegram-api: реализовать setMyName`
- Official docs: https://core.telegram.org/bots/api#setmyname
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:bot-profile`, `priority:P1`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Управлять локализуемым именем бота через конфигурацию и admin sync.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-088: `getMyName`

- Title: `telegram-api: реализовать getMyName`
- Official docs: https://core.telegram.org/bots/api#getmyname
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:bot-profile`, `priority:P1`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `getMyName` в область: управление публичным профилем бота, командами, menu button и default administrator rights. Определить конкретный сценарий: startup sync и admin-only commands, чтобы BotFather-настройки были воспроизводимы из репозитория.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-089: `setMyDescription`

- Title: `telegram-api: реализовать setMyDescription`
- Official docs: https://core.telegram.org/bots/api#setmydescription
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:bot-profile`, `priority:P1`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Управлять публичным описанием бота из репозитория, чтобы оно соответствовало текущей функциональности.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-090: `getMyDescription`

- Title: `telegram-api: реализовать getMyDescription`
- Official docs: https://core.telegram.org/bots/api#getmydescription
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:bot-profile`, `priority:P1`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `getMyDescription` в область: управление публичным профилем бота, командами, menu button и default administrator rights. Определить конкретный сценарий: startup sync и admin-only commands, чтобы BotFather-настройки были воспроизводимы из репозитория.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-091: `setMyShortDescription`

- Title: `telegram-api: реализовать setMyShortDescription`
- Official docs: https://core.telegram.org/bots/api#setmyshortdescription
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:bot-profile`, `priority:P1`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Управлять коротким описанием бота для карточек/поиска Telegram.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-092: `getMyShortDescription`

- Title: `telegram-api: реализовать getMyShortDescription`
- Official docs: https://core.telegram.org/bots/api#getmyshortdescription
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:bot-profile`, `priority:P1`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `getMyShortDescription` в область: управление публичным профилем бота, командами, menu button и default administrator rights. Определить конкретный сценарий: startup sync и admin-only commands, чтобы BotFather-настройки были воспроизводимы из репозитория.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-093: `setMyProfilePhoto`

- Title: `telegram-api: реализовать setMyProfilePhoto`
- Official docs: https://core.telegram.org/bots/api#setmyprofilephoto
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:bot-profile`, `priority:P1`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить воспроизводимое обновление profile photo из файла/asset с проверкой формата.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-094: `removeMyProfilePhoto`

- Title: `telegram-api: реализовать removeMyProfilePhoto`
- Official docs: https://core.telegram.org/bots/api#removemyprofilephoto
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:bot-profile`, `priority:P1`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить rollback для profile photo и документировать ограничения Bot API.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-095: `setChatMenuButton`

- Title: `telegram-api: реализовать setChatMenuButton`
- Official docs: https://core.telegram.org/bots/api#setchatmenubutton
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:bot-profile`, `priority:P1`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `setChatMenuButton` в область: управление публичным профилем бота, командами, menu button и default administrator rights. Определить конкретный сценарий: startup sync и admin-only commands, чтобы BotFather-настройки были воспроизводимы из репозитория.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-096: `getChatMenuButton`

- Title: `telegram-api: реализовать getChatMenuButton`
- Official docs: https://core.telegram.org/bots/api#getchatmenubutton
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:bot-profile`, `priority:P1`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `getChatMenuButton` в область: управление публичным профилем бота, командами, menu button и default administrator rights. Определить конкретный сценарий: startup sync и admin-only commands, чтобы BotFather-настройки были воспроизводимы из репозитория.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-097: `setMyDefaultAdministratorRights`

- Title: `telegram-api: реализовать setMyDefaultAdministratorRights`
- Official docs: https://core.telegram.org/bots/api#setmydefaultadministratorrights
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:bot-profile`, `priority:P1`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `setMyDefaultAdministratorRights` в область: управление публичным профилем бота, командами, menu button и default administrator rights. Определить конкретный сценарий: startup sync и admin-only commands, чтобы BotFather-настройки были воспроизводимы из репозитория.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-098: `getMyDefaultAdministratorRights`

- Title: `telegram-api: реализовать getMyDefaultAdministratorRights`
- Official docs: https://core.telegram.org/bots/api#getmydefaultadministratorrights
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:bot-profile`, `priority:P1`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `getMyDefaultAdministratorRights` в область: управление публичным профилем бота, командами, menu button и default administrator rights. Определить конкретный сценарий: startup sync и admin-only commands, чтобы BotFather-настройки были воспроизводимы из репозитория.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

### Gifts, verification и premium-сценарии

Area label: `area:gifts-verification`. Priority baseline: `priority:P3`
(P3: требует отдельного product/security решения).

#### BOTAPI-099: `getAvailableGifts`

- Title: `telegram-api: реализовать getAvailableGifts`
- Official docs: https://core.telegram.org/bots/api#getavailablegifts
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:gifts-verification`, `priority:P3`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `getAvailableGifts` в область: подарки, Premium gifts и verification actions, где нужны отдельные product rules и audit log. Определить конкретный сценарий: админский billing/rewards flow с явным подтверждением расходов и действий верификации.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-100: `sendGift`

- Title: `telegram-api: реализовать sendGift`
- Official docs: https://core.telegram.org/bots/api#sendgift
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:gifts-verification`, `priority:P3`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `sendGift` в область: подарки, Premium gifts и verification actions, где нужны отдельные product rules и audit log. Определить конкретный сценарий: админский billing/rewards flow с явным подтверждением расходов и действий верификации.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-101: `giftPremiumSubscription`

- Title: `telegram-api: реализовать giftPremiumSubscription`
- Official docs: https://core.telegram.org/bots/api#giftpremiumsubscription
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:gifts-verification`, `priority:P3`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `giftPremiumSubscription` в область: подарки, Premium gifts и verification actions, где нужны отдельные product rules и audit log. Определить конкретный сценарий: админский billing/rewards flow с явным подтверждением расходов и действий верификации.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-102: `verifyUser`

- Title: `telegram-api: реализовать verifyUser`
- Official docs: https://core.telegram.org/bots/api#verifyuser
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:gifts-verification`, `priority:P3`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `verifyUser` в область: подарки, Premium gifts и verification actions, где нужны отдельные product rules и audit log. Определить конкретный сценарий: админский billing/rewards flow с явным подтверждением расходов и действий верификации.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-103: `verifyChat`

- Title: `telegram-api: реализовать verifyChat`
- Official docs: https://core.telegram.org/bots/api#verifychat
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:gifts-verification`, `priority:P3`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `verifyChat` в область: подарки, Premium gifts и verification actions, где нужны отдельные product rules и audit log. Определить конкретный сценарий: админский billing/rewards flow с явным подтверждением расходов и действий верификации.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-104: `removeUserVerification`

- Title: `telegram-api: реализовать removeUserVerification`
- Official docs: https://core.telegram.org/bots/api#removeuserverification
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:gifts-verification`, `priority:P3`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `removeUserVerification` в область: подарки, Premium gifts и verification actions, где нужны отдельные product rules и audit log. Определить конкретный сценарий: админский billing/rewards flow с явным подтверждением расходов и действий верификации.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-105: `removeChatVerification`

- Title: `telegram-api: реализовать removeChatVerification`
- Official docs: https://core.telegram.org/bots/api#removechatverification
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:gifts-verification`, `priority:P3`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `removeChatVerification` в область: подарки, Premium gifts и verification actions, где нужны отдельные product rules и audit log. Определить конкретный сценарий: админский billing/rewards flow с явным подтверждением расходов и действий верификации.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

### Business account actions, gifts и Stars

Area label: `area:business-account`. Priority baseline: `priority:P3`
(P3: требует отдельного product/security решения).

#### BOTAPI-106: `readBusinessMessage`

- Title: `telegram-api: реализовать readBusinessMessage`
- Official docs: https://core.telegram.org/bots/api#readbusinessmessage
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:business-account`, `priority:P3`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `readBusinessMessage` в область: управление подключенным business account, его сообщениями, профилем, gifts и star balance. Определить конкретный сценарий: строго изолированный business-mode модуль с журналом действий и проверкой connection ownership.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-107: `deleteBusinessMessages`

- Title: `telegram-api: реализовать deleteBusinessMessages`
- Official docs: https://core.telegram.org/bots/api#deletebusinessmessages
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:business-account`, `priority:P3`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `deleteBusinessMessages` в область: управление подключенным business account, его сообщениями, профилем, gifts и star balance. Определить конкретный сценарий: строго изолированный business-mode модуль с журналом действий и проверкой connection ownership.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-108: `setBusinessAccountName`

- Title: `telegram-api: реализовать setBusinessAccountName`
- Official docs: https://core.telegram.org/bots/api#setbusinessaccountname
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:business-account`, `priority:P3`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `setBusinessAccountName` в область: управление подключенным business account, его сообщениями, профилем, gifts и star balance. Определить конкретный сценарий: строго изолированный business-mode модуль с журналом действий и проверкой connection ownership.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-109: `setBusinessAccountUsername`

- Title: `telegram-api: реализовать setBusinessAccountUsername`
- Official docs: https://core.telegram.org/bots/api#setbusinessaccountusername
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:business-account`, `priority:P3`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `setBusinessAccountUsername` в область: управление подключенным business account, его сообщениями, профилем, gifts и star balance. Определить конкретный сценарий: строго изолированный business-mode модуль с журналом действий и проверкой connection ownership.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-110: `setBusinessAccountBio`

- Title: `telegram-api: реализовать setBusinessAccountBio`
- Official docs: https://core.telegram.org/bots/api#setbusinessaccountbio
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:business-account`, `priority:P3`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `setBusinessAccountBio` в область: управление подключенным business account, его сообщениями, профилем, gifts и star balance. Определить конкретный сценарий: строго изолированный business-mode модуль с журналом действий и проверкой connection ownership.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-111: `setBusinessAccountProfilePhoto`

- Title: `telegram-api: реализовать setBusinessAccountProfilePhoto`
- Official docs: https://core.telegram.org/bots/api#setbusinessaccountprofilephoto
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:business-account`, `priority:P3`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `setBusinessAccountProfilePhoto` в область: управление подключенным business account, его сообщениями, профилем, gifts и star balance. Определить конкретный сценарий: строго изолированный business-mode модуль с журналом действий и проверкой connection ownership.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-112: `removeBusinessAccountProfilePhoto`

- Title: `telegram-api: реализовать removeBusinessAccountProfilePhoto`
- Official docs: https://core.telegram.org/bots/api#removebusinessaccountprofilephoto
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:business-account`, `priority:P3`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `removeBusinessAccountProfilePhoto` в область: управление подключенным business account, его сообщениями, профилем, gifts и star balance. Определить конкретный сценарий: строго изолированный business-mode модуль с журналом действий и проверкой connection ownership.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-113: `setBusinessAccountGiftSettings`

- Title: `telegram-api: реализовать setBusinessAccountGiftSettings`
- Official docs: https://core.telegram.org/bots/api#setbusinessaccountgiftsettings
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:business-account`, `priority:P3`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `setBusinessAccountGiftSettings` в область: управление подключенным business account, его сообщениями, профилем, gifts и star balance. Определить конкретный сценарий: строго изолированный business-mode модуль с журналом действий и проверкой connection ownership.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-114: `getBusinessAccountStarBalance`

- Title: `telegram-api: реализовать getBusinessAccountStarBalance`
- Official docs: https://core.telegram.org/bots/api#getbusinessaccountstarbalance
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:business-account`, `priority:P3`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `getBusinessAccountStarBalance` в область: управление подключенным business account, его сообщениями, профилем, gifts и star balance. Определить конкретный сценарий: строго изолированный business-mode модуль с журналом действий и проверкой connection ownership.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-115: `transferBusinessAccountStars`

- Title: `telegram-api: реализовать transferBusinessAccountStars`
- Official docs: https://core.telegram.org/bots/api#transferbusinessaccountstars
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:business-account`, `priority:P3`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `transferBusinessAccountStars` в область: управление подключенным business account, его сообщениями, профилем, gifts и star balance. Определить конкретный сценарий: строго изолированный business-mode модуль с журналом действий и проверкой connection ownership.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-116: `getBusinessAccountGifts`

- Title: `telegram-api: реализовать getBusinessAccountGifts`
- Official docs: https://core.telegram.org/bots/api#getbusinessaccountgifts
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:business-account`, `priority:P3`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `getBusinessAccountGifts` в область: управление подключенным business account, его сообщениями, профилем, gifts и star balance. Определить конкретный сценарий: строго изолированный business-mode модуль с журналом действий и проверкой connection ownership.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-117: `getUserGifts`

- Title: `telegram-api: реализовать getUserGifts`
- Official docs: https://core.telegram.org/bots/api#getusergifts
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:business-account`, `priority:P3`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `getUserGifts` в область: управление подключенным business account, его сообщениями, профилем, gifts и star balance. Определить конкретный сценарий: строго изолированный business-mode модуль с журналом действий и проверкой connection ownership.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-118: `getChatGifts`

- Title: `telegram-api: реализовать getChatGifts`
- Official docs: https://core.telegram.org/bots/api#getchatgifts
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:business-account`, `priority:P3`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `getChatGifts` в область: управление подключенным business account, его сообщениями, профилем, gifts и star balance. Определить конкретный сценарий: строго изолированный business-mode модуль с журналом действий и проверкой connection ownership.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-119: `convertGiftToStars`

- Title: `telegram-api: реализовать convertGiftToStars`
- Official docs: https://core.telegram.org/bots/api#convertgifttostars
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:business-account`, `priority:P3`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `convertGiftToStars` в область: управление подключенным business account, его сообщениями, профилем, gifts и star balance. Определить конкретный сценарий: строго изолированный business-mode модуль с журналом действий и проверкой connection ownership.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-120: `upgradeGift`

- Title: `telegram-api: реализовать upgradeGift`
- Official docs: https://core.telegram.org/bots/api#upgradegift
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:business-account`, `priority:P3`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `upgradeGift` в область: управление подключенным business account, его сообщениями, профилем, gifts и star balance. Определить конкретный сценарий: строго изолированный business-mode модуль с журналом действий и проверкой connection ownership.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-121: `transferGift`

- Title: `telegram-api: реализовать transferGift`
- Official docs: https://core.telegram.org/bots/api#transfergift
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:business-account`, `priority:P3`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `transferGift` в область: управление подключенным business account, его сообщениями, профилем, gifts и star balance. Определить конкретный сценарий: строго изолированный business-mode модуль с журналом действий и проверкой connection ownership.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

### Stories

Area label: `area:stories`. Priority baseline: `priority:P4`
(P4: нишевая или domain-specific возможность).

#### BOTAPI-122: `postStory`

- Title: `telegram-api: реализовать postStory`
- Official docs: https://core.telegram.org/bots/api#poststory
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:stories`, `priority:P4`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `postStory` в область: публикацию и управление stories через business/бот capabilities. Определить конкретный сценарий: отдельный content publishing flow, не смешанный с ответами Claude в чате.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-123: `repostStory`

- Title: `telegram-api: реализовать repostStory`
- Official docs: https://core.telegram.org/bots/api#repoststory
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:stories`, `priority:P4`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `repostStory` в область: публикацию и управление stories через business/бот capabilities. Определить конкретный сценарий: отдельный content publishing flow, не смешанный с ответами Claude в чате.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-124: `editStory`

- Title: `telegram-api: реализовать editStory`
- Official docs: https://core.telegram.org/bots/api#editstory
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:stories`, `priority:P4`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `editStory` в область: публикацию и управление stories через business/бот capabilities. Определить конкретный сценарий: отдельный content publishing flow, не смешанный с ответами Claude в чате.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-125: `deleteStory`

- Title: `telegram-api: реализовать deleteStory`
- Official docs: https://core.telegram.org/bots/api#deletestory
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:stories`, `priority:P4`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `deleteStory` в область: публикацию и управление stories через business/бот capabilities. Определить конкретный сценарий: отдельный content publishing flow, не смешанный с ответами Claude в чате.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

### Web Apps и prepared messages/buttons

Area label: `area:webapp`. Priority baseline: `priority:P2`
(P2: важно для групп, администрирования или интерактивности).

#### BOTAPI-126: `answerWebAppQuery`

- Title: `telegram-api: реализовать answerWebAppQuery`
- Official docs: https://core.telegram.org/bots/api#answerwebappquery
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:webapp`, `priority:P2`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `answerWebAppQuery` в область: связку Telegram Web Apps, prepared inline messages и prepared keyboard buttons. Определить конкретный сценарий: Mini App integration layer с проверкой init data и отдельными тестами подписи/авторизации.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-127: `savePreparedInlineMessage`

- Title: `telegram-api: реализовать savePreparedInlineMessage`
- Official docs: https://core.telegram.org/bots/api#savepreparedinlinemessage
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:webapp`, `priority:P2`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `savePreparedInlineMessage` в область: связку Telegram Web Apps, prepared inline messages и prepared keyboard buttons. Определить конкретный сценарий: Mini App integration layer с проверкой init data и отдельными тестами подписи/авторизации.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-128: `savePreparedKeyboardButton`

- Title: `telegram-api: реализовать savePreparedKeyboardButton`
- Official docs: https://core.telegram.org/bots/api#savepreparedkeyboardbutton
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:webapp`, `priority:P2`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `savePreparedKeyboardButton` в область: связку Telegram Web Apps, prepared inline messages и prepared keyboard buttons. Определить конкретный сценарий: Mini App integration layer с проверкой init data и отдельными тестами подписи/авторизации.
- Method note: Bot API 9.6; связан с Mini Apps и managed bot/user/chat requests.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

### Редактирование, удаление и suggested posts

Area label: `area:message-management`. Priority baseline: `priority:P1`
(P1: высокий пользовательский эффект для Claude-бота).

#### BOTAPI-129: `editMessageCaption`

- Title: `telegram-api: реализовать editMessageCaption`
- Official docs: https://core.telegram.org/bots/api#editmessagecaption
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:message-management`, `priority:P1`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `editMessageCaption` в область: управление уже отправленными сообщениями, poll lifecycle, reactions cleanup и suggested posts. Определить конкретный сценарий: общий message management service, используемый streaming, moderation и media flows.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-130: `editMessageMedia`

- Title: `telegram-api: реализовать editMessageMedia`
- Official docs: https://core.telegram.org/bots/api#editmessagemedia
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:message-management`, `priority:P1`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `editMessageMedia` в область: управление уже отправленными сообщениями, poll lifecycle, reactions cleanup и suggested posts. Определить конкретный сценарий: общий message management service, используемый streaming, moderation и media flows.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-131: `editMessageLiveLocation`

- Title: `telegram-api: реализовать editMessageLiveLocation`
- Official docs: https://core.telegram.org/bots/api#editmessagelivelocation
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:message-management`, `priority:P1`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `editMessageLiveLocation` в область: управление уже отправленными сообщениями, poll lifecycle, reactions cleanup и suggested posts. Определить конкретный сценарий: общий message management service, используемый streaming, moderation и media flows.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-132: `stopMessageLiveLocation`

- Title: `telegram-api: реализовать stopMessageLiveLocation`
- Official docs: https://core.telegram.org/bots/api#stopmessagelivelocation
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:message-management`, `priority:P1`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `stopMessageLiveLocation` в область: управление уже отправленными сообщениями, poll lifecycle, reactions cleanup и suggested posts. Определить конкретный сценарий: общий message management service, используемый streaming, moderation и media flows.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-133: `editMessageChecklist`

- Title: `telegram-api: реализовать editMessageChecklist`
- Official docs: https://core.telegram.org/bots/api#editmessagechecklist
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:message-management`, `priority:P1`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `editMessageChecklist` в область: управление уже отправленными сообщениями, poll lifecycle, reactions cleanup и suggested posts. Определить конкретный сценарий: общий message management service, используемый streaming, moderation и media flows.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-134: `editMessageReplyMarkup`

- Title: `telegram-api: реализовать editMessageReplyMarkup`
- Official docs: https://core.telegram.org/bots/api#editmessagereplymarkup
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:message-management`, `priority:P1`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Обновлять inline keyboards без изменения текста сообщения, например после выбора модели или подтверждения действия.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-135: `stopPoll`

- Title: `telegram-api: реализовать stopPoll`
- Official docs: https://core.telegram.org/bots/api#stoppoll
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:message-management`, `priority:P1`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `stopPoll` в область: управление уже отправленными сообщениями, poll lifecycle, reactions cleanup и suggested posts. Определить конкретный сценарий: общий message management service, используемый streaming, moderation и media flows.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-136: `approveSuggestedPost`

- Title: `telegram-api: реализовать approveSuggestedPost`
- Official docs: https://core.telegram.org/bots/api#approvesuggestedpost
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:message-management`, `priority:P1`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `approveSuggestedPost` в область: управление уже отправленными сообщениями, poll lifecycle, reactions cleanup и suggested posts. Определить конкретный сценарий: общий message management service, используемый streaming, moderation и media flows.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-137: `declineSuggestedPost`

- Title: `telegram-api: реализовать declineSuggestedPost`
- Official docs: https://core.telegram.org/bots/api#declinesuggestedpost
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:message-management`, `priority:P1`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `declineSuggestedPost` в область: управление уже отправленными сообщениями, poll lifecycle, reactions cleanup и suggested posts. Определить конкретный сценарий: общий message management service, используемый streaming, moderation и media flows.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-138: `deleteMessage`

- Title: `telegram-api: реализовать deleteMessage`
- Official docs: https://core.telegram.org/bots/api#deletemessage
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:message-management`, `priority:P1`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить controlled cleanup сообщений бота и admin moderation actions с audit log.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-139: `deleteMessages`

- Title: `telegram-api: реализовать deleteMessages`
- Official docs: https://core.telegram.org/bots/api#deletemessages
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:message-management`, `priority:P1`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить bulk cleanup с chunking по ограничениям Telegram и отчетом о частичных ошибках.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-140: `deleteMessageReaction`

- Title: `telegram-api: реализовать deleteMessageReaction`
- Official docs: https://core.telegram.org/bots/api#deletemessagereaction
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:message-management`, `priority:P1`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `deleteMessageReaction` в область: управление уже отправленными сообщениями, poll lifecycle, reactions cleanup и suggested posts. Определить конкретный сценарий: общий message management service, используемый streaming, moderation и media flows.
- Method note: Новый метод Bot API 10.0; проверить права бота и allowed_updates для reaction state.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-141: `deleteAllMessageReactions`

- Title: `telegram-api: реализовать deleteAllMessageReactions`
- Official docs: https://core.telegram.org/bots/api#deleteallmessagereactions
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:message-management`, `priority:P1`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `deleteAllMessageReactions` в область: управление уже отправленными сообщениями, poll lifecycle, reactions cleanup и suggested posts. Определить конкретный сценарий: общий message management service, используемый streaming, moderation и media flows.
- Method note: Новый метод Bot API 10.0; нужен аккуратный audit log для модерации.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

### Stickers и custom emoji

Area label: `area:stickers`. Priority baseline: `priority:P4`
(P4: нишевая или domain-specific возможность).

#### BOTAPI-142: `sendSticker`

- Title: `telegram-api: реализовать sendSticker`
- Official docs: https://core.telegram.org/bots/api#sendsticker
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:stickers`, `priority:P4`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `sendSticker` в область: отправку stickers/custom emoji и полный lifecycle sticker sets. Определить конкретный сценарий: опциональный creative/media module; не блокирует основной Claude chat flow.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-143: `getStickerSet`

- Title: `telegram-api: реализовать getStickerSet`
- Official docs: https://core.telegram.org/bots/api#getstickerset
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:stickers`, `priority:P4`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `getStickerSet` в область: отправку stickers/custom emoji и полный lifecycle sticker sets. Определить конкретный сценарий: опциональный creative/media module; не блокирует основной Claude chat flow.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-144: `getCustomEmojiStickers`

- Title: `telegram-api: реализовать getCustomEmojiStickers`
- Official docs: https://core.telegram.org/bots/api#getcustomemojistickers
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:stickers`, `priority:P4`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `getCustomEmojiStickers` в область: отправку stickers/custom emoji и полный lifecycle sticker sets. Определить конкретный сценарий: опциональный creative/media module; не блокирует основной Claude chat flow.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-145: `uploadStickerFile`

- Title: `telegram-api: реализовать uploadStickerFile`
- Official docs: https://core.telegram.org/bots/api#uploadstickerfile
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:stickers`, `priority:P4`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `uploadStickerFile` в область: отправку stickers/custom emoji и полный lifecycle sticker sets. Определить конкретный сценарий: опциональный creative/media module; не блокирует основной Claude chat flow.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-146: `createNewStickerSet`

- Title: `telegram-api: реализовать createNewStickerSet`
- Official docs: https://core.telegram.org/bots/api#createnewstickerset
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:stickers`, `priority:P4`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `createNewStickerSet` в область: отправку stickers/custom emoji и полный lifecycle sticker sets. Определить конкретный сценарий: опциональный creative/media module; не блокирует основной Claude chat flow.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-147: `addStickerToSet`

- Title: `telegram-api: реализовать addStickerToSet`
- Official docs: https://core.telegram.org/bots/api#addstickertoset
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:stickers`, `priority:P4`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `addStickerToSet` в область: отправку stickers/custom emoji и полный lifecycle sticker sets. Определить конкретный сценарий: опциональный creative/media module; не блокирует основной Claude chat flow.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-148: `setStickerPositionInSet`

- Title: `telegram-api: реализовать setStickerPositionInSet`
- Official docs: https://core.telegram.org/bots/api#setstickerpositioninset
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:stickers`, `priority:P4`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `setStickerPositionInSet` в область: отправку stickers/custom emoji и полный lifecycle sticker sets. Определить конкретный сценарий: опциональный creative/media module; не блокирует основной Claude chat flow.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-149: `deleteStickerFromSet`

- Title: `telegram-api: реализовать deleteStickerFromSet`
- Official docs: https://core.telegram.org/bots/api#deletestickerfromset
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:stickers`, `priority:P4`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `deleteStickerFromSet` в область: отправку stickers/custom emoji и полный lifecycle sticker sets. Определить конкретный сценарий: опциональный creative/media module; не блокирует основной Claude chat flow.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-150: `replaceStickerInSet`

- Title: `telegram-api: реализовать replaceStickerInSet`
- Official docs: https://core.telegram.org/bots/api#replacestickerinset
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:stickers`, `priority:P4`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `replaceStickerInSet` в область: отправку stickers/custom emoji и полный lifecycle sticker sets. Определить конкретный сценарий: опциональный creative/media module; не блокирует основной Claude chat flow.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-151: `setStickerEmojiList`

- Title: `telegram-api: реализовать setStickerEmojiList`
- Official docs: https://core.telegram.org/bots/api#setstickeremojilist
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:stickers`, `priority:P4`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `setStickerEmojiList` в область: отправку stickers/custom emoji и полный lifecycle sticker sets. Определить конкретный сценарий: опциональный creative/media module; не блокирует основной Claude chat flow.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-152: `setStickerKeywords`

- Title: `telegram-api: реализовать setStickerKeywords`
- Official docs: https://core.telegram.org/bots/api#setstickerkeywords
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:stickers`, `priority:P4`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `setStickerKeywords` в область: отправку stickers/custom emoji и полный lifecycle sticker sets. Определить конкретный сценарий: опциональный creative/media module; не блокирует основной Claude chat flow.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-153: `setStickerMaskPosition`

- Title: `telegram-api: реализовать setStickerMaskPosition`
- Official docs: https://core.telegram.org/bots/api#setstickermaskposition
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:stickers`, `priority:P4`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `setStickerMaskPosition` в область: отправку stickers/custom emoji и полный lifecycle sticker sets. Определить конкретный сценарий: опциональный creative/media module; не блокирует основной Claude chat flow.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-154: `setStickerSetTitle`

- Title: `telegram-api: реализовать setStickerSetTitle`
- Official docs: https://core.telegram.org/bots/api#setstickersettitle
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:stickers`, `priority:P4`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `setStickerSetTitle` в область: отправку stickers/custom emoji и полный lifecycle sticker sets. Определить конкретный сценарий: опциональный creative/media module; не блокирует основной Claude chat flow.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-155: `setStickerSetThumbnail`

- Title: `telegram-api: реализовать setStickerSetThumbnail`
- Official docs: https://core.telegram.org/bots/api#setstickersetthumbnail
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:stickers`, `priority:P4`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `setStickerSetThumbnail` в область: отправку stickers/custom emoji и полный lifecycle sticker sets. Определить конкретный сценарий: опциональный creative/media module; не блокирует основной Claude chat flow.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-156: `setCustomEmojiStickerSetThumbnail`

- Title: `telegram-api: реализовать setCustomEmojiStickerSetThumbnail`
- Official docs: https://core.telegram.org/bots/api#setcustomemojistickersetthumbnail
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:stickers`, `priority:P4`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `setCustomEmojiStickerSetThumbnail` в область: отправку stickers/custom emoji и полный lifecycle sticker sets. Определить конкретный сценарий: опциональный creative/media module; не блокирует основной Claude chat flow.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-157: `deleteStickerSet`

- Title: `telegram-api: реализовать deleteStickerSet`
- Official docs: https://core.telegram.org/bots/api#deletestickerset
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:stickers`, `priority:P4`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `deleteStickerSet` в область: отправку stickers/custom emoji и полный lifecycle sticker sets. Определить конкретный сценарий: опциональный creative/media module; не блокирует основной Claude chat flow.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

### Платежи, invoices и Telegram Stars

Area label: `area:payments-stars`. Priority baseline: `priority:P3`
(P3: требует отдельного product/security решения).

#### BOTAPI-158: `sendInvoice`

- Title: `telegram-api: реализовать sendInvoice`
- Official docs: https://core.telegram.org/bots/api#sendinvoice
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:payments-stars`, `priority:P3`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить paid сценарий только после проектирования billing domain, payload signing и audit log.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-159: `createInvoiceLink`

- Title: `telegram-api: реализовать createInvoiceLink`
- Official docs: https://core.telegram.org/bots/api#createinvoicelink
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:payments-stars`, `priority:P3`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `createInvoiceLink` в область: Telegram Payments, invoice links, shipping/pre-checkout callbacks, Stars balance, refunds и subscriptions. Определить конкретный сценарий: billing module с идемпотентностью, audit log и отдельными security tests.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-160: `answerShippingQuery`

- Title: `telegram-api: реализовать answerShippingQuery`
- Official docs: https://core.telegram.org/bots/api#answershippingquery
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:payments-stars`, `priority:P3`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить shipping handler, если появятся физические goods; иначе явно оставить как blocked-by-product.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-161: `answerPreCheckoutQuery`

- Title: `telegram-api: реализовать answerPreCheckoutQuery`
- Official docs: https://core.telegram.org/bots/api#answerprecheckoutquery
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:payments-stars`, `priority:P3`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить обязательный pre-checkout handler с идемпотентной проверкой заказа перед списанием.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-162: `getMyStarBalance`

- Title: `telegram-api: реализовать getMyStarBalance`
- Official docs: https://core.telegram.org/bots/api#getmystarbalance
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:payments-stars`, `priority:P3`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `getMyStarBalance` в область: Telegram Payments, invoice links, shipping/pre-checkout callbacks, Stars balance, refunds и subscriptions. Определить конкретный сценарий: billing module с идемпотентностью, audit log и отдельными security tests.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-163: `getStarTransactions`

- Title: `telegram-api: реализовать getStarTransactions`
- Official docs: https://core.telegram.org/bots/api#getstartransactions
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:payments-stars`, `priority:P3`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `getStarTransactions` в область: Telegram Payments, invoice links, shipping/pre-checkout callbacks, Stars balance, refunds и subscriptions. Определить конкретный сценарий: billing module с идемпотентностью, audit log и отдельными security tests.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-164: `refundStarPayment`

- Title: `telegram-api: реализовать refundStarPayment`
- Official docs: https://core.telegram.org/bots/api#refundstarpayment
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:payments-stars`, `priority:P3`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `refundStarPayment` в область: Telegram Payments, invoice links, shipping/pre-checkout callbacks, Stars balance, refunds и subscriptions. Определить конкретный сценарий: billing module с идемпотентностью, audit log и отдельными security tests.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-165: `editUserStarSubscription`

- Title: `telegram-api: реализовать editUserStarSubscription`
- Official docs: https://core.telegram.org/bots/api#edituserstarsubscription
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:payments-stars`, `priority:P3`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `editUserStarSubscription` в область: Telegram Payments, invoice links, shipping/pre-checkout callbacks, Stars balance, refunds и subscriptions. Определить конкретный сценарий: billing module с идемпотентностью, audit log и отдельными security tests.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

### Telegram Passport и Games

Area label: `area:passport-games`. Priority baseline: `priority:P4`
(P4: нишевая или domain-specific возможность).

#### BOTAPI-166: `setPassportDataErrors`

- Title: `telegram-api: реализовать setPassportDataErrors`
- Official docs: https://core.telegram.org/bots/api#setpassportdataerrors
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:passport-games`, `priority:P4`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `setPassportDataErrors` в область: нишевые Telegram Passport validation и game platform methods. Определить конкретный сценарий: изолированные domain-specific modules, добавляемые только при появлении реального product scenario.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-167: `sendGame`

- Title: `telegram-api: реализовать sendGame`
- Official docs: https://core.telegram.org/bots/api#sendgame
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:passport-games`, `priority:P4`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `sendGame` в область: нишевые Telegram Passport validation и game platform methods. Определить конкретный сценарий: изолированные domain-specific modules, добавляемые только при появлении реального product scenario.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-168: `setGameScore`

- Title: `telegram-api: реализовать setGameScore`
- Official docs: https://core.telegram.org/bots/api#setgamescore
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:passport-games`, `priority:P4`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `setGameScore` в область: нишевые Telegram Passport validation и game platform methods. Определить конкретный сценарий: изолированные domain-specific modules, добавляемые только при появлении реального product scenario.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.

#### BOTAPI-169: `getGameHighScores`

- Title: `telegram-api: реализовать getGameHighScores`
- Official docs: https://core.telegram.org/bots/api#getgamehighscores
- Labels: `telegram-api`, `bot-api-10.0`, `kind:feature`, `area:passport-games`, `priority:P4`, `stage:S1-spec`
- Stages: `S1-spec` -> `S2-design` -> `S3-implementation` -> `S4-tests` -> `S5-docs`
- Scope: Добавить поддержку `getGameHighScores` в область: нишевые Telegram Passport validation и game platform methods. Определить конкретный сценарий: изолированные domain-specific modules, добавляемые только при появлении реального product scenario.
- Acceptance criteria:
  - параметры метода, права бота и ограничения Telegram описаны в issue;
  - реализация идет через typed aiogram API или изолированный raw Bot API
    helper, если текущий aiogram не поддерживает метод;
  - есть unit tests для успешного вызова, ошибки Telegram и validation path;
  - пользовательская или админская документация обновлена вместе с
    `docs/functionality-analysis.md`.
