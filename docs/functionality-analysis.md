# Анализ текущей функциональности

Снимок состояния: 2026-05-25. Документ фиксирует фактическую функциональность
`telegram-claude-agent` после реализации базового Telegram-бота для работы с
`free-claude-code`.

## Назначение проекта

`telegram-claude-agent` предоставляет Telegram-интерфейс к HTTP proxy
`free-claude-code`. Приложение принимает сообщения через Telegram Bot API,
преобразует их в формат Anthropic Messages API и отправляет в proxy. Ответы
возвращаются пользователю как Telegram-сообщения.

Основной runtime состоит из:

- FastAPI-приложения и webhook endpoint в `bot/main.py`;
- aiogram `Dispatcher` с роутерами команд, чата и inline mode;
- клиента `ClaudeProxyClient` для `/v1/messages`, `/v1/models` и
  `/v1/messages/count_tokens`;
- in-memory хранилища истории и пользовательских настроек;
- middleware для structured logging и rate limiting.

## Поддерживаемые режимы запуска

### Long polling

Если `TELEGRAM_WEBHOOK_URL` не задан, `bot/main.py` запускает
`dp.start_polling()` в background task во время FastAPI startup. Это удобно для
локальной разработки, но процесс всё равно стартует через `uvicorn`.

### Webhook

Если `TELEGRAM_WEBHOOK_URL` задан, приложение регистрирует webhook в Telegram.
Endpoint `POST /webhook` принимает update JSON, валидирует его через
`aiogram.types.Update.model_validate()` и передает в dispatcher.

Если задан `API_SECRET_TOKEN`, webhook дополнительно проверяет заголовок
`X-Telegram-Bot-Api-Secret-Token`. При несовпадении возвращается HTTP 403.

### Health check

Endpoint `GET /health` возвращает `{"status": "ok"}` и может использоваться
для простой проверки доступности процесса.

## Покрытие Telegram Bot API

Покрытие сверено с официальной документацией Telegram Bot API на 2026-05-25:
https://core.telegram.org/bots/api. На этот момент актуальная документация уже
описывает Bot API 10.0 от 2026-05-08, а проект закрепляет `aiogram==3.3.0`, так
что новые методы и типы Bot API 9.x/10.x не следует считать автоматически
поддержанными только из-за использования aiogram.

Подробный issue-style backlog для доведения покрытия до полного Bot API
описан в
[telegram-bot-api-implementation-guide.md](telegram-bot-api-implementation-guide.md):
в нем 169 карточек для пока не интегрированных методов с labels, stages,
scope и acceptance criteria.

### Уже используемые методы Bot API

| Метод | Где используется | Фактическое назначение |
| --- | --- | --- |
| `getMe` | `bot/main.py`, `bot/handlers/chat.py` | Кеширование данных бота при startup и получение username для определения mention/reply в группах. |
| `getUpdates` | `dp.start_polling()` в `bot/main.py` | Непрямое использование через aiogram long polling, когда `TELEGRAM_WEBHOOK_URL` не задан. |
| `setWebhook` | `bot/main.py` | Регистрация webhook URL и optional `secret_token` при наличии `TELEGRAM_WEBHOOK_URL`. |
| `sendMessage` | `message.answer()` в command/chat/rate-limit handlers | Отправка командных ответов, Claude-ответов, ошибок и rate-limit уведомлений. |
| `editMessageText` | `sent_msg.edit_text()` в streaming handler | Обновление одного сообщения во время streaming и замена его финальным первым chunk'ом. |
| `getFile` | `bot/handlers/chat.py` | Получение `file_path` для входящих `photo`, `voice` и `document`. |
| `answerInlineQuery` | `bot/handlers/inline.py` | Минимальный inline mode: возвращается один статический `InlineQueryResultArticle`. |

`message.bot.download_file()` скачивает файл по `file_path`, полученному через
`getFile`; это важная часть file flow, но не отдельный метод Bot API из списка
документации.

### Уже обрабатываемые update-типы и объекты

- `message`: частично обрабатываются text, photo, voice, document, caption и
  reply metadata;
- `inline_query`: обрабатывается минимально, без запроса к Claude proxy;
- `callback_query`: распознается только middleware для логирования и rate
  limiting, но отдельного handler нет.

Текущий `TELEGRAM_GUEST_MODE_ENABLED` не является официальным Telegram Bot API
Guest Mode из Bot API 10.0. В коде это локальная политика для групп: если бот
уже находится в группе и к нему обратились mention/reply, история группы не
прикладывается к запросу в proxy. Официальные `guest_message`,
`Message.guest_query_id` и `answerGuestQuery` сейчас не интегрированы.

### Что не интегрировано для максимальных возможностей

Почти все остальные методы Bot API пока не используются. Для максимального
покрытия их лучше добавлять не одним большим слоем, а по функциональным
направлениям:

1. Lifecycle и диагностика: `deleteWebhook`, `getWebhookInfo`, `logOut`,
   `close`, явная настройка `allowed_updates`, диагностика конфликтов между
   webhook и long polling.
2. Профиль и команды бота: `setMyCommands`, `deleteMyCommands`,
   `getMyCommands`, `setMyName`, `getMyName`, `setMyDescription`,
   `getMyDescription`, `setMyShortDescription`, `getMyShortDescription`,
   `setMyProfilePhoto`, `removeMyProfilePhoto`, `setChatMenuButton`,
   `getChatMenuButton`, `setMyDefaultAdministratorRights`,
   `getMyDefaultAdministratorRights`.
3. Более богатые ответы пользователю: `sendChatAction`, `sendPhoto`,
   `sendDocument`, `sendAudio`, `sendVoice`, `sendVideo`, `sendAnimation`,
   `sendVideoNote`, `sendMediaGroup`, `sendLivePhoto`, `sendPaidMedia`,
   `sendLocation`, `sendVenue`, `sendContact`, `sendPoll`, `sendChecklist`,
   `sendDice`, `sendMessageDraft`, `setMessageReaction`.
4. Управление сообщениями: `forwardMessage`, `forwardMessages`, `copyMessage`,
   `copyMessages`, `editMessageCaption`, `editMessageMedia`,
   `editMessageLiveLocation`, `stopMessageLiveLocation`,
   `editMessageChecklist`, `editMessageReplyMarkup`, `stopPoll`,
   `approveSuggestedPost`, `declineSuggestedPost`, `deleteMessage`,
   `deleteMessages`, `deleteMessageReaction`, `deleteAllMessageReactions`.
5. Интерактивность: полноценные `answerInlineQuery` ответы через Claude,
   handler для `chosen_inline_result`, `answerCallbackQuery` и inline keyboards
   для настроек/выбора модели, `answerGuestQuery` для официального Guest Mode,
   `answerWebAppQuery`, `savePreparedInlineMessage`,
   `savePreparedKeyboardButton`.
6. Группы, модерация и форумы: `getChat`, `getChatAdministrators`,
   `getChatMemberCount`, `getChatMember`, `banChatMember`,
   `unbanChatMember`, `restrictChatMember`, `promoteChatMember`,
   `setChatAdministratorCustomTitle`, `setChatMemberTag`,
   `setChatPermissions`, invite-link методы, join-request методы,
   `pinChatMessage`, `unpinChatMessage`, `unpinAllChatMessages`,
   forum-topic методы и `leaveChat`.
7. Пользовательский контекст Telegram: `getUserProfilePhotos`,
   `getUserProfileAudios`, `getUserChatBoosts`,
   `getUserPersonalChatMessages`, `setUserEmojiStatus`.
8. Бизнес, managed bots и bot-to-bot: `getBusinessConnection`,
   `readBusinessMessage`, `deleteBusinessMessages`, методы
   `setBusinessAccount*`, `getManagedBotToken`, `replaceManagedBotToken`,
   `getManagedBotAccessSettings`, `setManagedBotAccessSettings`.
9. Gifts, Stars и платежи: `getAvailableGifts`, `sendGift`,
   `giftPremiumSubscription`, `getMyStarBalance`, `getStarTransactions`,
   `refundStarPayment`, `editUserStarSubscription`, `sendInvoice`,
   `createInvoiceLink`, `answerShippingQuery`, `answerPreCheckoutQuery`.
10. Нишевые платформенные возможности: stories (`postStory`, `repostStory`,
    `editStory`, `deleteStory`), stickers/custom emoji, Telegram Passport
    (`setPassportDataErrors`) и Games (`sendGame`, `setGameScore`,
    `getGameHighScores`).

Для этого проекта наиболее полезный следующий слой Telegram API выглядит так:
сначала lifecycle/diagnostics, `sendChatAction`, реальные inline/callback
flows, official Guest Mode и rich outbound media; затем group administration,
payments/Stars/gifts, business/managed-bot возможности и остальные
domain-specific методы.

Для планирования последующих PR этот список уже разложен до отдельных
issue-карточек в
[telegram-bot-api-implementation-guide.md](telegram-bot-api-implementation-guide.md).

## Пользовательские сценарии

### Команды

- `/start` отправляет приветствие и подсказку использовать `/help`;
- `/help` перечисляет доступные команды и поддерживаемые типы сообщений;
- `/model` без аргументов показывает текущую модель пользователя и пытается
  получить список моделей из proxy;
- `/model <model_id>` сохраняет выбранную модель в in-memory настройках
  пользователя;
- `/settings` показывает текущую модель, streaming flag, guest mode и лимит
  запросов;
- `/clear` очищает историю разговора для пары `(chat_id, user_id)`.

Важная деталь: выбранная через `/model <model_id>` модель сохраняется в
`storage.user_settings`, но обработчик чата сейчас отправляет запросы с
`settings.free_claude_default_model`. То есть команда сохраняет настройку, но
не влияет на реальные ответы чата.

### Текстовые сообщения

Личные чаты используют историю сообщений пользователя в конкретном чате.
Новое сообщение добавляется к истории, отправляется в proxy и после успешного
ответа сохраняются обе стороны диалога.

История ограничена `MemoryStorage.max_history` и хранится только в памяти
процесса. После перезапуска приложения история и пользовательские настройки
теряются.

### Группы и Guest Mode

В группах и супергруппах бот отвечает только когда:

- сообщение содержит `@bot_username`;
- caption медиа содержит `@bot_username`;
- сообщение является reply на сообщение бота.

При включенном `TELEGRAM_GUEST_MODE_ENABLED` история в группах не используется:
в proxy отправляется только текущий запрос. Это снижает риск утечки контекста
между участниками группы. Это не поддержка официального Telegram Guest Mode,
где бот может отвечать через `answerGuestQuery` на `guest_message`, не являясь
полноценным участником чата.

### Изображения

При получении `photo` бот скачивает самый крупный вариант изображения,
кодирует его в base64 и отправляет как content block типа `image` с
`media_type=image/jpeg`. Caption, если он есть, добавляется отдельным text
block.

### Документы

Для документов поддерживается извлечение текста из:

- `text/plain`;
- `application/pdf`;
- `application/vnd.openxmlformats-officedocument.wordprocessingml.document`;
- `application/msword`.

Неизвестный MIME-тип логируется и возвращает пустой результат. При пустом
результате пользователь получает сообщение об ошибке извлечения текста.

### Голосовые сообщения

Голосовые сообщения скачиваются, сохраняются во временный `.ogg` файл и
транскрибируются через optional dependency `openai-whisper`. Если whisper не
установлен или транскрипция падает, пользователь получает сообщение о
невозможности транскрибации.

### Inline mode

Inline handler возвращает один статический `InlineQueryResultArticle`.
Фактической отправки inline query в Claude proxy сейчас нет.

## Интеграция с free-claude-code

`ClaudeProxyClient` отправляет JSON-запросы с заголовками:

- `Content-Type: application/json`;
- `Authorization: Bearer <FREE_CLAUDE_AUTH_TOKEN>`;
- `anthropic-version: 2023-06-01`.

Поддерживаемые методы:

- `list_models()` выполняет `GET /v1/models` и понимает форматы `models[]` и
  `data[]`;
- `count_tokens()` выполняет `POST /v1/messages/count_tokens`;
- `send_message()` выполняет `POST /v1/messages` в streaming или non-streaming
  режиме.

Streaming сейчас реализован как чтение SSE-подобных строк из уже полученного
`httpx.Response`. Для каждого `content_block_delta` с `text_delta` бот
обновляет одно Telegram-сообщение, а после завершения рендерит полный ответ и
разбивает его на части до Telegram-лимита 4096 символов.

## Форматирование ответов

Перед отправкой финального ответа используется минимальный Markdown to Telegram
HTML рендерер:

- `**bold**` -> `<b>bold</b>`;
- `*italic*` -> `<i>italic</i>`;
- `` `inline` `` -> `<code>inline</code>`;
- fenced code blocks -> `<pre><code>...</code></pre>`.

Сырой HTML экранируется. Если Telegram не принимает HTML chunk, отправка
fallback'ится на plain text.

Ограничение: разбивка HTML по 4096 символов не проверяет баланс HTML-тегов на
границах chunk'ов. При длинном форматированном ответе часть chunk'ов может
попасть в fallback plain text.

## Конфигурация

Конфигурация загружается через `pydantic-settings` из `.env` и переменных
окружения. Ключевые параметры:

- `FREE_CLAUDE_BASE_URL`;
- `FREE_CLAUDE_AUTH_TOKEN`;
- `FREE_CLAUDE_DEFAULT_MODEL`;
- `FREE_CLAUDE_TIMEOUT_SECONDS`;
- `FREE_CLAUDE_STREAMING_ENABLED`;
- `TELEGRAM_BOT_TOKEN`;
- `TELEGRAM_WEBHOOK_URL`;
- `TELEGRAM_GUEST_MODE_ENABLED`;
- `TELEGRAM_ALLOWED_CHAT_IDS`;
- `API_SECRET_TOKEN`;
- `RATE_LIMIT_REQUESTS_PER_MINUTE`;
- `LOG_LEVEL`.

`TELEGRAM_ALLOWED_CHAT_IDS` парсится как comma-separated список целых chat id.
Если список пустой, бот доступен во всех чатах.

## Безопасность и ограничения доступа

Текущие защитные механизмы:

- webhook secret token при заданном `API_SECRET_TOKEN`;
- optional whitelist чатов через `TELEGRAM_ALLOWED_CHAT_IDS`;
- per-user rate limit в sliding window на 60 секунд;
- guest mode для групп;
- экранирование HTML в LLM-ответах перед Telegram HTML.

Ограничения:

- `API_SECRET_TOKEN` опционален на уровне настроек, хотя для webhook режима он
  практически обязателен;
- rate limit хранится в памяти и сбрасывается при рестарте;
- нет persistent audit log, admin panel или метрик;
- нет отдельной проверки размера входных файлов перед скачиванием и обработкой.

## Наблюдаемость

`structlog` настроен на JSON output. `LoggingMiddleware` логирует входящие
сообщения, callback query, inline query и неизвестные update types.

`LOG_LEVEL` присутствует в настройках, но сейчас не применяется к конфигурации
logging. Фактическая детализация логов зависит от дефолтного окружения.

## Хранение данных

`MemoryStorage` хранит:

- историю по ключу `(chat_id, user_id)`;
- пользовательские настройки по `user_id`.

Плюсы текущего решения: простота и отсутствие внешней инфраструктуры.
Минусы: нет persistence, нет горизонтального масштабирования с общей историей,
нет TTL и нет защиты от роста `user_settings`.

## Деплой

Проект содержит:

- `Dockerfile` на `python:3.11-slim`;
- `docker-compose.yml` для полного стека с `free-claude-code`;
- `docker-compose.external.yml` для подключения к уже запущенному proxy на
  host machine.

Основной production entrypoint: `uvicorn bot.main:app --host 0.0.0.0 --port
8000`.

## Тестовое покрытие

Автоматизированные unit tests покрывают:

- парсинг `TELEGRAM_ALLOWED_CHAT_IDS` и boolean env values;
- операции `MemoryStorage`;
- `ClaudeProxyClient.list_models()`, non-streaming и streaming отправку;
- извлечение текста из plain text и поведение на неизвестном MIME;
- rate limit middleware;
- Markdown/HTML форматирование, удаление mention и разбивку Telegram сообщений.

Integration tests описаны для живого proxy, но сейчас всегда skipped через
module-level `pytestmark`.

Локальная проверка на Python 3.12.3:

```text
python -m pytest -v
27 passed, 2 skipped, 6 warnings
```

Предупреждения связаны с pydantic deprecated `__fields__` при использовании
`MagicMock(spec=types.Message)` в тестах rate limit middleware.

## Выявленные пробелы

1. Выбор модели через `/model <model_id>` не используется в `handle_chat_message()`.
2. `LOG_LEVEL` задан в конфигурации, но не применён к logging setup.
3. `test_list_models_openai_format` не проверяет OpenAI-compatible ветку:
   внутри теста патчится `post`, хотя production method использует `get`, и
   assertions отсутствуют.
4. Integration tests нельзя включить через `INTEGRATION_TEST=1`, потому что
   skip condition сейчас всегда `True`.
5. Streaming implementation использует `AsyncClient.post()` и затем
   `aiter_lines()` на response; для настоящего HTTP streaming обычно лучше
   использовать streaming API клиента, чтобы не буферизовать весь ответ.
6. HTML chunking не гарантирует валидность HTML внутри каждого Telegram
   сообщения.
7. Голосовые сообщения зависят от optional whisper/ffmpeg, но runtime не
   сообщает администратору о неполной установке до первого voice request.
8. In-memory storage подходит для MVP, но не для restart-safe или multi-replica
   deployment.
9. Нет тестов обработчиков команд `/model`, `/settings`, `/clear` с моками
   Telegram message objects.
10. Нет теста webhook secret validation и `/health`.
11. Покрытие Telegram Bot API ограничено семью методами; official Guest Mode,
    callback flows, rich outbound media, bot profile/commands management,
    moderation, payments/Stars/gifts, business и managed-bot методы не
    реализованы.

## Рекомендуемый порядок дальнейших работ

1. Починить использование пользовательской модели в chat handler и добавить
   unit tests для `/model`.
2. Исправить `test_list_models_openai_format`, чтобы он реально проверял
   `data[]` response от `GET /v1/models`.
3. Сделать integration tests opt-in через `INTEGRATION_TEST=1`.
4. Применить `LOG_LEVEL` к logging configuration.
5. Добавить тесты webhook secret validation, `/health`, command handlers и
   edge cases HTML chunking.
6. Рассмотреть persistent storage backend: Redis или database.
7. Перейти на настоящий streaming transport в `httpx.AsyncClient.stream()`,
   если proxy поддерживает long-lived SSE responses.
8. Добавить ограничения и диагностику для входных файлов и optional voice
   dependencies.
9. Добавить следующий слой Telegram API: `deleteWebhook`, `getWebhookInfo`,
   `sendChatAction`, `setMyCommands`, `answerCallbackQuery`, полноценный
   `answerInlineQuery`, `answerGuestQuery` и rich outbound media методы.
