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
в нем 169 карточек методов с labels, stages, scope и acceptance criteria;
после внедрения `deleteWebhook`, `getWebhookInfo`, `logOut`, `close`, `forwardMessage`,
`copyMessage`, `forwardMessages`, `sendPhoto`, `copyMessages`, `sendAudio`,
`sendLivePhoto`, `sendDocument`, `sendVideo`, `sendVideoNote`, `sendAnimation`,
`sendVoice`, `sendPaidMedia`, `sendLocation`, `sendMediaGroup`, `sendVenue`,
`sendPoll`, `sendContact`, `sendDice`, `sendChecklist`, `editMessageLiveLocation`,
`stopMessageLiveLocation`, `postStory`,
`editStory`, `sendChatAction`,
`sendMessageDraft`, `getUserProfilePhotos`, `setMessageReaction`,
`setUserEmojiStatus`, `getUserProfileAudios`, `banChatMember`,
`unbanChatMember`, `restrictChatMember`, `promoteChatMember`,
`approveChatJoinRequest`, `createChatInviteLink`, `editChatInviteLink`,
`setChatPhoto`, `deleteChatPhoto`, `pinChatMessage`, `unpinChatMessage`,
`unpinAllChatMessages`, `getChatMember`, `getUserPersonalChatMessages`,
`getBusinessAccountStarBalance`, `getForumTopicIconStickers`, `editForumTopic`,
`editGeneralForumTopic`,
`closeForumTopic`, `closeGeneralForumTopic`, `reopenForumTopic`,
`unpinAllForumTopicMessages`, `unpinAllGeneralForumTopicMessages`,
`unhideGeneralForumTopic`, `setMyName`, `getMyName`, `setMyDescription`,
`getChatMenuButton`, `editMessageChecklist`;
остается 106 пока не
интегрированных метода.
Эти карточки также заведены как реальные GitHub issues в репозитории; индекс
соответствия `BOTAPI-###` -> issue описан в
[telegram-bot-api-issue-index.md](telegram-bot-api-issue-index.md).

### Уже используемые методы Bot API

| Метод | Где используется | Фактическое назначение |
| --- | --- | --- |
| `getMe` | `bot/main.py`, `bot/handlers/chat.py` | Кеширование данных бота при startup и получение username для определения mention/reply в группах. |
| `getUpdates` | `dp.start_polling()` в `bot/main.py` | Непрямое использование через aiogram long polling, когда `TELEGRAM_WEBHOOK_URL` не задан. |
| `setWebhook` | `bot/main.py` | Регистрация webhook URL и optional `secret_token` при наличии `TELEGRAM_WEBHOOK_URL`. |
| `deleteWebhook` | `bot/services/webhook_delete.py`, `/deletewebhook` в `bot/handlers/commands.py` | Админское удаление webhook перед переходом на long polling или local Bot API с опциональным `drop_pending_updates`. |
| `getWebhookInfo` | `bot/services/webhook_info.py`, `/webhook` в `bot/handlers/commands.py` | Админская диагностика статуса webhook, pending updates, `allowed_updates` и последних ошибок доставки. |
| `setMyCommands` | `bot/services/set_my_commands.py`, `/setmycommands` в `bot/handlers/commands.py` | Admin-flow синхронизации default command list, отображаемого в Telegram clients, через typed aiogram API; команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS` без fallback, принимает список `command:description`, валидирует лимиты Telegram (0-100 команд, имена 1-32 lowercase/digit/underscore, описания 1-256) до обращения к Telegram, а ошибки Telegram возвращаются оператору. |
| `setMyName` | `bot/services/set_my_name.py`, `/setmyname` в `bot/handlers/commands.py`, startup sync в `bot/main.py` | Admin/config-flow синхронизации default или localized display name бота через typed aiogram API `Bot.set_my_name`; при startup вызывается только если задан `TELEGRAM_BOT_NAME`, optional `TELEGRAM_BOT_NAME_LANGUAGE_CODE` задает локаль, команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS` без fallback и deny-by-default при пустом списке, имя валидируется по лимиту Telegram 0-64 символа, пустая строка очищает выбранное имя, специальных update types и chat administrator rights не требуется, так как метод меняет профиль самого бота; structured logs пишут только длину имени и наличие language code, rollback выполняется повторной установкой прежнего имени, очисткой env sync или через BotFather. |
| `setMyDescription` | `bot/services/set_my_description.py`, `/setmydescription` в `bot/handlers/commands.py`, startup sync в `bot/main.py` | Admin/config-flow синхронизации default или localized public description бота через typed aiogram API `Bot.set_my_description`; при startup вызывается только если задан `TELEGRAM_BOT_DESCRIPTION`, optional `TELEGRAM_BOT_DESCRIPTION_LANGUAGE_CODE` задает локаль, команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS` без fallback и deny-by-default при пустом списке, описание валидируется по лимиту Telegram 0-512 символов, пустая строка очищает выбранное описание, специальных update types и chat administrator rights не требуется, так как метод меняет профиль самого бота; structured logs пишут только длину описания и наличие language code, rollback выполняется повторной установкой прежнего описания, очисткой env sync или через BotFather. |
| `setMyShortDescription` | `bot/services/set_my_short_description.py`, `/setmyshortdescription` в `bot/handlers/commands.py`, startup sync в `bot/main.py` | Admin/config-flow синхронизации default или localized public short description бота через typed aiogram API `Bot.set_my_short_description`; при startup вызывается только если задан `TELEGRAM_BOT_SHORT_DESCRIPTION`, optional `TELEGRAM_BOT_SHORT_DESCRIPTION_LANGUAGE_CODE` задает локаль, команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS` без fallback и deny-by-default при пустом списке, short description валидируется по лимиту Telegram 0-120 символов, пустая строка очищает выбранное короткое описание, специальных update types и chat administrator rights не требуется, так как метод меняет профиль самого бота; structured logs пишут только длину short description и наличие language code, rollback выполняется повторной установкой прежнего короткого описания, очисткой env sync или через BotFather. |
| `getMyDescription` | `bot/services/get_my_description.py`, `/getmydescription` в `bot/handlers/commands.py`, startup audit в `bot/main.py` | Read-only admin/config diagnostic для проверки default или localized public description бота через typed aiogram API `Bot.get_my_description`; метод принимает только optional `language_code` и возвращает `BotDescription`, не требует chat administrator rights и специальных update types, а команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS` без fallback и deny-by-default при пустом списке; startup audit читает фактическое описание после optional `TELEGRAM_BOT_DESCRIPTION` sync, structured logs пишут только длину описания и наличие language code, ошибки Telegram возвращаются оператору или прерывают startup как операционная misconfiguration. |
| `getMyShortDescription` | `bot/services/get_my_short_description.py`, `/getmyshortdescription` в `bot/handlers/commands.py`, startup audit в `bot/main.py` | Read-only admin/config diagnostic для проверки default или localized public short description бота через typed aiogram API `Bot.get_my_short_description`; метод принимает только optional `language_code` и возвращает `BotShortDescription`, не требует chat administrator rights и специальных update types, а команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS` без fallback и deny-by-default при пустом списке; startup audit читает фактическое короткое описание после optional `TELEGRAM_BOT_SHORT_DESCRIPTION` sync, structured logs пишут только длину short description и наличие language code, ошибки Telegram возвращаются оператору или прерывают startup как операционная misconfiguration. |
| `getMyName` | `bot/services/get_my_name.py`, `/getmyname` в `bot/handlers/commands.py`, startup audit в `bot/main.py` | Read-only admin/config diagnostic для проверки default или localized display name бота через typed aiogram API `Bot.get_my_name`; метод принимает только optional `language_code` и возвращает `BotName`, не требует chat administrator rights и специальных update types, а команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS` без fallback и deny-by-default при пустом списке; startup audit читает фактическое имя после optional `TELEGRAM_BOT_NAME` sync, structured logs пишут только длину имени и наличие language code, ошибки Telegram возвращаются оператору или прерывают startup как операционная misconfiguration. |
| `deleteMyCommands` | `bot/services/delete_my_commands.py`, `/deletemycommands` в `bot/handlers/commands.py` | Admin-flow безопасной очистки command menu перед повторной синхронизацией через typed aiogram API; команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS` без fallback, принимает optional `scope`, `chat_id`, `user_id` и `language`, валидирует совместимость scope-параметров до обращения к Telegram, не требует chat administrator rights, а ошибки Telegram возвращаются оператору. |
| `getMyCommands` | `bot/services/get_my_commands.py`, `/getmycommands` в `bot/handlers/commands.py` | Read-only admin-diagnostic проверки фактического command menu через typed aiogram API; команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS` без fallback, принимает те же optional `scope`, `chat_id`, `user_id` и `language`, валидирует совместимость scope-параметров до обращения к Telegram, не требует chat administrator rights и не вызывает `free-claude-code`; сервис умеет сравнивать actual commands с ожидаемой конфигурацией и выводить missing, unexpected и description mismatch диагностику, а ошибки Telegram возвращаются оператору. |
| `getChatMenuButton` | `bot/services/get_chat_menu_button.py`, `/getchatmenubutton` в `bot/handlers/commands.py` | Read-only admin-diagnostic проверки фактической menu button для default state или конкретного `chat_id` через typed aiogram API `Bot.get_chat_menu_button`; команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS` без fallback и deny-by-default при пустом списке, принимает только optional `chat_id`, валидирует целочисленный идентификатор до обращения к Telegram, не требует chat administrator rights, специальных update types или вызова `free-claude-code`, а ошибки Telegram возвращаются оператору. |
| `logOut` | `bot/services/log_out.py`, `/logout` в `bot/handlers/commands.py` | Защищенный admin-flow выхода из cloud Bot API перед запуском local Bot API server, с обязательным подтверждением. |
| `close` | `bot/services/close.py`, `/close` в `bot/handlers/commands.py` | Защищенный admin-flow закрытия bot instance перед миграцией между local Bot API серверами, с обязательным подтверждением. |
| `forwardMessage` | `bot/services/forward_message.py`, `/forward` в `bot/handlers/commands.py` | Admin-flow пересылки одного сообщения из другого чата в текущий admin-чат для поддержки/модерации, с `protect_content` по умолчанию. |
| `forwardMessages` | `bot/services/forward_messages.py`, `/forwards` в `bot/handlers/commands.py` | Admin-flow пакетной пересылки 1-100 сообщений из другого чата в текущий admin-чат с сохранением album grouping, с `protect_content` по умолчанию. |
| `copyMessage` | `bot/services/copy_message.py`, `/copy` в `bot/handlers/commands.py` | Admin-flow копирования одного сообщения из другого чата в текущий admin-чат как нового сообщения без ссылки на исходного отправителя, с `protect_content` по умолчанию. |
| `copyMessages` | `bot/services/copy_messages.py`, `/copies` в `bot/handlers/commands.py` | Admin-flow пакетного копирования 1-100 сообщений из другого чата в текущий admin-чат как новых сообщений без ссылки на исходного отправителя, с сохранением album grouping, `protect_content` по умолчанию и опциональным `remove_caption`. |
| `sendPhoto` | `bot/services/send_photo.py`, `/photo` в `bot/handlers/commands.py` | Admin-flow отправки изображения в текущий чат как настоящего Telegram-фото по URL или `file_id`, а не только текстовой интерпретации. |
| `sendAudio` | `bot/services/send_audio.py`, `/audio` в `bot/handlers/commands.py` | Admin-flow отправки аудиофайла в текущий чат как проигрываемого музыкального трека по URL или `file_id`, а не только текстовой интерпретации. |
| `sendLivePhoto` | `bot/services/send_live_photo.py`, `/livephoto` в `bot/handlers/commands.py` | Admin-flow отправки live photo (короткое видео + статичная обложка) в текущий чат по `file_id`, через изолированный raw Bot API helper, так как pinned `aiogram==3.3.0` не имеет typed wrapper для этого метода Bot API 10.0. |
| `sendDocument` | `bot/services/send_document.py`, `/document` в `bot/handlers/commands.py` | Admin-flow отправки файла в текущий чат как Telegram-документа по URL или `file_id` — для больших текстовых, PDF или исходных артефактов, когда текстовый ответ не подходит. |
| `sendVideo` | `bot/services/send_video.py`, `/video` в `bot/handlers/commands.py` | Admin-flow отправки видео в текущий чат как проигрываемого Telegram-видео по URL или `file_id`, а не только текстовой интерпретации. |
| `sendVideoNote` | `bot/services/send_video_note.py`, `/videonote` в `bot/handlers/commands.py` | Admin-flow отправки видеосообщения-кружка (круглого квадратного видео) в текущий чат по `file_id`, через typed aiogram API; у видеосообщений нет caption, и Telegram не поддерживает их отправку по URL. |
| `sendAnimation` | `bot/services/send_animation.py`, `/animation` в `bot/handlers/commands.py` | Admin-flow отправки анимации (GIF или видео без звука) в текущий чат как проигрываемого зацикленного клипа по URL или `file_id`, а не только текстовой интерпретации. |
| `sendSticker` | `bot/services/send_sticker.py`, `/sticker` в `bot/handlers/commands.py` | Admin-flow отправки sticker/custom emoji в текущий чат по URL или `file_id`, через typed aiogram API; сценарий изолирован от основного Claude chat flow и закрыт строгим admin allowlist. |
| `sendVoice` | `bot/services/send_voice.py`, `/voice` в `bot/handlers/commands.py` | Admin-flow отправки голосового сообщения в текущий чат как проигрываемого аудиоклипа (в виде waveform) по URL или `file_id`, а не только текстовой интерпретации. |
| `sendPaidMedia` | `bot/services/send_paid_media.py`, `/paidmedia` в `bot/handlers/commands.py` | Admin-flow отправки платного фото в текущий чат, доступ к которому пользователи оплачивают Telegram Stars, по URL или `file_id`, через изолированный raw Bot API helper, так как pinned `aiogram==3.3.0` не имеет typed wrapper для этого метода Bot API 7.6. |
| `answerWebAppQuery` | `bot/services/answer_web_app_query.py`, `/answerwebappquery` в `bot/handlers/commands.py` | Admin-flow ответа на Telegram Web App query одним `InlineQueryResult` от имени пользователя через typed aiogram API; команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS`, не вызывает `free-claude-code`, а Telegram проверяет действительность `web_app_query_id`. |
| `savePreparedInlineMessage` | `bot/services/save_prepared_inline_message.py`, `/savepreparedinline` в `bot/handlers/commands.py` | Admin-flow сохранения одного `InlineQueryResult` как prepared inline message для пользователя через изолированный raw Bot API helper, так как pinned `aiogram==3.3.0` не имеет typed wrapper для этого метода Bot API 10.0; optional `allow_*_chats` ограничивают типы чатов, команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS`, специальных chat administrator rights не требует и не вызывает `free-claude-code`. |
| `savePreparedKeyboardButton` | `bot/services/save_prepared_keyboard_button.py`, `/savepreparedkeyboard` в `bot/handlers/commands.py` | Admin-flow сохранения prepared keyboard button для Telegram Mini App пользователя по `user_id` и `prepared_message_id` через изолированный raw Bot API helper, так как pinned `aiogram==3.3.0` не имеет typed wrapper для этого метода Bot API 10.0; сценарий предполагает проверенную Mini App init data и prepared inline message, команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS`, не требует chat administrator rights, rollback выполняется заменой prepared message/button или снятием Mini App entry point. |
| `sendLocation` | `bot/services/send_location.py`, `/location` в `bot/handlers/commands.py` | Admin-flow отправки точки на карте в текущий чат как настоящей Telegram-локации по широте и долготе, через typed aiogram API; у локаций нет caption, координаты валидируются по диапазонам и не пишутся в structured logs. |
| `editMessageLiveLocation` | `bot/services/edit_message_live_location.py`, `/editlivelocation` в `bot/handlers/commands.py` | Admin-flow обновления координат активной live location, ранее отправленной ботом, по `chat_id` + `message_id` или `inline_message_id`; используется изолированный raw Bot API helper для совместимости с pinned `aiogram==3.3.0`, координаты и optional `horizontal_accuracy`/`heading`/`proximity_alert_radius` валидируются до обращения к Telegram и не пишутся в structured logs. |
| `stopMessageLiveLocation` | `bot/services/stop_message_live_location.py`, `/stoplivelocation` в `bot/handlers/commands.py` | Admin-flow остановки активной live location, ранее отправленной ботом, по `chat_id` + `message_id` или `inline_message_id`; используется изолированный raw Bot API helper для совместимости с pinned `aiogram==3.3.0`, optional `reply_markup` поддержан на уровне сервиса, а structured logs фиксируют только target message и наличие inline/reply markup. |
| `editMessageChecklist` | `bot/services/edit_message_checklist.py`, `/editchecklist` в `bot/handlers/commands.py` | Admin-flow редактирования checklist message от имени подключенного business account по live `business_connection_id`, `chat_id`, `message_id` и replacement `InputChecklist`; используется изолированный raw Bot API helper, так как pinned `aiogram==3.3.0` не имеет typed wrapper для этого метода Bot API 10.0; команда доступна только в `TELEGRAM_ADMIN_CHAT_IDS`, валидирует title/tasks как `/checklist`, не требует специальных update types и не пишет title/task text в structured logs. |
| `editMessageReplyMarkup` | `bot/services/edit_message_reply_markup.py`, `/editreplymarkup` в `bot/handlers/commands.py` | Admin-flow обновления только inline keyboard у сообщения, ранее отправленного ботом, по `chat_id` + `message_id` или `inline_message_id`; используется изолированный raw Bot API helper, команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS`, поддерживает очистку keyboard и empty inline keyboard, а structured logs фиксируют только target message и наличие reply markup. |
| `sendMediaGroup` | `bot/services/send_media_group.py`, `/mediagroup` в `bot/handlers/commands.py` | Admin-flow отправки 2-10 медиа в текущий чат как единого альбома (media group) по URL или `file_id`, через typed aiogram API; все элементы одного типа (photo/video/document/audio), единый caption применяется к первому элементу. |
| `sendVenue` | `bot/services/send_venue.py`, `/venue` в `bot/handlers/commands.py` | Admin-flow отправки заведения (venue) — именованного места с названием и адресом, закрепленного на карте — в текущий чат по широте, долготе, title и address, через typed aiogram API; координаты валидируются по диапазонам, а сами координаты, title и address не пишутся в structured logs. |
| `sendPoll` | `bot/services/send_poll.py`, `/poll` в `bot/handlers/commands.py` | Admin-flow отправки нативного опроса (poll) — интерактивного вопроса с 2-10 вариантами ответа — в текущий чат, через typed aiogram API; длины вопроса (до 300) и вариантов (до 100) и их количество валидируются до обращения к Telegram, а сам вопрос и варианты ответа не пишутся в structured logs. |
| `stopPoll` | `bot/services/stop_poll.py`, `/stoppoll` в `bot/handlers/commands.py` | Admin-flow закрытия активного нативного опроса, ранее отправленного ботом, по `chat_id` и `message_id`, через typed aiogram API; `message_id` валидируется как positive id, команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS`, а structured logs фиксируют только target message и итоговый poll id/count без текста вопроса и вариантов. |
| `sendContact` | `bot/services/send_contact.py`, `/contact` в `bot/handlers/commands.py` | Admin-flow отправки телефонного контакта (contact) — имени с номером телефона, который получатель может сохранить в адресную книгу — в текущий чат, через typed aiogram API; phone_number и first_name обязательны, last_name опционален, а номер телефона и имя контакта не пишутся в structured logs. |
| `sendDice` | `bot/services/send_dice.py`, `/dice` в `bot/handlers/commands.py` | Admin-flow отправки анимированной кости (dice) — анимированного эмодзи со случайным значением, которое выбирает Telegram — в текущий чат, через typed aiogram API; опциональный emoji ограничен набором 🎲/🎯/🏀/⚽/🎳/🎰 и валидируется до обращения к Telegram, без аргумента отправляется 🎲. |
| `sendChecklist` | `bot/services/send_checklist.py`, `/checklist` в `bot/handlers/commands.py` | Admin-flow отправки чеклиста (checklist) — озаглавленного списка из 1-30 задач — в текущий чат от имени подключенного business account, через изолированный raw Bot API helper, так как pinned `aiogram==3.3.0` не имеет typed wrapper для этого метода Bot API 9.1; требует `business_connection_id`, длины title (до 255) и задач (до 100) и их количество валидируются до обращения к Telegram, а title и тексты задач не пишутся в structured logs. |
| `postStory` | `bot/services/post_story.py`, `/poststory` в `bot/handlers/commands.py` | Admin-flow публикации photo story от имени managed business account по `business_connection_id`; команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS`, требует Telegram business right `can_manage_stories`, принимает `active_period` только 21600/43200/86400/172800, caption до 2048 символов и использует изолированный raw Bot API helper для совместимости с pinned `aiogram==3.3.0`; специальных update types не требуется, так как сценарий запускается обычной командой из admin-чата, rollback выполняется удалением или архивированием story в Telegram. |
| `repostStory` | `bot/services/repost_story.py`, `/repoststory` в `bot/handlers/commands.py` | Admin-flow репоста story между managed business accounts по destination `business_connection_id`, source `from_chat_id`, `from_story_id` и `active_period`; команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS`, требует Telegram business right `can_manage_stories` для обоих business accounts, принимает `active_period` только 21600/43200/86400/172800 и использует изолированный raw Bot API helper для совместимости с pinned `aiogram==3.3.0`; source story должна быть ранее опубликована или репостнута этим ботом, rollback выполняется удалением или архивированием reposted story в Telegram. |
| `editStory` | `bot/services/edit_story.py`, `/editstory` в `bot/handlers/commands.py` | Admin-flow редактирования photo story, ранее опубликованной ботом от имени managed business account, по `business_connection_id`, `story_id`, replacement `photo_file_id` и optional caption; команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS`, требует Telegram business right `can_manage_stories`, валидирует positive `story_id` и caption до 2048 символов, использует изолированный raw Bot API helper для совместимости с pinned `aiogram==3.3.0`; специальных update types не требуется, rollback выполняется повторным `/editstory` с прежним media/caption или ручным edit/archive в Telegram. |
| `getBusinessConnection` | `bot/services/get_business_connection.py`, `/businessconnection` в `bot/handlers/commands.py` | Admin-flow получения `BusinessConnection` по live `business_connection_id`, через изолированный raw Bot API helper, так как pinned `aiogram==3.3.0` не имеет typed wrapper для этого метода Bot API 10.0; команда доступна только в `TELEGRAM_ADMIN_CHAT_IDS`, не падает обратно на `TELEGRAM_ALLOWED_CHAT_IDS`, показывает owner/user chat/lifecycle/can_reply/enabled metadata и не пишет owner-поля или полный объект в structured logs. |
| `getBusinessAccountStarBalance` | `bot/services/get_business_account_star_balance.py`, `/businessstarbalance` в `bot/handlers/commands.py` | Read-only admin-flow получения `StarAmount` для подключенного business account по live `business_connection_id`; используется изолированный raw Bot API helper, так как pinned `aiogram==3.3.0` не имеет typed wrapper для этого метода Bot API 10.0; команда доступна только в `TELEGRAM_ADMIN_CHAT_IDS`, не падает обратно на `TELEGRAM_ALLOWED_CHAT_IDS`, требует Telegram business right `can_view_gifts_and_stars`, а ownership/permission errors возвращаются оператору без retry; structured logs содержат connection id и форму результата, но не сумму Stars. |
| `transferBusinessAccountStars` | `bot/services/transfer_business_account_stars.py`, `/transferbusinessstars` в `bot/handlers/commands.py` | Destructive admin-flow перевода Telegram Stars с подключенного business account на баланс бота по live `business_connection_id` и положительному `star_count`; используется изолированный raw Bot API helper, так как pinned `aiogram==3.3.0` не имеет typed wrapper для этого метода Bot API 10.0; команда доступна только в `TELEGRAM_ADMIN_CHAT_IDS`, не падает обратно на `TELEGRAM_ALLOWED_CHAT_IDS`, требует явный `confirm`, Telegram business right `can_transfer_stars` и Telegram ownership/balance checks; structured logs содержат connection id, amount и форму ошибки. |
| `convertGiftToStars` | `bot/services/convert_gift_to_stars.py`, `/convertgiftstars` в `bot/handlers/commands.py` | Destructive admin-flow конвертации одного regular owned gift подключенного business account в Telegram Stars по live `business_connection_id` и `owned_gift_id`; используется изолированный raw Bot API helper, так как pinned `aiogram==3.3.0` не имеет typed wrapper для этого метода Bot API 10.0; команда доступна только в `TELEGRAM_ADMIN_CHAT_IDS`, не падает обратно на `TELEGRAM_ALLOWED_CHAT_IDS`, требует явный `confirm`, Telegram business right для конвертации gifts to Stars и Telegram ownership/eligibility checks; structured logs содержат connection id, owned gift id и форму ошибки. |
| `upgradeGift` | `bot/services/upgrade_gift.py`, `/upgradegift` в `bot/handlers/commands.py` | Destructive admin-flow upgrade одного owned gift подключенного business account по live `business_connection_id`, `owned_gift_id` и optional `keep_original_details`; используется изолированный raw Bot API helper, так как pinned `aiogram==3.3.0` не имеет typed wrapper для этого метода Bot API 10.0; команда доступна только в `TELEGRAM_ADMIN_CHAT_IDS`, не падает обратно на `TELEGRAM_ALLOWED_CHAT_IDS`, требует явный `confirm`, Telegram business right для transfer/upgrade gifts и Telegram ownership/balance/eligibility checks; structured logs содержат connection id, owned gift id, optional detail flag и форму ошибки. |
| `readBusinessMessage` | `bot/services/read_business_message.py`, `/readbusinessmessage` в `bot/handlers/commands.py` | Admin-flow отметки одного сообщения подключенного business account как прочитанного по live `business_connection_id` и положительному `message_id`, через изолированный raw Bot API helper, так как pinned `aiogram==3.3.0` не имеет typed wrapper для этого метода Bot API 10.0; команда доступна только в `TELEGRAM_ADMIN_CHAT_IDS`, не падает обратно на `TELEGRAM_ALLOWED_CHAT_IDS`, а Telegram ownership/rights errors возвращаются оператору без retry. |
| `deleteBusinessMessages` | `bot/services/delete_business_messages.py`, `/deletebusinessmessages` в `bot/handlers/commands.py` | Destructive admin-flow удаления 1-100 сообщений подключенного business account по live `business_connection_id` и положительным `message_ids`, через изолированный raw Bot API helper, так как pinned `aiogram==3.3.0` не имеет typed wrapper для этого метода Bot API 10.0; команда доступна только в `TELEGRAM_ADMIN_CHAT_IDS`, не падает обратно на `TELEGRAM_ALLOWED_CHAT_IDS`, требует явный `confirm`, а Telegram ownership/rights errors возвращаются оператору без retry; structured logs содержат connection id, count и error shape, но не содержимое сообщений. |
| `deleteMessage` | `bot/services/delete_message.py`, `/deletemessage` в `bot/handlers/commands.py` | Destructive admin-flow удаления одного сообщения по `chat_id` и положительному `message_id`, через typed aiogram API `Bot.delete_message`; команда доступна только в `TELEGRAM_ADMIN_CHAT_IDS`, не падает обратно на `TELEGRAM_ALLOWED_CHAT_IDS`, требует явный `confirm`, специальных update types не требует, так как запускается обычной командой из admin-чата; Telegram проверяет 48-часовое окно удаления, 24-часовое ограничение dice-сообщений в private chats, владение сообщением и право `can_delete_messages` для удаления чужих сообщений в группах/супергруппах/каналах; structured logs содержат target ids и форму ошибки, но не содержимое сообщений. |
| `deleteMessages` | `bot/services/delete_messages.py`, `/deletemessages` в `bot/handlers/commands.py` | Destructive admin-flow bulk cleanup по `chat_id` и положительным `message_ids`, через typed aiogram API `Bot.delete_messages`; Telegram принимает 1-100 ids за request, поэтому helper chunk-ит большие cleanup-наборы по 100 и продолжает обработку после ошибок отдельных chunks; команда доступна только в `TELEGRAM_ADMIN_CHAT_IDS`, не падает обратно на `TELEGRAM_ALLOWED_CHAT_IDS`, требует явный `confirm`, специальных update types не требует, так как запускается обычной командой из admin-чата; Telegram пропускает ненайденные сообщения и проверяет 48-часовое окно удаления, 24-часовое ограничение dice-сообщений в private chats, владение сообщением и право `can_delete_messages` для удаления чужих сообщений в группах/супергруппах/каналах; structured logs содержат target chat id, counts и форму ошибки, но не содержимое сообщений; rollback только ручной, `free-claude-code` не вызывается. |
| `setBusinessAccountProfilePhoto` | `bot/services/set_business_account_profile_photo.py`, `/setbusinessaccountprofilephoto` в `bot/handlers/commands.py` | Admin-flow установки static JPG profile photo подключенного business account по live `business_connection_id`, локальному `photo_path` и опциональному `public=true`; используется изолированный raw multipart Bot API helper, так как pinned `aiogram==3.3.0` не имеет typed wrapper для этого метода Bot API 10.0, а Telegram требует fresh upload через `InputProfilePhotoStatic`; команда доступна только в `TELEGRAM_ADMIN_CHAT_IDS`, не падает обратно на `TELEGRAM_ALLOWED_CHAT_IDS`, а Telegram ownership/`can_edit_profile_photo` errors возвращаются оператору без retry; structured logs содержат connection id, path, visibility flag и error shape, но не содержимое файла. |
| `removeBusinessAccountProfilePhoto` | `bot/services/remove_business_account_profile_photo.py`, `/removebusinessaccountprofilephoto` в `bot/handlers/commands.py` | Destructive admin-flow удаления main или public fallback profile photo подключенного business account по live `business_connection_id` и опциональному `public=true`; используется изолированный raw Bot API helper, так как pinned `aiogram==3.3.0` не имеет typed wrapper для этого метода Bot API 10.0; команда доступна только в `TELEGRAM_ADMIN_CHAT_IDS`, не падает обратно на `TELEGRAM_ALLOWED_CHAT_IDS`, требует явный `confirm`, а Telegram ownership/`can_edit_profile_photo` errors возвращаются оператору без retry; structured logs содержат connection id, visibility flag и error shape. |
| `setBusinessAccountGiftSettings` | `bot/services/set_business_account_gift_settings.py`, `/setbusinessaccountgiftsettings` в `bot/handlers/commands.py` | Admin-flow изменения incoming gift privacy settings подключенного business account по live `business_connection_id`, обязательному `show_gift_button` и полному объекту `AcceptedGiftTypes`; используется изолированный raw Bot API helper, так как pinned `aiogram==3.3.0` не имеет typed wrapper для этого метода Bot API 10.0; команда доступна только в `TELEGRAM_ADMIN_CHAT_IDS`, не падает обратно на `TELEGRAM_ALLOWED_CHAT_IDS`, а Telegram ownership/`can_change_gift_settings` errors возвращаются оператору без retry; structured logs содержат connection id, gift button flag, count enabled gift types и error shape. |
| `getManagedBotToken` | `bot/services/get_managed_bot_token.py`, `/managedbottoken` в `bot/handlers/commands.py` | Admin-flow получения live token управляемого бота по положительному `user_id`, через изолированный raw Bot API helper, так как pinned `aiogram==3.3.0` не имеет typed wrapper для managed-bot методов Bot API 9.6; команда доступна только в `TELEGRAM_ADMIN_CHAT_IDS`, не падает обратно на `TELEGRAM_ALLOWED_CHAT_IDS`, требует trusted source для id из `managed_bot`/`managed_bot_created`, показывает токен только в ответе admin-чата и не пишет токен в structured logs. |
| `getManagedBotAccessSettings` | `bot/services/get_managed_bot_access_settings.py`, `/managedbotaccess` в `bot/handlers/commands.py` | Admin-flow чтения `BotAccessSettings` управляемого бота по положительному `user_id`, через изолированный raw Bot API helper, так как pinned `aiogram==3.3.0` не имеет typed wrapper для managed-bot access settings Bot API 10.0; команда доступна только в `TELEGRAM_ADMIN_CHAT_IDS`, не падает обратно на `TELEGRAM_ALLOWED_CHAT_IDS`, требует trusted source для id из `managed_bot`/`managed_bot_created`, показывает restricted flag и allowlist summary в admin-чате и не пишет returned user objects в structured logs. |
| `setManagedBotAccessSettings` | `bot/services/set_managed_bot_access_settings.py`, `/setmanagedbotaccess` в `bot/handlers/commands.py` | Admin-flow изменения `BotAccessSettings` управляемого бота по положительному `user_id`, через изолированный raw Bot API helper, так как pinned `aiogram==3.3.0` не имеет typed wrapper для managed-bot access settings Bot API 10.0; команда доступна только в `TELEGRAM_ADMIN_CHAT_IDS`, не падает обратно на `TELEGRAM_ALLOWED_CHAT_IDS`, требует trusted source для id из `managed_bot`/`managed_bot_created`, требует явный `confirm`, принимает режим `restricted`/`open` и optional allowlist user ids, а structured logs содержат только `user_id`, restricted flag и count. |
| `replaceManagedBotToken` | `bot/services/replace_managed_bot_token.py`, `/replacemanagedbottoken` в `bot/handlers/commands.py` | Admin-flow ротации live token управляемого бота по положительному `user_id`, через изолированный raw Bot API helper, так как pinned `aiogram==3.3.0` не имеет typed wrapper для managed-bot методов Bot API 9.6; команда доступна только в `TELEGRAM_ADMIN_CHAT_IDS`, не падает обратно на `TELEGRAM_ALLOWED_CHAT_IDS`, требует trusted source для id из `managed_bot`/`managed_bot_created` и явный `confirm`, показывает новый токен только в ответе admin-чата, не пишет токены в structured logs, а rollback выполняется повторной ротацией или заранее сохраненным прежним credential, если Telegram еще принимает его. |
| `sendChatAction` | `bot/services/send_chat_action.py`, `keep_chat_action` в `bot/handlers/chat.py` и `/chataction` в `bot/handlers/commands.py` | Показ chat action (transient-статуса вроде `typing…`) в чате через typed aiogram API. Автоматически показывается и обновляется, пока Claude/proxy обрабатывает входящее сообщение (управляется `TELEGRAM_CHAT_ACTION_ENABLED`); admin-команда `/chataction [action]` запускает action вручную, где action ограничен набором поддерживаемых значений и валидируется до обращения к Telegram. |
| `sendMessageDraft` | `bot/services/send_message_draft.py`, `handle_streaming_with_draft` в `bot/handlers/chat.py` и `/messagedraft` в `bot/handlers/commands.py` | Стриминг частичного ответа через эфемерный draft preview (временный ~30-секундный предпросмотр) в private chat как альтернатива частым `editMessageText`, через изолированный raw Bot API helper, так как pinned `aiogram==3.3.0` не имеет typed wrapper для этого метода Bot API 10.0; включается флагом `TELEGRAM_MESSAGE_DRAFT_ENABLED` и работает только в private chats, финальный ответ затем сохраняется обычным `sendMessage`. Admin-команда `/messagedraft [text]` запускает draft вручную; `draft_id` обязан быть ненулевым, а длина текста (до 4096) валидируется до обращения к Telegram, и текст draft не пишется в structured logs. |
| `getUserProfilePhotos` | `bot/services/get_user_profile_photos.py`, `/userprofilephotos` в `bot/handlers/commands.py` | Admin-flow получения фотографий профиля Telegram-пользователя по `user_id`, через typed aiogram API; не требует особых прав бота, Telegram может вернуть ошибку при ограниченной приватности пользователя; опциональные `offset` и `limit` (1-100) позволяют постранично получать фотографии, каждая в нескольких разрешениях; `user_id` и `file_id` фотографий не пишутся в structured logs. |
| `setMessageReaction` | `bot/services/set_message_reaction.py`, `/react` в `bot/handlers/commands.py` | Admin-flow установки emoji-реакции на сообщение в текущем чате по `message_id`, через typed aiogram API (поддерживается с `aiogram==3.3.0`, Bot API 7.0); реакция задаётся стандартным emoji из фиксированного набора Telegram или опускается для удаления всех реакций бота; опциональный флаг `big` включает увеличенную анимацию; служебные сообщения не поддерживают реакции, в альбомах нужно реагировать на первое сообщение; не-premium боты могут ставить не более одной реакции на сообщение. |
| `setUserEmojiStatus` | `bot/services/set_user_emoji_status.py`, `/setemojistatus` в `bot/handlers/commands.py` | Admin-flow установки или удаления emoji-статуса Telegram-пользователя по `user_id`, через typed aiogram API (Bot API 10.0); пользователь должен предварительно разрешить боту управление своим emoji-статусом через метод Mini App `requestEmojiStatusAccess` — без этого Telegram вернёт ошибку; передача пустой строки в качестве `custom_emoji_id` удаляет текущий статус; бот не требует административных прав; `user_id` не пишется в structured logs уровня "info". |
| `getUserProfileAudios` | `bot/services/get_user_profile_audios.py`, `/userprofileaudios` в `bot/handlers/commands.py` | Admin-flow получения аудио профиля Telegram-пользователя по `user_id`, через typed aiogram API (Bot API 9.4, поддерживается в `aiogram==3.28`); не требует особых прав бота, Telegram может вернуть ошибку при ограниченной приватности пользователя; опциональные `offset` и `limit` (1-100) позволяют постранично получать аудио; для каждого трека выводятся `file_id`, длительность, исполнитель, название и имя файла при наличии; `user_id` и `file_id` аудио не пишутся в structured logs. |
| `banChatMember` | `bot/services/ban_chat_member.py`, `/banchatmember` в `bot/handlers/commands.py` | Admin-flow блокировки пользователя в группе, супергруппе или канале по `chat_id` и `user_id`, через typed aiogram API; команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS` без fallback, бот должен быть администратором целевого чата с правом `can_restrict_members`; опциональные `until_date_unix` и `revoke=true|false` управляют временной блокировкой и удалением сообщений, а ошибки Telegram возвращаются оператору. |
| `banChatSenderChat` | `bot/services/ban_chat_sender_chat.py`, `/banchatsenderchat` в `bot/handlers/commands.py` | Admin-flow блокировки channel/sender chat в супергруппе или канале по `chat_id` и `sender_chat_id`, через typed aiogram API; команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS` без fallback и deny-by-default при пустом списке, бот должен быть администратором целевого чата с правом `can_restrict_members`; специальных update types не требуется, так как сценарий запускается обычной командой из admin-чата, а ошибки Telegram возвращаются оператору. |
| `unbanChatMember` | `bot/services/unban_chat_member.py`, `/unbanchatmember` в `bot/handlers/commands.py` | Admin-flow разблокировки пользователя в группе, супергруппе или канале по `chat_id` и `user_id`, через typed aiogram API; команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS` без fallback и deny-by-default при пустом списке, бот должен быть администратором целевого чата с правом `can_restrict_members`; опциональный `only_if_banned=true|false` передается как `only_if_banned`, а ошибки Telegram возвращаются оператору. |
| `unbanChatSenderChat` | `bot/services/unban_chat_sender_chat.py`, `/unbanchatsenderchat` в `bot/handlers/commands.py` | Admin-flow разблокировки channel/sender chat в супергруппе или канале по `chat_id` и `sender_chat_id`, через typed aiogram API; команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS` без fallback и deny-by-default при пустом списке, бот должен быть администратором целевого чата с правом `can_restrict_members`; специальных update types не требуется, так как сценарий запускается обычной командой из admin-чата, а ошибки Telegram возвращаются оператору. |
| `restrictChatMember` | `bot/services/restrict_chat_member.py`, `/restrictchatmember` в `bot/handlers/commands.py` | Admin-flow ограничения или восстановления прав пользователя в группе/супергруппе по `chat_id`, `user_id` и preset (`mute`, `readonly`, `unrestrict`), через typed aiogram API; команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS` без fallback и deny-by-default при пустом списке, бот должен быть администратором целевого чата с правом `can_restrict_members`; опциональные `until_date_unix` и `independent=true|false` управляют сроком ограничения и `use_independent_chat_permissions`, а ошибки Telegram возвращаются оператору. |
| `setChatPermissions` | `bot/services/set_chat_permissions.py`, `/setchatpermissions` в `bot/handlers/commands.py` | Admin-flow изменения default permissions всех не-администраторов в группе/супергруппе по `chat_id` и preset (`closed`, `text`, `media`, `open`), через typed aiogram API; команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS` без fallback и deny-by-default при пустом списке, бот должен быть администратором целевого чата с правом `can_restrict_members`; опциональный `independent=true|false` передается как `use_independent_chat_permissions`, специальных update types не требуется, так как сценарий запускается обычной командой из admin-чата, а ошибки Telegram возвращаются оператору. |
| `setChatPhoto` | `bot/services/set_chat_photo.py`, `/setchatphoto` в `bot/handlers/commands.py` | Admin-flow установки новой фотографии группы или супергруппы по `chat_id` и локальному `photo_path`; команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS` без fallback и deny-by-default при пустом списке, бот должен быть администратором целевого чата с правом изменять информацию чата; используется typed aiogram API `Bot.set_chat_photo` с `FSInputFile`, потому что Telegram требует загрузку нового файла, а не URL или `file_id`; специальных update types не требуется, rollback выполняется повторной установкой прежней фотографии, а ошибки Telegram по правам, неизвестному чату, файлу или валидации изображения возвращаются оператору. |
| `setMyProfilePhoto` | `bot/services/set_my_profile_photo.py`, `/setmyprofilephoto` в `bot/handlers/commands.py` | Admin-flow установки новой фотографии профиля бота из локального `photo_path`; команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS` без fallback и deny-by-default при пустом списке; используется изолированный raw multipart Bot API helper, так как pinned `aiogram==3.3.0` не имеет typed wrapper для этого метода Bot API 10.0, а Telegram требует загрузку нового файла, а не URL или `file_id`; специальных update types и прав в чатах не требуется, rollback выполняется повторной установкой прежней фотографии или ручным удалением в Telegram/BotFather, а ошибки Telegram по файлу или валидации изображения возвращаются оператору. |
| `removeMyProfilePhoto` | `bot/services/remove_my_profile_photo.py`, `/removemyprofilephoto` в `bot/handlers/commands.py` | Admin-flow удаления текущей фотографии профиля бота; команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS` без fallback и deny-by-default при пустом списке, требует явный `confirm`, потому что меняет публичный профиль бота; используется изолированный raw Bot API helper, так как pinned `aiogram==3.3.0` не имеет typed wrapper для этого метода Bot API 10.0; параметров метода нет, специальных update types и прав в чатах не требуется, rollback выполняется повторной установкой прежней фотографии через `/setmyprofilephoto <photo_path>`, а ошибки Telegram и rate-limit ответы возвращаются оператору. |
| `setChatStickerSet` | `bot/services/set_chat_sticker_set.py`, `/setchatstickerset` в `bot/handlers/commands.py` | Admin-flow установки sticker set для супергруппы по `chat_id` и `sticker_set_name`; команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS` без fallback и deny-by-default при пустом списке, бот должен быть администратором целевой супергруппы с правом изменять информацию чата; используется typed aiogram API `Bot.set_chat_sticker_set`, специальных update types не требуется, так как сценарий запускается обычной командой из admin-чата, а ошибки Telegram по правам, типу чата, неизвестному чату или невалидному sticker set возвращаются оператору. |
| `deleteChatStickerSet` | `bot/services/delete_chat_sticker_set.py`, `/deletechatstickerset` в `bot/handlers/commands.py` | Admin-flow удаления sticker set из супергруппы по `chat_id`; команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS` без fallback и deny-by-default при пустом списке, бот должен быть администратором целевой супергруппы с правом изменять информацию чата; используется typed aiogram API `Bot.delete_chat_sticker_set`, специальных update types не требуется, так как сценарий запускается обычной командой из admin-чата; rollback выполняется ручным повторным `/setchatstickerset` с прежним `sticker_set_name`, а ошибки Telegram по правам, типу чата, неизвестному чату или отсутствующему sticker set возвращаются оператору. |
| `pinChatMessage` | `bot/services/pin_chat_message.py`, `/pinchatmessage` в `bot/handlers/commands.py` | Admin-flow закрепления сообщения в группе, супергруппе или канале по `chat_id`, `message_id` и optional notification flag (`silent`, `loud`), через typed aiogram API `Bot.pin_chat_message`; команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS` без fallback и deny-by-default при пустом списке, бот должен быть администратором целевого чата с `can_pin_messages` в группах/супергруппах или `can_edit_messages` в каналах; специальных update types не требуется, так как сценарий запускается обычной командой из admin-чата, rollback выполняется ручным откреплением или `/unpinchatmessage`, а ошибки Telegram по правам, неизвестному чату или сообщению возвращаются оператору. |
| `unpinChatMessage` | `bot/services/unpin_chat_message.py`, `/unpinchatmessage` в `bot/handlers/commands.py` | Admin-flow открепления конкретного или последнего закрепленного сообщения в группе, супергруппе или канале по `chat_id` и optional `message_id`, через typed aiogram API `Bot.unpin_chat_message`; команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS` без fallback и deny-by-default при пустом списке, бот должен быть администратором целевого чата с `can_pin_messages` в группах/супергруппах или `can_edit_messages` в каналах; специальных update types не требуется, так как сценарий запускается обычной командой из admin-чата, rollback выполняется ручным повторным закреплением, а ошибки Telegram по правам, неизвестному чату или незакрепленному сообщению возвращаются оператору. |
| `unpinAllChatMessages` | `bot/services/unpin_all_chat_messages.py`, `/unpinallchatmessages` в `bot/handlers/commands.py` | Admin-flow массового открепления всех закрепленных сообщений в группе, супергруппе или канале по `chat_id`, через typed aiogram API `Bot.unpin_all_chat_messages`; команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS` без fallback и deny-by-default при пустом списке, бот должен быть администратором целевого чата с `can_pin_messages` в группах/супергруппах или `can_edit_messages` в каналах; специальных update types не требуется, так как сценарий запускается обычной командой из admin-чата, rollback выполняется ручным повторным закреплением нужных сообщений, а ошибки Telegram по правам или неизвестному чату возвращаются оператору. |
| `promoteChatMember` | `bot/services/promote_chat_member.py`, `/promotechatmember` в `bot/handlers/commands.py` | Admin-flow повышения или понижения пользователя в группе, супергруппе или канале по `chat_id`, `user_id` и preset (`moderator`, `manager`, `demote`), через typed aiogram API; команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS` без fallback и deny-by-default при пустом списке, бот должен быть администратором целевого чата с правом `can_promote_members` и может выдавать только свои права; ошибки Telegram возвращаются оператору. |
| `getChatMemberCount` | `bot/services/get_chat_member_count.py`, `/getchatmembercount` в `bot/handlers/commands.py` | Admin-flow получения количества участников группы, супергруппы или канала по `chat_id`, через typed aiogram API `Bot.get_chat_member_count`; команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS` без fallback и deny-by-default при пустом списке, бот должен иметь доступ к целевому чату, обычно быть его участником; специальных update types не требуется, так как сценарий запускается обычной командой из admin-чата, а ошибки Telegram по неизвестному чату, отсутствующему доступу или rate limit возвращаются оператору. |
| `getChatMember` | `bot/services/get_chat_member.py`, `/getchatmember` в `bot/handlers/commands.py` | Admin-flow просмотра статуса и прав одного участника группы, супергруппы или канала по `chat_id` и `user_id`, через typed aiogram API `Bot.get_chat_member`; команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS` без fallback и deny-by-default при пустом списке, бот должен иметь доступ к целевому чату и может требовать administrator status в зависимости от типа чата и privacy settings; ответ выводит requested ids, status, display name, username, custom title, anonymity/member flags и включенные permission fields, специальных update types не требуется, так как сценарий запускается обычной командой из admin-чата, а ошибки Telegram по неизвестному чату, отсутствующему пользователю, недостаточным правам или rate limit возвращаются оператору. |
| `getChatAdministrators` | `bot/services/get_chat_administrators.py`, `/getchatadministrators` в `bot/handlers/commands.py` | Admin-flow аудита администраторов группы, супергруппы или канала по `chat_id`, через typed aiogram API `Bot.get_chat_administrators`; команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS` без fallback и deny-by-default при пустом списке, бот должен иметь доступ к целевому чату и может требовать administrator status в зависимости от типа чата и privacy settings; ответ выводит количество администраторов, user id, display name, username, status, custom title, anonymity flag и включенные admin rights, специальных update types не требуется, так как сценарий запускается обычной командой из admin-чата, а ошибки Telegram по неизвестному чату, отсутствующему доступу, недостаточным правам или rate limit возвращаются оператору. |
| `getForumTopicIconStickers` | `bot/services/get_forum_topic_icon_stickers.py`, `/forumtopiciconstickers` в `bot/handlers/commands.py` | Admin-flow просмотра custom emoji stickers, которые Telegram разрешает использовать как иконки forum topics; команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS` без fallback и deny-by-default при пустом списке, метод не принимает параметров и не требует специальных update types, так как сценарий запускается обычной командой из admin-чата; используется изолированный raw Bot API helper для совместимости с pinned `aiogram==3.3.0`, результат парсится в aiogram `Sticker` и выводит количество, emoji, `custom_emoji_id` и sticker set name; команда не вызывает `free-claude-code`, не меняет состояние Telegram и нужна для модераторского triage перед созданием или редактированием тем в супергруппах, а ошибки транспорта, Telegram API или rate limit возвращаются оператору. |
| `createForumTopic` | `bot/services/create_forum_topic.py`, `/createforumtopic` в `bot/handlers/commands.py` | Admin-flow создания forum topic в супергруппе по `chat_id`, обязательному `name` и optional `icon_color`/`icon_custom_emoji_id`; команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS` без fallback и deny-by-default при пустом списке, проверяет обязательность имени и лимит до 128 символов; бот должен быть администратором целевой супергруппы с правом manage topics, специальных update types не требуется, так как сценарий запускается обычной командой из admin-чата; используется изолированный raw Bot API helper для совместимости с pinned `aiogram==3.3.0`, результат парсится в aiogram `ForumTopic`, а ошибки транспорта, Telegram API или rate limit возвращаются оператору; команда не вызывает `free-claude-code`, меняет состояние только указанной супергруппы, rollback выполняется ручным удалением созданной темы в Telegram или будущей lifecycle-командой. |
| `editForumTopic` | `bot/services/edit_forum_topic.py`, `/editforumtopic` в `bot/handlers/commands.py` | Admin-flow редактирования forum topic в супергруппе по `chat_id` и `message_thread_id`; команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS` без fallback и deny-by-default при пустом списке, принимает `name=<text>` и/или `icon_custom_emoji_id=<id>`, проверяет наличие хотя бы одного изменяемого поля и лимит имени до 128 символов; используется изолированный raw Bot API helper для совместимости с pinned `aiogram==3.3.0`, так как метод отсутствует в текущем typed API, а ошибки транспорта, Telegram API или rate limit возвращаются оператору; команда не вызывает `free-claude-code`, меняет состояние только указанной темы, rollback выполняется повторным `/editforumtopic` с прежним именем или `icon_custom_emoji_id`. |
| `editGeneralForumTopic` | `bot/services/edit_general_forum_topic.py`, `/editgeneralforumtopic` в `bot/handlers/commands.py` | Admin-flow переименования General forum topic в forum-enabled супергруппе по `chat_id` и обязательному `name`; команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS` без fallback и deny-by-default при пустом списке, проверяет обязательность имени и лимит до 128 символов; бот должен быть администратором целевой супергруппы с правом manage topics, специальных update types не требуется, так как сценарий запускается обычной командой из admin-чата; используется изолированный raw Bot API helper для совместимости с pinned `aiogram==3.3.0`, так как метод отсутствует в текущем typed API, а ошибки транспорта, Telegram API или rate limit возвращаются оператору; команда не вызывает `free-claude-code`, меняет только имя General topic в указанной супергруппе, rollback выполняется повторным `/editgeneralforumtopic` с прежним именем. |
| `closeForumTopic` | `bot/services/close_forum_topic.py`, `/closeforumtopic` в `bot/handlers/commands.py` | Admin-flow закрытия forum topic в супергруппе по `chat_id` и `message_thread_id`; команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS` без fallback и deny-by-default при пустом списке, проверяет целочисленный positive `message_thread_id`; бот должен быть администратором целевой супергруппы с правом manage topics, специальных update types не требуется, так как сценарий запускается обычной командой из admin-чата; используется изолированный raw Bot API helper для совместимости с pinned `aiogram==3.3.0`, результат Telegram должен быть `True`, а ошибки транспорта, Telegram API или rate limit возвращаются оператору; команда не вызывает `free-claude-code`, меняет состояние только указанной темы, rollback выполняется `/reopenforumtopic` после проверки того же `chat_id` и `message_thread_id`. |
| `closeGeneralForumTopic` | `bot/services/close_general_forum_topic.py`, `/closegeneralforumtopic` в `bot/handlers/commands.py` | Admin-flow закрытия General forum topic в супергруппе по `chat_id`; команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS` без fallback и deny-by-default при пустом списке, проверяет обязательный целочисленный `chat_id`; бот должен быть администратором целевой супергруппы с правом manage topics, специальных update types не требуется, так как сценарий запускается обычной командой из admin-чата; используется изолированный raw Bot API helper для совместимости с pinned `aiogram==3.3.0`, результат Telegram должен быть `True`, а ошибки транспорта, Telegram API или rate limit возвращаются оператору; команда не вызывает `free-claude-code`, меняет состояние только General topic в указанной супергруппе, rollback выполняется `/reopengeneralforumtopic` после проверки того же `chat_id`. |
| `reopenForumTopic` | `bot/services/reopen_forum_topic.py`, `/reopenforumtopic` в `bot/handlers/commands.py` | Admin-flow повторного открытия закрытой forum topic в супергруппе по `chat_id` и `message_thread_id`; команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS` без fallback и deny-by-default при пустом списке, проверяет целочисленный positive `message_thread_id`; бот должен быть администратором целевой супергруппы с правом manage topics, специальных update types не требуется, так как сценарий запускается обычной командой из admin-чата; используется изолированный raw Bot API helper для совместимости с pinned `aiogram==3.3.0`, результат Telegram должен быть `True`, а ошибки транспорта, Telegram API или rate limit возвращаются оператору; команда не вызывает `free-claude-code`, меняет состояние только указанной темы, rollback выполняется ручным повторным закрытием темы в Telegram или будущей lifecycle-командой. |
| `reopenGeneralForumTopic` | `bot/services/reopen_general_forum_topic.py`, `/reopengeneralforumtopic` в `bot/handlers/commands.py` | Admin-flow повторного открытия General forum topic в супергруппе по `chat_id`; команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS` без fallback и deny-by-default при пустом списке, проверяет обязательный целочисленный `chat_id`; бот должен быть администратором целевой супергруппы с правом manage topics, специальных update types не требуется, так как сценарий запускается обычной командой из admin-чата; используется изолированный raw Bot API helper для совместимости с pinned `aiogram==3.3.0`, результат Telegram должен быть `True`, а ошибки транспорта, Telegram API или rate limit возвращаются оператору; команда не вызывает `free-claude-code`, меняет состояние только General topic в указанной супергруппе, rollback выполняется `/closegeneralforumtopic` после проверки того же `chat_id`. |
| `hideGeneralForumTopic` | `bot/services/hide_general_forum_topic.py`, `/hidegeneralforumtopic` в `bot/handlers/commands.py` | Admin-flow скрытия General forum topic в супергруппе по `chat_id`; команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS` без fallback и deny-by-default при пустом списке, проверяет обязательный целочисленный `chat_id`; бот должен быть администратором целевой супергруппы с правом manage topics, специальных update types не требуется, так как сценарий запускается обычной командой из admin-чата; используется изолированный raw Bot API helper для совместимости с pinned `aiogram==3.3.0`, результат Telegram должен быть `True`, а ошибки транспорта, Telegram API или rate limit возвращаются оператору; команда не вызывает `free-claude-code`, меняет только видимость General topic в указанной супергруппе, rollback выполняется `/unhidegeneralforumtopic` после проверки того же `chat_id`. |
| `unhideGeneralForumTopic` | `bot/services/unhide_general_forum_topic.py`, `/unhidegeneralforumtopic` в `bot/handlers/commands.py` | Admin-flow возврата видимости General forum topic в супергруппе по `chat_id`; команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS` без fallback и deny-by-default при пустом списке, проверяет обязательный целочисленный `chat_id`; бот должен быть администратором целевой супергруппы с правом manage topics, специальных update types не требуется, так как сценарий запускается обычной командой из admin-чата; используется изолированный raw Bot API helper для совместимости с pinned `aiogram==3.3.0`, результат Telegram должен быть `True`, а ошибки транспорта, Telegram API или rate limit возвращаются оператору; команда не вызывает `free-claude-code`, меняет только видимость General topic в указанной супергруппе, rollback выполняется `/hidegeneralforumtopic` после проверки того же `chat_id`. |
| `deleteForumTopic` | `bot/services/delete_forum_topic.py`, `/deleteforumtopic` в `bot/handlers/commands.py` | Admin-flow удаления forum topic в супергруппе по `chat_id` и `message_thread_id`; команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS` без fallback и deny-by-default при пустом списке, проверяет целочисленный positive `message_thread_id`; бот должен быть администратором целевой супергруппы с правом manage topics, специальных update types не требуется, так как сценарий запускается обычной командой из admin-чата; используется изолированный raw Bot API helper для совместимости с pinned `aiogram==3.3.0`, результат Telegram должен быть `True`, а ошибки транспорта, Telegram API или rate limit возвращаются оператору; команда не вызывает `free-claude-code`, удаляет только указанную тему, rollback операционный и неполный: пересоздать тему через `/createforumtopic` и перенести или скопировать нужные сообщения вручную. |
| `unpinAllForumTopicMessages` | `bot/services/unpin_all_forum_topic_messages.py`, `/unpinallforumtopicmessages` в `bot/handlers/commands.py` | Admin-flow массового открепления всех закрепленных сообщений в конкретной forum topic супергруппы по `chat_id` и `message_thread_id`; команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS` без fallback и deny-by-default при пустом списке, проверяет целочисленный positive `message_thread_id`; бот должен быть администратором целевой супергруппы с правом manage topics, специальных update types не требуется, так как сценарий запускается обычной командой из admin-чата; используется изолированный raw Bot API helper для совместимости с pinned `aiogram==3.3.0`, результат Telegram должен быть `True`, а ошибки транспорта, Telegram API или rate limit возвращаются оператору; команда не вызывает `free-claude-code`, меняет только pinned-message state указанной темы, rollback выполняется ручным повторным закреплением нужных сообщений в Telegram или `/pinchatmessage`. |
| `unpinAllGeneralForumTopicMessages` | `bot/services/unpin_all_general_forum_topic_messages.py`, `/unpinallgeneralforumtopicmessages` в `bot/handlers/commands.py` | Admin-flow массового открепления всех закрепленных сообщений в General forum topic супергруппы по `chat_id`; команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS` без fallback и deny-by-default при пустом списке, проверяет обязательный целочисленный `chat_id`; бот должен быть администратором целевой forum-enabled супергруппы с правом manage topics, специальных update types не требуется, так как сценарий запускается обычной командой из admin-чата; используется изолированный raw Bot API helper для совместимости с pinned `aiogram==3.3.0`, метод принимает только `chat_id`, результат Telegram должен быть `True`, а ошибки транспорта, Telegram API или rate limit возвращаются оператору; команда не вызывает `free-claude-code`, меняет только pinned-message state General topic, rollback выполняется ручным повторным закреплением нужных сообщений в Telegram или `/pinchatmessage`. |
| `getUserPersonalChatMessages` | `bot/services/get_user_personal_chat_messages.py`, `/userpersonalchatmessages` в `bot/handlers/commands.py` | Admin-flow просмотра последних сообщений из personal chat между пользователем и ботом по `user_id` и `limit` 1-100, через typed aiogram API `Bot.get_user_personal_chat_messages`; команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS` без fallback и deny-by-default при пустом списке, так как может раскрывать приватные conversation metadata; ответ выводит количество сообщений и базовые metadata (`message_id`, chat id/type/title, date), специальных update types не требуется, так как сценарий запускается обычной командой из admin-чата, а ошибки Telegram по неизвестному пользователю, недоступной истории, правам или rate limit возвращаются оператору. |
| `exportChatInviteLink` | `bot/services/export_chat_invite_link.py`, `/exportchatinvitelink` в `bot/handlers/commands.py` | Admin-flow ротации и получения primary invite link группы, супергруппы или канала по `chat_id`, через typed aiogram API; команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS` без fallback и deny-by-default при пустом списке, бот должен быть администратором целевого чата с правом `can_invite_users`; успешный вызов отзывает ранее сгенерированную primary invite link, специальных update types не требуется, так как сценарий запускается обычной командой из admin-чата, а ошибки Telegram возвращаются оператору. |
| `leaveChat` | `bot/services/leave_chat.py`, `/leavechat` в `bot/handlers/commands.py` | Destructive admin-flow вывода бота из группы, супергруппы или канала по `chat_id`, через typed aiogram API `Bot.leave_chat`; команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS` без fallback и deny-by-default при пустом списке, требует явного `confirm`, бот должен быть текущим участником целевого чата; специальных update types не требуется, так как сценарий запускается обычной командой из admin-чата, rollback выполняется ручным добавлением бота обратно и восстановлением прав, а ошибки Telegram возвращаются оператору. |
| `approveChatJoinRequest` | `bot/services/approve_chat_join_request.py`, `/approvechatjoinrequest` в `bot/handlers/commands.py` | Admin-flow одобрения pending join request пользователя в группе, супергруппе или канале по `chat_id` и `user_id`; команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS` без fallback и deny-by-default при пустом списке, бот должен быть администратором целевого чата с правом `can_invite_users`; используется typed aiogram API, если runtime его предоставляет, иначе изолированный raw Bot API helper для совместимости с pinned `aiogram==3.3.0`; специальных update types для самой команды не требуется, так как сценарий запускается обычной командой из admin-чата, а ошибки Telegram по правам, отсутствующей заявке или rate limit возвращаются оператору. |
| `declineChatJoinRequest` | `bot/services/decline_chat_join_request.py`, `/declinechatjoinrequest` в `bot/handlers/commands.py` | Admin-flow отклонения pending join request пользователя в группе, супергруппе или канале по `chat_id` и `user_id`; команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS` без fallback и deny-by-default при пустом списке, бот должен быть администратором целевого чата с правом `can_invite_users`; используется typed aiogram API, если runtime его предоставляет, иначе изолированный raw Bot API helper для совместимости с pinned `aiogram==3.3.0`; специальных update types для самой команды не требуется, так как сценарий запускается обычной командой из admin-чата, а ошибки Telegram по правам, отсутствующей заявке или rate limit возвращаются оператору. |
| `createChatInviteLink` | `bot/services/create_chat_invite_link.py`, `/createchatinvitelink` в `bot/handlers/commands.py` | Admin-flow создания дополнительной invite link группы, супергруппы или канала по `chat_id` и опциям `name`, `expire_date`, `member_limit`, `creates_join_request`; команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS` без fallback и deny-by-default при пустом списке, бот должен быть администратором целевого чата с правом `can_invite_users`; используется typed aiogram API, если runtime его предоставляет, иначе изолированный raw Bot API helper для совместимости с pinned `aiogram==3.3.0`; `member_limit` валидируется в диапазоне 1-99999, `creates_join_request=true` нельзя совмещать с `member_limit`, специальных update types не требуется, а ошибки Telegram возвращаются оператору. |
| `editChatInviteLink` | `bot/services/edit_chat_invite_link.py`, `/editchatinvitelink` в `bot/handlers/commands.py` | Admin-flow изменения существующей non-primary invite link группы, супергруппы или канала по `chat_id`, `invite_link` и опциям `name`, `expire_date`, `member_limit`, `creates_join_request`; команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS` без fallback и deny-by-default при пустом списке, бот должен быть администратором целевого чата с правом `can_invite_users`; используется typed aiogram API, если runtime его предоставляет, иначе изолированный raw Bot API helper для совместимости с pinned `aiogram==3.3.0`; `member_limit` валидируется в диапазоне 1-99999, `creates_join_request=true` нельзя совмещать с `member_limit`, специальных update types не требуется, а ошибки Telegram возвращаются оператору. |
| `revokeChatInviteLink` | `bot/services/revoke_chat_invite_link.py`, `/revokechatinvitelink` в `bot/handlers/commands.py` | Admin-flow отзыва invite link, созданной ботом, для группы, супергруппы или канала по `chat_id` и `invite_link`; если отзывается primary link, Telegram автоматически генерирует новую; команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS` без fallback и deny-by-default при пустом списке, бот должен быть администратором целевого чата с правом `can_invite_users`; используется typed aiogram API, если runtime его предоставляет, иначе изолированный raw Bot API helper для совместимости с pinned `aiogram==3.3.0`; специальных update types не требуется, так как сценарий запускается обычной командой из admin-чата, а ошибки Telegram по правам или несуществующей ссылке возвращаются оператору. |
| `createChatSubscriptionInviteLink` | `bot/services/create_chat_subscription_invite_link.py`, `/createchatsubscriptioninvitelink` в `bot/handlers/commands.py` | Admin-flow создания paid subscription invite link супергруппы или канала по `chat_id`, `subscription_price` и опциям `name`, `subscription_period`; команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS` без fallback и deny-by-default при пустом списке, бот должен быть администратором целевого чата с правом `can_invite_users`; используется typed aiogram API, если runtime его предоставляет, иначе изолированный raw Bot API helper для совместимости с pinned `aiogram==3.3.0`; `subscription_price` валидируется в диапазоне 1-10000 Telegram Stars, `subscription_period` зафиксирован Telegram на 2592000 секунд, `name` ограничен 0-32 символами, специальных update types не требуется, а ошибки Telegram возвращаются оператору. |
| `editChatSubscriptionInviteLink` | `bot/services/edit_chat_subscription_invite_link.py`, `/editchatsubscriptioninvitelink` в `bot/handlers/commands.py` | Admin-flow изменения subscription invite link, созданной ботом, по `chat_id`, `invite_link` и опциональному `name`; команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS` без fallback и deny-by-default при пустом списке, бот должен быть администратором целевой супергруппы или канала с правом `can_invite_users`; используется typed aiogram API, если runtime его предоставляет, иначе изолированный raw Bot API helper для совместимости с pinned `aiogram==3.3.0`; `name` валидируется по ограничению Telegram 0-32 символа, специальных update types не требуется, а ошибки Telegram возвращаются оператору. |
| `deleteChatPhoto` | `bot/services/delete_chat_photo.py`, `/deletechatphoto` в `bot/handlers/commands.py` | Admin-flow удаления текущей фотографии группы или супергруппы по `chat_id`; команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS` без fallback и deny-by-default при пустом списке, бот должен быть администратором целевого чата с правом изменять информацию чата; используется typed aiogram API `Bot.delete_chat_photo`, специальных update types не требуется, так как сценарий запускается обычной командой из admin-чата, rollback выполняется вручную установкой новой фотографии, а ошибки Telegram по правам, неизвестному чату или отсутствующей removable photo возвращаются оператору. |
| `sendMessage` | `message.answer()` в command/chat/rate-limit handlers | Отправка командных ответов, Claude-ответов, ошибок и rate-limit уведомлений. |
| `editMessageText` | `sent_msg.edit_text()` в streaming handler | Обновление одного сообщения во время streaming и замена его финальным первым chunk'ом. |
| `getFile` | `bot/handlers/chat.py` | Получение `file_path` для входящих `photo`, `voice` и `document`. |
| `answerInlineQuery` | `bot/handlers/inline.py` | Минимальный inline mode: возвращается один статический `InlineQueryResultArticle`. |
| `answerCallbackQuery` | `bot/services/answer_callback_query.py`, `bot/handlers/callbacks.py` | Callback-flow для inline keyboards в `/settings`, `/model`, `/clear`, `/logout` и `/close`; используется typed aiogram API `Bot.answer_callback_query`, `callback_query_id` обязателен, optional text ограничен 200 символами, Telegram-ошибки логируются структурно. |

`message.bot.download_file()` скачивает файл по `file_path`, полученному через
`getFile`; это важная часть file flow, но не отдельный метод Bot API из списка
документации.

### Уже обрабатываемые update-типы и объекты

- `message`: частично обрабатываются text, photo, voice, document, caption и
  reply metadata;
- `inline_query`: обрабатывается минимально, без запроса к Claude proxy;
- `callback_query`: обрабатывается для inline keyboards настроек, выбора модели,
  очистки истории и подтверждений admin-действий.

`TELEGRAM_GUEST_MODE_ENABLED` сохраняет локальную политику для групп: если бот
уже находится в группе и к нему обратились mention/reply, история группы не
прикладывается к запросу в proxy. Официальный Telegram Guest Mode из Bot API
10.0 также поддержан на уровне ответа: когда входящее сообщение содержит
`Message.guest_query_id`, финальный ответ Claude отправляется через raw
`answerGuestQuery`, что позволяет отвечать на guest query без членства бота в
целевом чате.

### Что не интегрировано для максимальных возможностей

Почти все остальные методы Bot API пока не используются. Для максимального
покрытия их лучше добавлять не одним большим слоем, а по функциональным
направлениям:

1. Lifecycle и диагностика: явная настройка `allowed_updates`,
   диагностика конфликтов между webhook и long polling.
2. Профиль и команды бота: `setMyCommands`, `deleteMyCommands`,
   `getMyCommands`, `setMyName`, `getMyName`, `setMyDescription`,
   `getMyDescription`, `setMyShortDescription`, `getMyShortDescription`,
   `setMyProfilePhoto`, `removeMyProfilePhoto` (уже интегрированы),
   `setChatMenuButton`,
   `getChatMenuButton` (уже интегрирован),
   `setMyDefaultAdministratorRights` и `getMyDefaultAdministratorRights`
   (уже интегрированы).
3. Более богатые ответы пользователю: `sendChatAction`,
   `sendChecklist`,
   `sendMessageDraft`, `setMessageReaction` (все четыре уже интегрированы).
4. Управление сообщениями: `editMessageCaption`, `editMessageMedia`,
   `editMessageLiveLocation` и `stopMessageLiveLocation` (уже интегрированы),
   `editMessageChecklist` (уже интегрирован), `editMessageReplyMarkup`, `stopPoll`,
   `approveSuggestedPost` (уже интегрирован), `declineSuggestedPost`,
   `deleteMessage` (уже интегрирован),
   `deleteMessages`, `deleteMessageReaction`, `deleteAllMessageReactions`.
5. Интерактивность: полноценные `answerInlineQuery` ответы через Claude,
   handler для `chosen_inline_result`, `answerCallbackQuery` и inline keyboards
   для настроек/выбора модели, `answerGuestQuery` для официального Guest Mode,
   `answerWebAppQuery`, `savePreparedInlineMessage` и
   `savePreparedKeyboardButton` (уже интегрированы).
6. Группы, модерация и форумы: `getChat`, `getChatAdministrators`,
   `getChatMemberCount`, `getChatMember`, `banChatMember`,
   `unbanChatMember`, `restrictChatMember`, `promoteChatMember`,
   `setChatAdministratorCustomTitle`, `setChatMemberTag`,
   `setChatPermissions`, `exportChatInviteLink`, `createChatInviteLink`,
   `editChatInviteLink`, остальные invite-link методы, join-request методы,
   `pinChatMessage`, `unpinAllChatMessages`, forum-topic методы и
   `leaveChat`.
7. Пользовательский контекст Telegram: `getUserProfilePhotos` (уже интегрирован),
   `setUserEmojiStatus` (уже интегрирован), `getUserProfileAudios`,
   `getUserChatBoosts` (уже интегрирован как deny-by-default admin diagnostic
   `/userchatboosts <chat_id> <user_id>`; бот должен быть администратором в
   целевом чате), `getUserPersonalChatMessages`.
8. Бизнес, managed bots и bot-to-bot: `getBusinessConnection`,
   `readBusinessMessage`, `deleteBusinessMessages`, методы
   `setBusinessAccount*`, `getManagedBotToken`, `replaceManagedBotToken`,
   `getManagedBotAccessSettings`, `setManagedBotAccessSettings`.
9. Gifts, Stars и платежи: `getAvailableGifts` (уже интегрирован как
   deny-by-default admin billing/rewards diagnostic
   `/availablegifts confirm`; метод не принимает параметры, не требует
   специальных update types или chat admin rights и вызывает raw Bot API helper,
   так как pinned `aiogram==3.3.0` не имеет typed wrapper),
   `getChatGifts` (уже интегрирован как read-only admin diagnostic
   `/chatgifts <chat_id|@channelusername> [filters...]`, получает страницу
   `OwnedGifts` channel chat через raw Bot API helper и не требует специальных
   update types),
   `sendGift` (уже интегрирован как deny-by-default admin spending action
   `/sendgift <user|chat> <receiver_id> <gift_id> confirm [text]`; требует
   ровно один receiver, явное подтверждение, каталог gift id из доверенного
   review и raw Bot API helper из-за pinned `aiogram==3.3.0`),
   `giftPremiumSubscription`, `getMyStarBalance`, `getStarTransactions`,
   `refundStarPayment`, `editUserStarSubscription`, `sendInvoice`,
   `createInvoiceLink`, `answerShippingQuery`, `answerPreCheckoutQuery`.
10. Нишевые платформенные возможности: stories (`postStory`, `repostStory`,
    `editStory`, `deleteStory`), stickers/custom emoji, Telegram Passport
    (`setPassportDataErrors`) и Games (`sendGame`, `setGameScore`,
    `getGameHighScores`).

Для этого проекта наиболее полезный следующий слой Telegram API выглядит так:
сначала оставшиеся lifecycle/diagnostics, `sendChatAction`, реальные
inline/callback flows, official Guest Mode и rich outbound media; затем group
administration, payments/Stars/gifts, business/managed-bot возможности и
остальные domain-specific методы.

Для планирования последующих PR этот список уже разложен до отдельных
issue-карточек в
[telegram-bot-api-implementation-guide.md](telegram-bot-api-implementation-guide.md).

## Пользовательские сценарии

### Команды

- `/start` отправляет приветствие и подсказку использовать `/help`;
- `/help` перечисляет доступные команды и поддерживаемые типы сообщений;
- `/model` без аргументов показывает текущую модель пользователя и пытается
  получить список моделей из proxy; если список доступен, ответ содержит
  inline-кнопки выбора модели;
- `/model <model_id>` сохраняет выбранную модель в in-memory настройках
  пользователя;
- `/settings` показывает текущую модель, streaming flag, guest mode и лимит
  запросов и содержит inline-кнопку обновления;
- `/webhook` показывает диагностику Telegram webhook для разрешенных
  admin/ops чатов;
- `/deletewebhook [drop_pending_updates=true|false]` удаляет Telegram webhook
  для разрешенных admin/ops чатов перед переходом на polling или local Bot API;
- `/logout` выполняет защищенный выход бота из cloud Bot API сервера для
  admin-чатов и требует явного подтверждения `/logout confirm` или inline-кнопкой
  из admin-чата;
- `/close` выполняет защищенное закрытие bot instance на текущем Bot API
  сервере для admin-чатов и требует явного подтверждения `/close confirm` или
  inline-кнопкой из admin-чата;
- `/forward <from_chat_id> <message_id> [share]` пересылает одно сообщение из
  другого чата в текущий admin-чат для поддержки/модерации;
- `/forwards <from_chat_id> <message_id> [<message_id> ...] [share]` пакетно
  пересылает 1-100 сообщений из другого чата в текущий admin-чат с сохранением
  album grouping;
- `/copy <from_chat_id> <message_id> [share]` копирует одно сообщение из другого
  чата в текущий admin-чат как новое сообщение без ссылки на исходного
  отправителя;
- `/copies <from_chat_id> <message_id> [<message_id> ...] [share] [nocaption]`
  пакетно копирует 1-100 сообщений из другого чата в текущий admin-чат как новые
  сообщения без ссылки на исходного отправителя, с сохранением album grouping;
- `/photo <url_or_file_id> [caption]` отправляет изображение в текущий чат как
  настоящее Telegram-фото по URL или `file_id`, а не только как текст;
- `/audio <url_or_file_id> [caption]` отправляет аудиофайл в текущий чат как
  проигрываемый музыкальный трек по URL или `file_id`, а не только как текст;
- `/livephoto <live_photo_file_id> <photo_file_id> [caption]` отправляет live
  photo (короткое видео + статичная обложка) в текущий чат по `file_id`, а не
  только как текст;
- `/document <url_or_file_id> [caption]` отправляет файл в текущий чат как
  Telegram-документ по URL или `file_id` — для больших текстовых, PDF или
  исходных артефактов, когда текстовый ответ не подходит;
- `/banchatmember <chat_id> <user_id> [until_date_unix] [revoke=true|false]`
  блокирует пользователя в группе, супергруппе или канале из разрешенного
  admin-чата;
- `/banchatsenderchat <chat_id> <sender_chat_id>` блокирует channel/sender chat
  в супергруппе или канале из разрешенного admin-чата;
- `/unbanchatmember <chat_id> <user_id> [only_if_banned=true|false]`
  разблокирует пользователя в группе, супергруппе или канале из разрешенного
  admin-чата;
- `/restrictchatmember <chat_id> <user_id> <mute|readonly|unrestrict>
  [until_date_unix] [independent=true|false]` ограничивает или восстанавливает
  права пользователя в группе или супергруппе из разрешенного admin-чата;
- `/setchatpermissions <chat_id> <closed|text|media|open>
  [independent=true|false]` меняет default permissions всех
  не-администраторов в группе или супергруппе из разрешенного admin-чата;
- `/promotechatmember <chat_id> <user_id> <moderator|manager|demote>` повышает
  или понижает пользователя в группе, супергруппе или канале из разрешенного
  admin-чата;
- `/exportchatinvitelink <chat_id>` ротирует и возвращает primary invite link
  группы, супергруппы или канала из разрешенного admin-чата;
- `/leavechat <chat_id> confirm` выводит бота из группы, супергруппы или
  канала из разрешенного admin-чата и требует явного подтверждения;
- `/createchatinvitelink <chat_id> [name=<text>] [expire_date=<unix_time>]
  [member_limit=<1-99999>] [creates_join_request=true|false]` создает
  дополнительную invite link группы, супергруппы или канала из разрешенного
  admin-чата;
- `/editchatinvitelink <chat_id> <invite_link> [name=<text>]
  [expire_date=<unix_time>] [member_limit=<1-99999>]
  [creates_join_request=true|false]` меняет существующую non-primary invite
  link группы, супергруппы или канала из разрешенного admin-чата;
- `/revokechatinvitelink <chat_id> <invite_link>` отзывает invite link,
  созданную ботом, для группы, супергруппы или канала из разрешенного
  admin-чата;
- `/createchatsubscriptioninvitelink <chat_id> <subscription_price>
  [name=<text>] [subscription_period=2592000]` создает paid subscription
  invite link супергруппы или канала из разрешенного admin-чата;
- `/editchatsubscriptioninvitelink <chat_id> <invite_link> [name=<text>]`
  меняет существующую subscription invite link, созданную ботом, из
  разрешенного admin-чата;
- `/clear` очищает историю разговора для пары `(chat_id, user_id)` и показывает
  inline-кнопку повторной очистки текущего chat/user контекста.

Inline callback-сценарии требуют update type `callback_query`; специальных прав
бота не нужно, кроме уже существующего доступа к чату с сообщением-клавиатурой.
Admin callback-действия используют тот же deny-by-default allowlist
`TELEGRAM_ADMIN_CHAT_IDS`, что и текстовые `/logout` и `/close`. Rollback для
`/clear` невозможен без внешнего persistent storage, для выбора модели это
повторный выбор прежнего model id, а для `/logout` и `/close` rollback остается
операционным запуском бота после ограничений Telegram.

Важная деталь: выбранная через `/model <model_id>` модель сохраняется в
`storage.user_settings`, но обработчик чата сейчас отправляет запросы с
`settings.free_claude_default_model`. То есть команда сохраняет настройку, но
не влияет на реальные ответы чата.

### Webhook diagnostics

Команда `/webhook` вызывает typed aiogram API `Bot.get_webhook_info()` без
параметров. По официальной документации Telegram метод требует только валидный
bot token и возвращает `WebhookInfo`; если бот использует `getUpdates`, поле
`url` пустое.

Ответ команды включает webhook status, URL, `pending_update_count`,
`allowed_updates`, флаг custom certificate, `max_connections`, последнюю ошибку
доставки update и последнюю ошибку синхронизации с Telegram datacenters, если
они есть. Команда не меняет состояние webhook и не взаимодействует с
`free-claude-code`, поэтому rollback сводится к удалению allowlist для
диагностики или отключению использования команды.

Из-за operational metadata команда закрыта allowlist'ом:

- если задан `TELEGRAM_ADMIN_CHAT_IDS`, `/webhook` доступен только этим chat id;
- если `TELEGRAM_ADMIN_CHAT_IDS` пустой, используется fallback на
  `TELEGRAM_ALLOWED_CHAT_IDS`;
- если оба списка пустые, команда отключена и отвечает restricted message.

Глобальный `RateLimitMiddleware` применяется к `/webhook` так же, как к другим
Telegram-командам.

### Webhook lifecycle: deleteWebhook

Команда `/deletewebhook` вызывает typed aiogram API `Bot.delete_webhook()` и
передает единственный параметр Telegram Bot API `drop_pending_updates`.
Параметр опционален; без аргументов команда использует безопасное значение
`false`, то есть Telegram сохраняет pending updates. Чтобы явно удалить
накопившиеся updates, администратор должен вызвать:

```text
/deletewebhook drop_pending_updates=true
```

По официальной документации Telegram `deleteWebhook` возвращает `True` при
успехе и предназначен для удаления webhook integration перед возвратом к
`getUpdates`. Метод требует только валидный bot token; отдельные chat admin
права, новые update types или доступ к `free-claude-code` не нужны. В
закрепленном `aiogram==3.3.0` есть typed wrapper
`Bot.delete_webhook(drop_pending_updates: Optional[bool])`, поэтому raw Bot API
helper не используется.

Из-за destructive operational impact команда закрыта тем же allowlist'ом, что
и `/webhook`:

- если задан `TELEGRAM_ADMIN_CHAT_IDS`, `/deletewebhook` доступен только этим
  chat id;
- если `TELEGRAM_ADMIN_CHAT_IDS` пустой, используется fallback на
  `TELEGRAM_ALLOWED_CHAT_IDS`;
- если оба списка пустые, команда отключена и отвечает restricted message.

Privacy impact связан с `drop_pending_updates=true`: Telegram удаляет
накопленные входящие updates, и их нельзя восстановить. Security impact
связан с управлением каналом доставки: после удаления webhook бот должен быть
переведен на polling/local Bot API или webhook нужно зарегистрировать заново.
Rollback: снова задать `TELEGRAM_WEBHOOK_URL` и перезапустить приложение либо
вызвать `setWebhook`; rollback не восстанавливает updates, удаленные через
`drop_pending_updates=true`.

### logOut

Команда `/logout` вызывает typed aiogram API `Bot.log_out()` без параметров.
По официальной документации Telegram метод `logOut` требует только валидный
bot token, не принимает параметров и возвращает `True` при успехе. Метод нужен,
чтобы выйти из cloud Bot API сервера перед запуском бота против local Bot API
server.

`logOut` — деструктивная lifecycle-операция, поэтому она защищена строже, чем
диагностика `/webhook`:

- команда доступна только chat id из `TELEGRAM_ADMIN_CHAT_IDS` и не делает
  fallback на `TELEGRAM_ALLOWED_CHAT_IDS`; если `TELEGRAM_ADMIN_CHAT_IDS`
  пустой, команда отключена;
- требуется явное подтверждение: `/logout` без аргумента только показывает
  предупреждение о последствиях, а сам выход выполняется только после
  `/logout confirm`.

После успешного вызова бот перестает получать updates от cloud Bot API сервера
и не может залогиниться обратно в cloud в течение 10 минут. Recovery сводится к
ожиданию 10-минутного окна (или завершению миграции на local Bot API server) и
повторному запуску бота, который снова логинится. Команда не взаимодействует с
`free-claude-code`. Глобальный `RateLimitMiddleware` применяется к `/logout`
так же, как к другим командам.

### close

Команда `/close` вызывает typed aiogram API `Bot.close()` без параметров.
По официальной документации Telegram метод `close` требует только валидный bot
token, не принимает параметров и возвращает `True` при успехе. Метод закрывает
запущенный bot instance и нужен, чтобы безопасно перенести бота с одного local
Bot API server на другой.

`close` — деструктивная lifecycle-операция, поэтому она защищена так же строго,
как `/logout`:

- команда доступна только chat id из `TELEGRAM_ADMIN_CHAT_IDS` и не делает
  fallback на `TELEGRAM_ALLOWED_CHAT_IDS`; если `TELEGRAM_ADMIN_CHAT_IDS`
  пустой, команда отключена;
- требуется явное подтверждение: `/close` без аргумента только показывает
  предупреждение о последствиях, а само закрытие выполняется только после
  `/close confirm`.

Перед вызовом `close` нужно удалить webhook, чтобы бот не запустился снова после
рестарта сервера. Telegram возвращает ошибку 429, если `close` вызвать в первые
10 минут после запуска бота; в этом случае `/close` сообщает об ошибке Telegram
и не закрывает instance. Recovery сводится к переносу бота на новый Bot API
server и повторному запуску, после которого бот снова обрабатывает updates.
Команда не взаимодействует с `free-claude-code`. Глобальный
`RateLimitMiddleware` применяется к `/close` так же, как к другим командам.

### forwardMessage

Команда `/forward` вызывает typed aiogram API `Bot.forward_message()` для
метода Telegram `forwardMessage`. По официальной документации метод требует
`chat_id`, `from_chat_id` и `message_id` и возвращает отправленное `Message`.
Service-сообщения и сообщения с уже protected content переслать нельзя, а бот
должен иметь доступ к `from_chat_id`, то есть быть участником исходного чата.

Выбран admin-сценарий поддержки/модерации: оператор переносит конкретное
сообщение из чата, где находится бот, в текущий admin-чат для разбора. Целевой
чат всегда тот, где вызвана команда, поэтому бот не может переслать сообщение в
произвольный чат. Синтаксис: `/forward <from_chat_id> <message_id> [share]`.

По умолчанию пересланная копия защищается `protect_content=True`, чтобы
модерируемый контент нельзя было переслать или сохранить дальше; необязательное
ключевое слово `share` отключает защиту. Метод обрабатывает одиночное
сообщение; группировка альбома — задача `forwardMessages`.

`/forward` относится к message-relay и закрыт строгим admin allowlist:

- команда доступна только chat id из `TELEGRAM_ADMIN_CHAT_IDS` и не делает
  fallback на `TELEGRAM_ALLOWED_CHAT_IDS`; если `TELEGRAM_ADMIN_CHAT_IDS`
  пустой, команда отключена;
- при отсутствующих или нечисловых аргументах команда показывает usage и не
  обращается к Telegram;
- ошибки Telegram (например, недоступный чат или несуществующее сообщение)
  возвращаются пользователю, а пересылка не выполняется.

Команда не взаимодействует с `free-claude-code`. Глобальный
`RateLimitMiddleware` применяется к `/forward` так же, как к другим командам.

### forwardMessages

Команда `/forwards` вызывает typed aiogram API `Bot.forward_messages()` для
метода Telegram `forwardMessages`. По официальной документации метод требует
`chat_id`, `from_chat_id` и `message_ids` (1-100 идентификаторов в строго
возрастающем порядке) и возвращает массив `MessageId` отправленных сообщений.
В отличие от `forwardMessage`, `forwardMessages` сохраняет album grouping:
сообщения, изначально входившие в один альбом, пересылаются альбомом. Сообщения,
которые переслать нельзя (service-сообщения и сообщения с protected content),
пропускаются, поэтому возвращённый список может быть короче запрошенного; если
переслать нельзя ни одно, вызов завершается ошибкой. Бот должен иметь доступ к
`from_chat_id`, то есть быть участником исходного чата.

Выбран тот же admin-сценарий поддержки/модерации, что и для `/forward`, но для
переноса сразу нескольких сообщений (например, целого альбома) одним вызовом.
Целевой чат всегда тот, где вызвана команда. Синтаксис:
`/forwards <from_chat_id> <message_id> [<message_id> ...] [share]`.

По умолчанию пересланные копии защищаются `protect_content=True`; необязательное
ключевое слово `share` отключает защиту. Команда сообщает, сколько из
запрошенных сообщений было фактически переслано, так как часть могла быть
пропущена Telegram.

`/forwards` относится к message-relay и закрыт строгим admin allowlist:

- команда доступна только chat id из `TELEGRAM_ADMIN_CHAT_IDS` и не делает
  fallback на `TELEGRAM_ALLOWED_CHAT_IDS`; если `TELEGRAM_ADMIN_CHAT_IDS`
  пустой, команда отключена;
- при отсутствующих, нечисловых, нарушающих строгий порядок или выходящих за
  пределы 1-100 идентификаторах команда показывает usage и не обращается к
  Telegram;
- ошибки Telegram (например, недоступный чат) возвращаются пользователю, а
  пересылка не выполняется.

Команда не взаимодействует с `free-claude-code`. Глобальный
`RateLimitMiddleware` применяется к `/forwards` так же, как к другим командам.

### copyMessage

Команда `/copy` вызывает typed aiogram API `Bot.copy_message()` для метода
Telegram `copyMessage`. По официальной документации метод требует `chat_id`,
`from_chat_id` и `message_id` и возвращает только новый `MessageId`, а не полное
`Message`. В отличие от `forwardMessage`, `copyMessage` пересоздаёт содержимое
как новое сообщение **без ссылки на оригинал** (нет заголовка «forwarded from»),
поэтому оператор может разобрать или переразместить модерируемый контент, не
раскрывая источник. Service-сообщения, paid media, giveaway/giveaway-winners и
invoice-сообщения скопировать нельзя, а бот должен иметь доступ к `from_chat_id`,
то есть быть участником исходного чата.

Выбран тот же admin-сценарий поддержки/модерации, что и для `/forward`: оператор
переносит конкретное сообщение из чата, где находится бот, в текущий admin-чат
для разбора. Целевой чат всегда тот, где вызвана команда, поэтому бот не может
скопировать сообщение в произвольный чат. Синтаксис:
`/copy <from_chat_id> <message_id> [share]`.

По умолчанию скопированное сообщение защищается `protect_content=True`, чтобы
модерируемый контент нельзя было переслать или сохранить дальше; необязательное
ключевое слово `share` отключает защиту. Метод обрабатывает одиночное
сообщение; пакетное копирование с сохранением группировки альбома — задача
`copyMessages`, доступного как `/copies`.

`/copy` относится к message-relay и закрыт строгим admin allowlist:

- команда доступна только chat id из `TELEGRAM_ADMIN_CHAT_IDS` и не делает
  fallback на `TELEGRAM_ALLOWED_CHAT_IDS`; если `TELEGRAM_ADMIN_CHAT_IDS`
  пустой, команда отключена;
- при отсутствующих или нечисловых аргументах команда показывает usage и не
  обращается к Telegram;
- ошибки Telegram (например, недоступный чат или несуществующее сообщение)
  возвращаются пользователю, а копирование не выполняется.

Команда не взаимодействует с `free-claude-code`. Глобальный
`RateLimitMiddleware` применяется к `/copy` так же, как к другим командам.

### copyMessages

Команда `/copies` вызывает typed aiogram API `Bot.copy_messages()` для метода
Telegram `copyMessages`. По официальной документации метод требует `chat_id`,
`from_chat_id` и `message_ids` (1-100 идентификаторов в строго возрастающем
порядке) и возвращает массив `MessageId` отправленных сообщений. Как и
`copyMessage` и в отличие от `forwardMessages`, скопированные сообщения **не
имеют ссылки на оригинал** (нет заголовка «forwarded from»), поэтому оператор
может переразместить модерируемый контент, не раскрывая источник. Как и
`forwardMessages`, метод сохраняет album grouping: сообщения, изначально
входившие в один альбом, пересоздаются альбомом. Сообщения, которые скопировать
нельзя (service, giveaway/giveaway-winners и invoice-сообщения), пропускаются,
поэтому возвращённый список может быть короче запрошенного; бот должен иметь
доступ к `from_chat_id`, то есть быть участником исходного чата.

Выбран тот же admin-сценарий поддержки/модерации, что и для `/copy`, но для
переноса сразу нескольких сообщений (например, целого альбома) одним вызовом.
Целевой чат всегда тот, где вызвана команда. Синтаксис:
`/copies <from_chat_id> <message_id> [<message_id> ...] [share] [nocaption]`.

По умолчанию скопированные сообщения защищаются `protect_content=True`;
необязательное ключевое слово `share` отключает защиту. В отличие от
`copyMessage`, у `copyMessages` нет переопределения `caption`, поэтому
необязательное ключевое слово `nocaption` включает `remove_caption=True` и
копирует сообщения без их исходных подписей; оба ключевых слова можно
комбинировать в конце в любом порядке. Команда сообщает, сколько из запрошенных
сообщений было фактически скопировано, так как часть могла быть пропущена
Telegram.

`/copies` относится к message-relay и закрыт строгим admin allowlist:

- команда доступна только chat id из `TELEGRAM_ADMIN_CHAT_IDS` и не делает
  fallback на `TELEGRAM_ALLOWED_CHAT_IDS`; если `TELEGRAM_ADMIN_CHAT_IDS`
  пустой, команда отключена;
- при отсутствующих, нечисловых, нарушающих строгий порядок или выходящих за
  пределы 1-100 идентификаторах команда показывает usage и не обращается к
  Telegram;
- ошибки Telegram (например, недоступный чат) возвращаются пользователю, а
  копирование не выполняется.

Команда не взаимодействует с `free-claude-code`. Глобальный
`RateLimitMiddleware` применяется к `/copies` так же, как к другим командам.

### sendPhoto

Команда `/photo` вызывает typed aiogram API `Bot.send_photo()` для метода
Telegram `sendPhoto`. По официальной документации метод требует `chat_id` и
`photo` и возвращает отправленное `Message`. `photo` может быть HTTP(S)-URL,
который Telegram скачивает сам, `file_id` уже существующего на серверах Telegram
фото или загружаемым файлом; helper принимает строковую форму URL/`file_id`.
Telegram ограничивает фото 10 MB, сумму ширины и высоты — 10000, соотношение
сторон — не более 20, а `caption` — 1024 символами после парсинга entities.

Выбран admin-сценарий исходящего медиа: оператор отправляет сгенерированное или
полученное изображение в чат как настоящее фото, а не только текстовую
интерпретацию. Целевой чат всегда тот, где вызвана команда. Синтаксис:
`/photo <url_or_file_id> [caption]`.

Caption необязателен, может содержать пробелы и проверяется на лимит 1024
символа до обращения к Telegram, чтобы validation path не зависел от ошибки
Telegram. Метод обрабатывает одиночное фото; отправка альбома — задача
`sendMediaGroup`.

`/photo` относится к исходящему медиа и закрыт строгим admin allowlist:

- команда доступна только chat id из `TELEGRAM_ADMIN_CHAT_IDS` и не делает
  fallback на `TELEGRAM_ALLOWED_CHAT_IDS`; если `TELEGRAM_ADMIN_CHAT_IDS`
  пустой, команда отключена;
- при отсутствующем photo-аргументе команда показывает usage, а при слишком
  длинном caption — сообщение о превышении лимита, и в обоих случаях не
  обращается к Telegram;
- ошибки Telegram (например, недоступный URL или превышение лимитов фото)
  возвращаются пользователю, а отправка не выполняется.

Команда не взаимодействует с `free-claude-code`. Глобальный
`RateLimitMiddleware` применяется к `/photo` так же, как к другим командам.

### sendAudio

Команда `/audio` вызывает typed aiogram API `Bot.send_audio()` для метода
Telegram `sendAudio`. По официальной документации метод требует `chat_id` и
`audio` и возвращает отправленное `Message`. `audio` может быть HTTP(S)-URL,
который Telegram скачивает сам, `file_id` уже существующего на серверах Telegram
аудиофайла или загружаемым файлом; helper принимает строковую форму
URL/`file_id`. Telegram ожидает аудио в формате `.MP3` или `.M4A`, ограничивает
файл, отправляемый по URL или `file_id`, 20 MB, а `caption` — 1024 символами
после парсинга entities. Опциональные `duration` (в секундах), `performer` и
`title` задают музыкальные метаданные трека.

Выбран admin-сценарий исходящего медиа: оператор отправляет сгенерированный или
полученный аудиоклип в чат как настоящий проигрываемый трек, а не только
текстовую интерпретацию. Целевой чат всегда тот, где вызвана команда. Синтаксис:
`/audio <url_or_file_id> [caption]`.

Caption необязателен, может содержать пробелы и проверяется на лимит 1024
символа до обращения к Telegram, чтобы validation path не зависел от ошибки
Telegram. Метод обрабатывает одиночный аудиофайл; голосовое сообщение — задача
`sendVoice`, а отправка альбома — `sendMediaGroup`.

`/audio` относится к исходящему медиа и закрыт строгим admin allowlist:

- команда доступна только chat id из `TELEGRAM_ADMIN_CHAT_IDS` и не делает
  fallback на `TELEGRAM_ALLOWED_CHAT_IDS`; если `TELEGRAM_ADMIN_CHAT_IDS`
  пустой, команда отключена;
- при отсутствующем audio-аргументе команда показывает usage, а при слишком
  длинном caption — сообщение о превышении лимита, и в обоих случаях не
  обращается к Telegram;
- ошибки Telegram (например, недоступный URL или неподдерживаемый формат файла)
  возвращаются пользователю, а отправка не выполняется.

Команда не взаимодействует с `free-claude-code`. Глобальный
`RateLimitMiddleware` применяется к `/audio` так же, как к другим командам.

### sendLivePhoto

Команда `/livephoto` отправляет live photo — короткое зацикленное видео в паре
со статичной обложкой — методом Telegram `sendLivePhoto` (Bot API 10.0). По
официальной документации метод требует `chat_id`, `live_photo` (видео) и `photo`
(статичная обложка) и возвращает отправленное `Message`. Видео `live_photo` не
должно быть длиннее 10 секунд и больше 10 MB. Telegram **не поддерживает**
отправку live photo по URL, поэтому `live_photo` и `photo` должны быть `file_id`
уже существующих на серверах Telegram медиа; helper принимает строковую форму
`file_id`. `caption` ограничен 1024 символами после парсинга entities.

Ключевое отличие от `sendPhoto`/`sendAudio`: pinned `aiogram==3.3.0`
(Bot API 7.0) не имеет typed wrapper для этого метода Bot API 10.0. Поэтому
реализация идет через изолированный raw Bot API helper
`bot/services/send_live_photo.py`, который сам собирает JSON-payload и POST'ит
его на endpoint `sendLivePhoto` через `httpx`, не завися от typed aiogram метода.
URL endpoint берется из `bot.session.api.api_url(...)`, чтобы учесть кастомный
local Bot API server, с fallback на cloud-endpoint. Ошибки транспорта и ответы
Telegram с `ok: false` поднимаются как единое исключение `SendLivePhotoError`.

Выбран admin-сценарий исходящего медиа: оператор отправляет live photo в чат, а
не только текстовую интерпретацию. Целевой чат всегда тот, где вызвана команда.
Синтаксис: `/livephoto <live_photo_file_id> <photo_file_id> [caption]`.

Caption необязателен, может содержать пробелы и проверяется на лимит 1024 символа
до обращения к Telegram, чтобы validation path не зависел от ошибки Telegram.

`/livephoto` относится к исходящему медиа и закрыт строгим admin allowlist:

- команда доступна только chat id из `TELEGRAM_ADMIN_CHAT_IDS` и не делает
  fallback на `TELEGRAM_ALLOWED_CHAT_IDS`; если `TELEGRAM_ADMIN_CHAT_IDS`
  пустой, команда отключена;
- при отсутствии любого из двух `file_id`-аргументов команда показывает usage, а
  при слишком длинном caption — сообщение о превышении лимита, и в обоих случаях
  не обращается к Telegram;
- ошибки Telegram (например, неверный `file_id` или неподдерживаемый формат
  файла) возвращаются пользователю, а отправка не выполняется.

Команда не взаимодействует с `free-claude-code`. Глобальный
`RateLimitMiddleware` применяется к `/livephoto` так же, как к другим командам.

### sendDocument

Команда `/document` вызывает typed aiogram API `Bot.send_document()` для метода
Telegram `sendDocument`. По официальной документации метод требует `chat_id` и
`document` и возвращает отправленное `Message`. `document` может быть HTTP(S)-URL,
который Telegram скачивает сам, `file_id` уже существующего на серверах Telegram
файла или загружаемым файлом; helper принимает строковую форму URL/`file_id`.
Telegram ограничивает файл, отправляемый по URL, 20 MB, а `caption` — 1024
символами после парсинга entities. Опциональные `disable_content_type_detection`
отключает серверное автоопределение типа контента, а `thumbnail` задает кастомную
обложку-превью.

Выбран admin-сценарий исходящего медиа: оператор возвращает большой текстовый,
PDF или исходный артефакт как настоящий документ, когда текстовый ответ не
подходит, а не только текстовую интерпретацию. Целевой чат всегда тот, где
вызвана команда. Синтаксис: `/document <url_or_file_id> [caption]`.

Caption необязателен, может содержать пробелы и проверяется на лимит 1024
символа до обращения к Telegram, чтобы validation path не зависел от ошибки
Telegram. Метод обрабатывает одиночный файл общего назначения; голосовое
сообщение — задача `sendVoice`, аудиотрек — `sendAudio`, а отправка альбома —
`sendMediaGroup`.

`/document` относится к исходящему медиа и закрыт строгим admin allowlist:

- команда доступна только chat id из `TELEGRAM_ADMIN_CHAT_IDS` и не делает
  fallback на `TELEGRAM_ALLOWED_CHAT_IDS`; если `TELEGRAM_ADMIN_CHAT_IDS`
  пустой, команда отключена;
- при отсутствующем document-аргументе команда показывает usage, а при слишком
  длинном caption — сообщение о превышении лимита, и в обоих случаях не
  обращается к Telegram;
- ошибки Telegram (например, недоступный URL или неверный `file_id`)
  возвращаются пользователю, а отправка не выполняется.

Команда не взаимодействует с `free-claude-code`. Глобальный
`RateLimitMiddleware` применяется к `/document` так же, как к другим командам.

### sendVideo

Команда `/video` вызывает typed aiogram API `Bot.send_video()` для метода
Telegram `sendVideo`. По официальной документации метод требует `chat_id` и
`video` и возвращает отправленное `Message`. `video` может быть HTTP(S)-URL,
который Telegram скачивает сам, `file_id` уже существующего на серверах Telegram
видео или загружаемым файлом; helper принимает строковую форму URL/`file_id`.
Telegram-клиенты поддерживают видео в формате MPEG4 (другие форматы могут быть
отправлены как `Document`), ограничивают файл, отправляемый по URL, 20 MB, а
`caption` — 1024 символами после парсинга entities. Опциональные `duration` (в
секундах), `width` и `height` описывают видео, `thumbnail` задает кастомную
обложку-превью, `has_spoiler` закрывает видео spoiler-анимацией, а
`supports_streaming` помечает файл как пригодный для стриминга.

Выбран admin-сценарий исходящего медиа: оператор отправляет сгенерированный или
полученный клип в чат как настоящее проигрываемое видео, а не только текстовую
интерпретацию. Целевой чат всегда тот, где вызвана команда. Синтаксис:
`/video <url_or_file_id> [caption]`.

Caption необязателен, может содержать пробелы и проверяется на лимит 1024
символа до обращения к Telegram, чтобы validation path не зависел от ошибки
Telegram. Метод обрабатывает одиночное видео; видеосообщение-кружок — задача
`sendVideoNote`, GIF/анимация без звука — `sendAnimation`, а отправка альбома —
`sendMediaGroup`.

`/video` относится к исходящему медиа и закрыт строгим admin allowlist:

- команда доступна только chat id из `TELEGRAM_ADMIN_CHAT_IDS` и не делает
  fallback на `TELEGRAM_ALLOWED_CHAT_IDS`; если `TELEGRAM_ADMIN_CHAT_IDS`
  пустой, команда отключена;
- при отсутствующем video-аргументе команда показывает usage, а при слишком
  длинном caption — сообщение о превышении лимита, и в обоих случаях не
  обращается к Telegram;
- ошибки Telegram (например, недоступный URL или неподдерживаемый формат файла)
  возвращаются пользователю, а отправка не выполняется.

Команда не взаимодействует с `free-claude-code`. Глобальный
`RateLimitMiddleware` применяется к `/video` так же, как к другим командам.

### sendVideoNote

Команда `/videonote` вызывает typed aiogram API `Bot.send_video_note()` для
метода Telegram `sendVideoNote`. По официальной документации метод требует
`chat_id` и `video_note` и возвращает отправленное `Message`. В отличие от
`sendVideo`, Telegram сейчас **не** поддерживает отправку видеосообщений-кружков
по URL, поэтому `video_note` должен быть `file_id` уже существующего на серверах
Telegram видеосообщения или загружаемым файлом; helper принимает строковую форму
`file_id`. У видеосообщений-кружков нет caption и они не принимают `parse_mode`.
Опциональные `duration` (в секундах) и `length` (диаметр квадратного
видеосообщения) описывают клип, а `thumbnail` задает кастомную обложку-превью.
Параметры соответствуют typed wrapper'у pinned `aiogram==3.3.0` (Bot API 7.0).

Выбран admin-сценарий исходящего медиа: оператор отправляет сгенерированный или
полученный клип в чат как настоящее проигрываемое видеосообщение-кружок, а не
только текстовую интерпретацию. Целевой чат всегда тот, где вызвана команда.
Синтаксис: `/videonote <file_id>`.

Caption у видеосообщений нет, поэтому команда не принимает текст подписи: лишние
токены после `file_id` игнорируются. Метод отправляет круглое квадратное
видеосообщение; обычное видео со звуком — задача `sendVideo`, GIF/анимация без
звука — `sendAnimation`, а отправка альбома — `sendMediaGroup`.

`/videonote` относится к исходящему медиа и закрыт строгим admin allowlist:

- команда доступна только chat id из `TELEGRAM_ADMIN_CHAT_IDS` и не делает
  fallback на `TELEGRAM_ALLOWED_CHAT_IDS`; если `TELEGRAM_ADMIN_CHAT_IDS`
  пустой, команда отключена;
- при отсутствующем video_note-аргументе команда показывает usage и не
  обращается к Telegram;
- ошибки Telegram (например, неверный `file_id` или попытка отправить по URL)
  возвращаются пользователю, а отправка не выполняется.

Команда не взаимодействует с `free-claude-code`. Глобальный
`RateLimitMiddleware` применяется к `/videonote` так же, как к другим командам.

### sendAnimation

Команда `/animation` вызывает typed aiogram API `Bot.send_animation()` для
метода Telegram `sendAnimation`. По официальной документации метод требует
`chat_id` и `animation` и возвращает отправленное `Message`. `animation` может
быть HTTP(S)-URL, который Telegram скачивает сам, `file_id` уже существующей на
серверах Telegram анимации или загружаемым файлом; helper принимает строковую
форму URL/`file_id`. Telegram доставляет GIF и H.264/MPEG-4 AVC файлы без звука,
ограничивает файл, отправляемый по URL, 20 MB, а `caption` — 1024 символами
после парсинга entities. Опциональные `duration` (в секундах), `width` и
`height` описывают анимацию, `thumbnail` задает кастомную обложку-превью, а
`has_spoiler` закрывает анимацию spoiler-анимацией.

Выбран admin-сценарий исходящего медиа: оператор отправляет сгенерированный или
полученный GIF/клип в чат как настоящую проигрываемую зацикленную анимацию, а не
только текстовую интерпретацию. Целевой чат всегда тот, где вызвана команда.
Синтаксис: `/animation <url_or_file_id> [caption]`.

Caption необязателен, может содержать пробелы и проверяется на лимит 1024
символа до обращения к Telegram, чтобы validation path не зависел от ошибки
Telegram. Метод обрабатывает анимацию без звука; видео со звуком — задача
`sendVideo`, видеосообщение-кружок — `sendVideoNote`, а отправка альбома —
`sendMediaGroup`.

`/animation` относится к исходящему медиа и закрыт строгим admin allowlist:

- команда доступна только chat id из `TELEGRAM_ADMIN_CHAT_IDS` и не делает
  fallback на `TELEGRAM_ALLOWED_CHAT_IDS`; если `TELEGRAM_ADMIN_CHAT_IDS`
  пустой, команда отключена;
- при отсутствующем animation-аргументе команда показывает usage, а при слишком
  длинном caption — сообщение о превышении лимита, и в обоих случаях не
  обращается к Telegram;
- ошибки Telegram (например, недоступный URL или неподдерживаемый формат файла)
  возвращаются пользователю, а отправка не выполняется.

Команда не взаимодействует с `free-claude-code`. Глобальный
`RateLimitMiddleware` применяется к `/animation` так же, как к другим командам.

### sendSticker

Команда `/sticker` вызывает typed aiogram API `Bot.send_sticker()` для метода
Telegram `sendSticker`. В pinned `aiogram==3.3.0` wrapper уже есть и принимает
`chat_id`, `sticker`, optional `message_thread_id`, `emoji`,
`disable_notification` и `protect_content`. По официальной документации метод
отправляет static `.WEBP`, animated `.TGS` или video `.WEBM` sticker и
возвращает отправленное `Message`. `sticker` может быть `file_id`, HTTP(S)-URL
для static `.WEBP` или загружаемым файлом; video stickers отправляются только
по `file_id`, animated stickers нельзя отправить по HTTP URL. Static и animated
stickers ограничены 512 KB, video stickers — 256 KB, размер должен вписываться
в 512x512. Optional `emoji` используется Telegram как emoji hint для только что
загруженных stickers.

Выбран отдельный admin-сценарий creative/media module: оператор отправляет
готовый sticker/custom emoji в текущий чат по URL или `file_id`. Это не часть
основного Claude chat flow, не вызывает `free-claude-code`, не требует приема
специальных update types и не требует chat administrator rights для обычной
отправки в чат, где бот может писать сообщения. Для групп/каналов действуют
обычные права бота на отправку сообщений/stickers; ошибки Telegram возвращаются
оператору без retry.

Синтаксис: `/sticker <url_or_file_id> [emoji]`.

`/sticker` закрыт строгим admin allowlist:

- команда доступна только chat id из `TELEGRAM_ADMIN_CHAT_IDS` и не делает
  fallback на `TELEGRAM_ALLOWED_CHAT_IDS`; если `TELEGRAM_ADMIN_CHAT_IDS`
  пустой, команда отключена;
- при отсутствующем sticker-аргументе команда показывает usage и не обращается
  к Telegram;
- ошибки Telegram (например, недоступный URL, неподдерживаемый формат или
  запрет отправки stickers в чате) возвращаются пользователю, а отправка не
  выполняется.

Rollback не требует миграций: удалить команду из меню/документации или убрать
чат из `TELEGRAM_ADMIN_CHAT_IDS`; уже отправленные stickers удаляются обычным
`deleteMessage` при наличии прав. Structured logs пишут только chat id, наличие
emoji hint, protect flag и id отправленного сообщения, без sticker file_id/URL.
Глобальный `RateLimitMiddleware` применяется к `/sticker` так же, как к другим
командам.

### sendVoice

Команда `/voice` вызывает typed aiogram API `Bot.send_voice()` для метода
Telegram `sendVoice`. По официальной документации метод требует `chat_id` и
`voice` и возвращает отправленное `Message`. `voice` может быть HTTP(S)-URL,
который Telegram скачивает сам, `file_id` уже существующего на серверах Telegram
голосового сообщения или загружаемым файлом; helper принимает строковую форму
URL/`file_id`. Чтобы аудио воспроизводилось именно как голосовое сообщение,
Telegram ожидает `.OGG` файл в кодировке OPUS, либо `.MP3` или `.M4A`; другие
форматы могут быть отправлены как audio или document. Telegram ограничивает файл,
отправляемый по URL или `file_id`, 20 MB, а `caption` — 1024 символами после
парсинга entities. Опциональный `duration` задает длительность голосового
сообщения в секундах.

Выбран admin-сценарий исходящего медиа: оператор отправляет сгенерированный или
полученный аудиоклип в чат как настоящее проигрываемое голосовое сообщение
(в виде waveform), а не только текстовую интерпретацию. Целевой чат всегда тот,
где вызвана команда. Синтаксис: `/voice <url_or_file_id> [caption]`.

Caption необязателен, может содержать пробелы и проверяется на лимит 1024
символа до обращения к Telegram, чтобы validation path не зависел от ошибки
Telegram. Метод отправляет голосовое сообщение; музыкальный трек с метаданными —
задача `sendAudio`, видеосообщение-кружок — `sendVideoNote`, а отправка альбома —
`sendMediaGroup`.

`/voice` относится к исходящему медиа и закрыт строгим admin allowlist:

- команда доступна только chat id из `TELEGRAM_ADMIN_CHAT_IDS` и не делает
  fallback на `TELEGRAM_ALLOWED_CHAT_IDS`; если `TELEGRAM_ADMIN_CHAT_IDS`
  пустой, команда отключена;
- при отсутствующем voice-аргументе команда показывает usage, а при слишком
  длинном caption — сообщение о превышении лимита, и в обоих случаях не
  обращается к Telegram;
- ошибки Telegram (например, недоступный URL или неподдерживаемый формат файла)
  возвращаются пользователю, а отправка не выполняется.

Команда не взаимодействует с `free-claude-code`. Глобальный
`RateLimitMiddleware` применяется к `/voice` так же, как к другим командам.

### sendPaidMedia

Команда `/paidmedia` отправляет платное медиа — контент, доступ к которому
пользователи оплачивают Telegram Stars, — методом Telegram `sendPaidMedia`
(введен в Bot API 7.6). По официальной документации метод требует `chat_id`,
`star_count` (цена в Telegram Stars; 1-25000 по состоянию на Bot API 10.0) и
`media` (JSON-массив до 10 элементов `InputPaidMedia`, каждый — `photo` или
`video`) и возвращает отправленное `Message`. Если `chat_id` указывает на канал,
все Star-поступления зачисляются на баланс канала; иначе — на баланс бота.
Опциональный `payload` (0-128 байт) не показывается пользователю и возвращается
в `purchased_paid_media` updates, а `caption` ограничен 1024 символами после
парсинга entities.

Ключевое отличие от `sendPhoto`/`sendVideo`: pinned `aiogram==3.3.0`
(Bot API 7.0) не имеет typed wrapper для этого метода Bot API 7.6. Поэтому
реализация идет через изолированный raw Bot API helper
`bot/services/send_paid_media.py`, который сам собирает JSON-payload (с
JSON-сериализацией массива `media`) и POST'ит его на endpoint `sendPaidMedia`
через `httpx`, не завися от typed aiogram метода. URL endpoint берется из
`bot.session.api.api_url(...)`, чтобы учесть кастомный local Bot API server, с
fallback на cloud-endpoint. Ошибки транспорта и ответы Telegram с `ok: false`
поднимаются как единое исключение `SendPaidMediaError`.

Выбран admin-сценарий исходящего медиа: оператор отправляет платное фото в чат,
а не только текстовую интерпретацию. Целевой чат всегда тот, где вызвана команда.
Синтаксис: `/paidmedia <star_count> <url_or_file_id> [caption]`. Команда
отправляет одиночное фото (`media=[{"type": "photo", ...}]`), а helper принимает
полный массив `media` для до 10 photo/video элементов.

`star_count` проверяется на диапазон 1-25000, а caption необязателен, может
содержать пробелы и проверяется на лимит 1024 символа до обращения к Telegram,
чтобы validation path не зависел от ошибки Telegram.

`/paidmedia` относится к исходящему медиа и закрыт строгим admin allowlist:

- команда доступна только chat id из `TELEGRAM_ADMIN_CHAT_IDS` и не делает
  fallback на `TELEGRAM_ALLOWED_CHAT_IDS`; если `TELEGRAM_ADMIN_CHAT_IDS`
  пустой, команда отключена;
- при отсутствии цены или media-аргумента (или нечисловой цене) команда
  показывает usage, при цене вне диапазона 1-25000 — сообщение о допустимом
  диапазоне, а при слишком длинном caption — сообщение о превышении лимита, и во
  всех случаях не обращается к Telegram;
- ошибки Telegram (например, недостаточные права бота на отправку платного медиа
  или неверный `file_id`) возвращаются пользователю, а отправка не выполняется.

Команда не взаимодействует с `free-claude-code`. Глобальный
`RateLimitMiddleware` применяется к `/paidmedia` так же, как к другим командам.

### getAvailableGifts

Команда `/availablegifts` вызывает Telegram `getAvailableGifts` (Bot API 10.0)
для получения текущего каталога обычных подарков. По официальной документации
метод не принимает параметров и возвращает объект `Gifts` со списком `gifts`.
Он не требует прав администратора в чатах и не требует подписки на специальные
update types: сценарий запускается обычным admin message update.

Ключевое отличие от старых методов: pinned `aiogram==3.3.0` не имеет typed
wrapper для `getAvailableGifts`, поэтому реализация идет через изолированный
raw Bot API helper `bot/services/get_available_gifts.py`. Helper POST'ит пустой
JSON-payload на endpoint `getAvailableGifts`, использует URL из
`bot.session.api.api_url(...)` для поддержки local Bot API server и поднимает
transport/Telegram `ok: false` ошибки как `GetAvailableGiftsError`.

Выбран отдельный админский billing/rewards scenario: оператор явно выполняет
`/availablegifts confirm`, чтобы получить каталог перед отдельными будущими
действиями, которые могут тратить Telegram Stars, отправлять подарки или
участвовать в verification/rewards flow. Этот метод сам по себе read-only: он
не тратит Stars, не отправляет gifts, не меняет verification state и не вызывает
`free-claude-code`. Rollback не нужен, достаточно игнорировать результат или
отключить команду.

Product rules и audit log:

- команда доступна только chat id из `TELEGRAM_ADMIN_CHAT_IDS` и не делает
  fallback на `TELEGRAM_ALLOWED_CHAT_IDS`; если список пустой, команда
  отключена;
- команда требует literal `confirm`, чтобы billing/rewards review был явным
  действием оператора, даже несмотря на read-only nature метода;
- structured logs включают только `gifts_count` и gift ids, без user/chat data и
  без содержимого будущих spending actions;
- Telegram permission/transport/rate-limit errors возвращаются в admin chat;
- любые будущие методы `sendGift`, `giftPremiumSubscription` или verification
  actions должны быть отдельными командами с собственным подтверждением,
  allowlist checks, rollback notes и audit log.

### sendGift

Команда `/sendgift` вызывает Telegram `sendGift` (Bot API 10.0) для отправки
обычного подарка пользователю или каналу. По официальной документации метод
требует `gift_id` и ровно один receiver: `user_id` или `chat_id`. Дополнительно
поддерживаются `pay_for_upgrade`, `text`, `text_parse_mode` и `text_entities`.
Метод возвращает boolean `True` и списывает стоимость подарка в Telegram Stars
с баланса бота. Специальные update types не нужны; права и баланс проверяются
Telegram на стороне конкретного receiver.

Так как pinned `aiogram==3.3.0` не имеет typed wrapper для `sendGift`,
реализация использует изолированный raw Bot API helper
`bot/services/send_gift.py`. Helper POST'ит JSON-payload на endpoint `sendGift`,
использует URL из `bot.session.api.api_url(...)` для поддержки local Bot API
server, проверяет ровно один receiver до HTTP-вызова и поднимает
transport/Telegram `ok: false`/unexpected-result ошибки как `SendGiftError`.

Выбран отдельный admin billing/rewards scenario: оператор сначала получает
каталог через `/availablegifts confirm`, выбирает `gift_id` из доверенного
review, проверяет receiver и product rules, затем выполняет
`/sendgift <user|chat> <receiver_id> <gift_id> confirm [text]`. Команда не
связана с `free-claude-code` и не смешивается с verification actions. Rollback
ограничен операционными действиями: сама доставка подарка не отменяется этим
ботом, поэтому ошибочные расходы нужно разбирать по audit log и балансу Stars.

Product rules и audit log:

- команда доступна только chat id из `TELEGRAM_ADMIN_CHAT_IDS` и не делает
  fallback на `TELEGRAM_ALLOWED_CHAT_IDS`; если список пустой, команда
  отключена;
- команда требует literal `confirm` в том же сообщении, которое запускает
  расход Stars;
- parser принимает `user <positive_user_id>` или `chat <chat_id|@username>` и
  отклоняет команды с двумя receiver или без receiver;
- optional gift text ограничен 128 символами до отправки;
- structured logs включают `gift_id`, receiver type, `pay_for_upgrade` и факт
  наличия текста, но не сам текст и не unrelated user/chat data;
- Telegram permission/balance/transport/rate-limit errors возвращаются в admin
  chat.

### giftPremiumSubscription

Команда `/giftpremium` вызывает Telegram `giftPremiumSubscription` (Bot API
10.0) для подарка Telegram Premium пользователю. По официальной документации
метод требует `user_id`, `month_count` и `star_count`: именно это количество
Telegram Stars будет списано с баланса бота. Дополнительно поддерживаются
`text`, `text_parse_mode` и `text_entities`. Метод возвращает boolean `True`.
Специальные update types не нужны, потому что сценарий запускается обычным
admin message update; существование пользователя, права/доступность Premium
gift и баланс Stars проверяет Telegram.

Так как pinned `aiogram==3.3.0` не имеет typed wrapper для
`giftPremiumSubscription`, реализация использует изолированный raw Bot API
helper `bot/services/gift_premium_subscription.py`. Helper POST'ит JSON-payload
на endpoint `giftPremiumSubscription`, использует URL из
`bot.session.api.api_url(...)` для поддержки local Bot API server, валидирует
`user_id`, `month_count` и `star_count` до HTTP-вызова и поднимает
transport/Telegram `ok: false`/unexpected-result ошибки как
`GiftPremiumSubscriptionError`.

Выбран отдельный admin billing/rewards scenario:
`/giftpremium <user_id> <month_count> <star_count> confirm [text]`. Оператор
должен заранее проверить текущую Telegram цену Premium gift, product rules,
получателя, баланс Stars и связь действия с verification/rewards flow. Команда
не вызывает `free-claude-code` и не смешивается с обычными gifts или
verification actions. Rollback ограничен операционными действиями: Premium gift
нельзя отменить этим ботом, поэтому ошибочные расходы нужно разбирать по audit
log и балансу Stars.

Product rules и audit log:

- команда доступна только chat id из `TELEGRAM_ADMIN_CHAT_IDS` и не делает
  fallback на `TELEGRAM_ALLOWED_CHAT_IDS`; если список пустой, команда
  отключена;
- команда требует literal `confirm` в том же сообщении, которое запускает
  расход Stars;
- parser принимает positive `user_id`, `month_count` в диапазоне `3..12` и
  positive `star_count`; optional text ограничен 128 символами до отправки;
- structured logs включают `user_id`, `month_count`, `star_count` и факт
  наличия текста, но не сам текст и не unrelated chat data;
- Telegram permission/balance/transport/rate-limit errors возвращаются в admin
  chat.

### verifyUser

Команда `/verifyuser` вызывает Telegram `verifyUser` (Bot API 10.0) для
верификации пользователя от имени бота, которому Telegram выдал право
верифицировать пользователей. По официальной документации метод требует
`user_id`, опционально принимает `custom_description` и возвращает boolean
`True`. Специальные update types не нужны, потому что сценарий запускается
обычным admin message update; доступность пользователя и право бота на
верификацию проверяет Telegram.

Так как pinned `aiogram==3.3.0` не имеет typed wrapper для `verifyUser`,
реализация использует изолированный raw Bot API helper
`bot/services/verify_user.py`. Helper POST'ит JSON-payload на endpoint
`verifyUser`, использует URL из `bot.session.api.api_url(...)` для поддержки
local Bot API server, валидирует positive `user_id` и ограничение
`custom_description` в 70 символов до HTTP-вызова и поднимает
transport/Telegram `ok: false`/unexpected-result ошибки как `VerifyUserError`.

Выбран отдельный admin verification scenario:
`/verifyuser <user_id> confirm [custom_description]`. Оператор должен заранее
проверить user identity, product rules, право бота на verification action,
audit trail и rollback plan. Команда не вызывает `free-claude-code`, не тратит
Stars и не смешивается с gifts или Premium gifting. Rollback должен выполняться
отдельным remove-verification действием, когда оно доступно в боте.

Product rules и audit log:

- команда доступна только chat id из `TELEGRAM_ADMIN_CHAT_IDS` и не делает
  fallback на `TELEGRAM_ALLOWED_CHAT_IDS`; если список пустой, команда
  отключена;
- команда требует literal `confirm` в том же сообщении, которое запускает
  verification action;
- parser принимает positive `user_id`; optional `custom_description` ограничен
  70 символами до отправки;
- structured logs включают `user_id` и факт наличия description, но не сам
  description и не unrelated chat data;
- Telegram permission/transport/rate-limit errors возвращаются в admin chat.

### removeUserVerification

Команда `/removeuserverification` вызывает Telegram `removeUserVerification`
(Bot API 10.0) для удаления верификации пользователя от имени бота, которому
Telegram выдал право управлять user verification. По официальной документации
метод требует только `user_id` и возвращает boolean `True`. Специальные update
types не нужны, потому что сценарий запускается обычным admin message update;
доступность пользователя и право бота на removal action проверяет Telegram.

Так как pinned `aiogram==3.3.0` не имеет typed wrapper для
`removeUserVerification`, реализация использует изолированный raw Bot API
helper `bot/services/remove_user_verification.py`. Helper POST'ит JSON-payload
на endpoint `removeUserVerification`, использует URL из
`bot.session.api.api_url(...)` для поддержки local Bot API server, валидирует
positive `user_id` до HTTP-вызова и поднимает transport/Telegram `ok: false`/
unexpected-result ошибки как `RemoveUserVerificationError`.

Выбран отдельный admin verification scenario:
`/removeuserverification <user_id> confirm`. Оператор должен заранее проверить
user identity, product rules, право бота на verification removal, audit trail и
rollback plan. Команда не вызывает `free-claude-code`, не тратит Stars и не
смешивается с gifts или Premium gifting. Rollback выполняется отдельным
confirmed `/verifyuser <user_id> confirm [custom_description]` действием.

Product rules и audit log:

- команда доступна только chat id из `TELEGRAM_ADMIN_CHAT_IDS` и не делает
  fallback на `TELEGRAM_ALLOWED_CHAT_IDS`; если список пустой, команда
  отключена;
- команда требует literal `confirm` в том же сообщении, которое запускает
  verification removal action;
- parser принимает только positive `user_id`;
- structured logs включают `user_id`, но не unrelated chat data;
- Telegram permission/transport/rate-limit errors возвращаются в admin chat.

### verifyChat

Команда `/verifychat` вызывает Telegram `verifyChat` (Bot API 10.0) для
верификации чата от имени бота, которому Telegram выдал право верифицировать
чаты. По официальной документации метод требует `chat_id`, опционально
принимает `custom_description` и возвращает boolean `True`. Специальные update
types не нужны, потому что сценарий запускается обычным admin message update;
доступность чата и право бота на верификацию проверяет Telegram.

Так как pinned `aiogram==3.3.0` не имеет typed wrapper для `verifyChat`,
реализация использует изолированный raw Bot API helper
`bot/services/verify_chat.py`. Helper POST'ит JSON-payload на endpoint
`verifyChat`, использует URL из `bot.session.api.api_url(...)` для поддержки
local Bot API server, валидирует non-zero numeric `chat_id`, non-empty string
`chat_id` и ограничение `custom_description` в 70 символов до HTTP-вызова и
поднимает transport/Telegram `ok: false`/unexpected-result ошибки как
`VerifyChatError`.

Выбран отдельный admin verification scenario:
`/verifychat <chat_id|@username> confirm [custom_description]`. Оператор должен
заранее проверить chat identity, product rules, право бота на verification
action, audit trail и rollback plan. Команда не вызывает `free-claude-code`, не
тратит Stars и не смешивается с gifts или Premium gifting. Rollback должен
выполняться отдельным remove-verification действием, когда оно доступно в боте.

Product rules и audit log:

- команда доступна только chat id из `TELEGRAM_ADMIN_CHAT_IDS` и не делает
  fallback на `TELEGRAM_ALLOWED_CHAT_IDS`; если список пустой, команда
  отключена;
- команда требует literal `confirm` в том же сообщении, которое запускает
  verification action;
- parser принимает non-zero numeric `chat_id` или string `@username`; optional
  `custom_description` ограничен 70 символами до отправки;
- structured logs включают `chat_id` и факт наличия description, но не сам
  description и не unrelated chat data;
- Telegram permission/privacy/validation/transport/rate-limit errors
  возвращаются в admin chat.

### removeChatVerification

Команда `/removechatverification` вызывает Telegram `removeChatVerification`
(Bot API 10.0) для удаления верификации чата от имени бота, которому Telegram
выдал право управлять chat verification. По официальной документации метод
требует `chat_id` и возвращает boolean `True`. Специальные update types не
нужны, потому что сценарий запускается обычным admin message update;
доступность чата и право бота на removal action проверяет Telegram.

Так как pinned `aiogram==3.3.0` не имеет typed wrapper для
`removeChatVerification`, реализация использует изолированный raw Bot API
helper `bot/services/remove_chat_verification.py`. Helper POST'ит JSON-payload
на endpoint `removeChatVerification`, использует URL из
`bot.session.api.api_url(...)` для поддержки local Bot API server, валидирует
non-zero numeric `chat_id` или non-empty string `chat_id` до HTTP-вызова и
поднимает transport/Telegram `ok: false`/unexpected-result ошибки как
`RemoveChatVerificationError`.

Выбран отдельный admin verification scenario:
`/removechatverification <chat_id|@username> confirm`. Оператор должен заранее
проверить chat identity, product rules, право бота на verification removal,
audit trail и rollback plan. Команда не вызывает `free-claude-code`, не тратит
Stars и не смешивается с gifts или Premium gifting. Rollback выполняется
отдельным confirmed `/verifychat <chat_id|@username> confirm
[custom_description]` действием.

Product rules и audit log:

- команда доступна только chat id из `TELEGRAM_ADMIN_CHAT_IDS` и не делает
  fallback на `TELEGRAM_ALLOWED_CHAT_IDS`; если список пустой, команда
  отключена;
- команда требует literal `confirm` в том же сообщении, которое запускает
  verification removal action;
- parser принимает non-zero numeric `chat_id` или string `@username`;
- structured logs включают `chat_id`, но не unrelated chat data;
- Telegram permission/privacy/validation/transport/rate-limit errors
  возвращаются в admin chat.

### sendLocation

Команда `/location` вызывает typed aiogram API `Bot.send_location()` для метода
Telegram `sendLocation`. По официальной документации метод требует `chat_id`,
`latitude` и `longitude` и возвращает отправленное `Message`. Опциональный
`horizontal_accuracy` (0-1500 м) задает радиус неопределенности; live-локация
запускается через `live_period` (60-86400 с), а для live-локаций `heading`
(1-360°) задает направление движения и `proximity_alert_radius` (1-100000 м) —
дистанцию для proximity-уведомлений. Параметры соответствуют typed wrapper'у
pinned `aiogram==3.3.0` (Bot API 7.0).

Выбран admin-сценарий исходящего ответа: оператор отправляет точку на карте в
чат как настоящую Telegram-локацию, а не только текстовую интерпретацию.
Целевой чат всегда тот, где вызвана команда. Синтаксис:
`/location <latitude> <longitude>`. Координаты передаются в десятичных градусах.

У локаций нет caption, поэтому команда не принимает текст подписи: лишние токены
после долготы игнорируются. Координаты парсятся как числа с плавающей точкой, а
затем проверяются на диапазоны (`latitude` -90..90, `longitude` -180..180) до
обращения к Telegram, чтобы validation path не зависел от ошибки Telegram.
Координаты могут раскрывать местоположение человека, поэтому в structured logs
пишутся только факт live-локации и id отправленного сообщения, без самих
координат.

`/location` относится к исходящим ответам и закрыт строгим admin allowlist:

- команда доступна только chat id из `TELEGRAM_ADMIN_CHAT_IDS` и не делает
  fallback на `TELEGRAM_ALLOWED_CHAT_IDS`; если `TELEGRAM_ADMIN_CHAT_IDS`
  пустой, команда отключена;
- при отсутствии или нечисловых координатах команда показывает usage, при
  координатах вне допустимых диапазонов — сообщение о допустимом диапазоне, и в
  обоих случаях не обращается к Telegram;
- ошибки Telegram (например, отсутствие прав на отправку в чат) возвращаются
  пользователю, а отправка не выполняется.

Команда не взаимодействует с `free-claude-code`. Глобальный
`RateLimitMiddleware` применяется к `/location` так же, как к другим командам.

### editMessageLiveLocation

Команда `/editlivelocation` вызывает Telegram Bot API
`editMessageLiveLocation` через изолированный raw Bot API helper. Метод
редактирует активную live location, ранее отправленную ботом, и принимает либо
`chat_id` + `message_id`, либо `inline_message_id`, а также обязательные
`latitude` и `longitude`. Опциональные параметры соответствуют официальной
сигнатуре: `horizontal_accuracy` (0-1500 м), `heading` (1-360°) и
`proximity_alert_radius` (1-100000 м). Telegram возвращает отредактированный
`Message` для обычного сообщения или `True` для inline-сообщения.

Выбран message-management admin-сценарий для streaming, moderation и media
flows: оператор может передвинуть уже опубликованную live location без создания
нового сообщения. Синтаксис:
`/editlivelocation <chat_id> <message_id> <latitude> <longitude>` или
`/editlivelocation inline=<inline_message_id> <latitude> <longitude>`.
Дополнительные параметры передаются флагами `accuracy=...`, `heading=...` и
`proximity=...`.

Параметры валидируются до обращения к Telegram: `message_id` должен быть
положительным, координаты должны попадать в диапазоны latitude -90..90 и
longitude -180..180, optional accuracy/heading/proximity — в документированные
Telegram диапазоны. Команда не требует дополнительных update types, так как
запускается обычным сообщением из admin-чата. Для групп/каналов Telegram
проверяет, что бот может редактировать целевое live-location сообщение; метод
применим только к live locations, отправленным ботом, включая inline target.

Privacy/security impact: координаты могут раскрывать местоположение человека,
поэтому structured logs фиксируют только идентификаторы target message и наличие
optional параметров, но не latitude/longitude. Команда закрыта строгим
`TELEGRAM_ADMIN_CHAT_IDS`, не использует fallback на `TELEGRAM_ALLOWED_CHAT_IDS`
и не вызывает `free-claude-code`. Rollback выполняется повторным вызовом с
предыдущими координатами либо остановкой live location через отдельный
`stopMessageLiveLocation`/ручное действие Telegram. Ошибки Telegram,
авторизации, transport и rate-limit возвращаются оператору в admin chat.

### stopMessageLiveLocation

Команда `/stoplivelocation` вызывает Telegram Bot API
`stopMessageLiveLocation` через изолированный raw Bot API helper. Метод
останавливает активную live location, ранее отправленную ботом, и принимает
либо `chat_id` + `message_id`, либо `inline_message_id`. Telegram возвращает
отредактированный `Message` для обычного сообщения или `True` для
inline-сообщения. Optional `reply_markup` поддержан на уровне сервиса для
совместимости с официальной сигнатурой, но не выставлен в пользовательский
синтаксис команды, чтобы не принимать сложный JSON из admin-чата.

Выбран тот же message-management admin-сценарий для streaming, moderation и
media flows: оператор может завершить уже опубликованную live location без
ручного перехода в Telegram client. Синтаксис:
`/stoplivelocation <chat_id> <message_id>` или
`/stoplivelocation inline=<inline_message_id>`.

Параметры валидируются до обращения к Telegram: для обычного target нужны оба
поля `chat_id` и `message_id`, `message_id` должен быть положительным, а inline
target нельзя смешивать с regular target. Команда не требует дополнительных
update types, так как запускается обычным сообщением из admin-чата. Telegram
проверяет, что бот может редактировать целевое live-location сообщение; метод
применим только к live locations, отправленным ботом, включая inline target.

Privacy/security impact ниже, чем у обновления координат: команда не принимает
новые координаты и structured logs фиксируют только идентификаторы target
message, наличие inline target и наличие reply markup. Команда закрыта строгим
`TELEGRAM_ADMIN_CHAT_IDS`, не использует fallback на
`TELEGRAM_ALLOWED_CHAT_IDS` и не вызывает `free-claude-code`. Rollback прямым
повторным вызовом невозможен: после остановки нужно отправить новую live
location или восстановить состояние вручную в Telegram. Ошибки Telegram,
авторизации, transport и rate-limit возвращаются оператору в admin chat.

### sendVenue

Команда `/venue` вызывает typed aiogram API `Bot.send_venue()` для метода
Telegram `sendVenue`. По официальной документации метод требует `chat_id`,
`latitude`, `longitude`, `title` и `address` и возвращает отправленное
`Message`. Заведение можно опционально связать с местом в Foursquare через
`foursquare_id` и `foursquare_type` (например `arts_entertainment/aquarium`)
или с местом в Google Places через `google_place_id` и `google_place_type`.
Параметры соответствуют typed wrapper'у pinned `aiogram==3.3.0` (Bot API 7.0);
`business_connection_id` и более новые поля появились в последующих версиях Bot
API и в этот wrapper не входят.

Выбран admin-сценарий исходящего ответа: оператор отправляет заведение в чат как
настоящий Telegram venue (именованное место с названием и адресом, закрепленное
на карте), а не только текстовую интерпретацию. Целевой чат всегда тот, где
вызвана команда. Синтаксис: `/venue <latitude> <longitude> <title> | <address>`.
Координаты передаются в десятичных градусах.

`title` и `address` следуют за координатами и разделяются вертикальной чертой
(`|`); оба могут содержать пробелы и оба обязательны. Координаты парсятся как
числа с плавающей точкой, а затем проверяются на диапазоны (`latitude` -90..90,
`longitude` -180..180) до обращения к Telegram, чтобы validation path не зависел
от ошибки Telegram. Заведение раскрывает конкретное место и адрес, поэтому в
structured logs пишутся только факт наличия Foursquare/Google Places metadata и
id отправленного сообщения, без самих координат, названия и адреса.

`/venue` относится к исходящим ответам и закрыт строгим admin allowlist:

- команда доступна только chat id из `TELEGRAM_ADMIN_CHAT_IDS` и не делает
  fallback на `TELEGRAM_ALLOWED_CHAT_IDS`; если `TELEGRAM_ADMIN_CHAT_IDS`
  пустой, команда отключена;
- при отсутствии или нечисловых координатах, отсутствии разделителя или пустых
  title/address команда показывает usage, при координатах вне допустимых
  диапазонов — сообщение о допустимом диапазоне, и в обоих случаях не обращается
  к Telegram;
- ошибки Telegram (например, отсутствие прав на отправку в чат) возвращаются
  пользователю, а отправка не выполняется.

Команда не взаимодействует с `free-claude-code`. Глобальный
`RateLimitMiddleware` применяется к `/venue` так же, как к другим командам.

### sendPoll

Команда `/poll` вызывает typed aiogram API `Bot.send_poll()` для метода
Telegram `sendPoll`. По официальной документации метод требует `chat_id`,
`question` (1-300 символов) и `options` (2-10 строк по 1-100 символов) и
возвращает отправленное `Message`. По умолчанию опрос анонимный и типа
`regular`; для quiz-опроса передаются `type="quiz"` и `correct_option_id`, а
опционально — `explanation`. `open_period` (5-600 секунд) или `close_date`
задают автоматическое закрытие, а `is_closed` отправляет уже закрытый опрос для
предпросмотра. Параметры соответствуют typed wrapper'у pinned `aiogram==3.3.0`
(Bot API 7.0); в этой версии `options` — это список строк (в Bot API 7.3 он стал
списком `InputPollOption`), а `business_connection_id` и более новые поля в
wrapper не входят.

Выбран admin-сценарий исходящего ответа: оператор отправляет в чат настоящий
нативный Telegram-опрос (интерактивный вопрос с вариантами ответа), а не только
текстовую интерпретацию. Целевой чат всегда тот, где вызвана команда. Синтаксис:
`/poll <question> | <option> | <option> [| <option> ...]`. Вопрос идет первым, за
ним следуют варианты ответа, все разделяются вертикальной чертой (`|`); вопрос и
каждый вариант могут содержать пробелы.

Команда сама проверяет validation path до обращения к Telegram: при отсутствии
аргументов, отсутствии разделителя (а значит и вариантов) или пустом вопросе/
варианте показывается usage; при количестве вариантов вне диапазона 2-10 —
сообщение о допустимом количестве; при превышении длины вопроса (300) или
варианта (100) — сообщение о допустимой длине. Опрос отправляется с дефолтами
Telegram (анонимный одиночный regular-опрос). Вопрос и варианты ответа — это
контент, который оператор решил опубликовать, поэтому в structured logs пишутся
только количество вариантов, признак quiz и id отправленного сообщения, без
текста вопроса и вариантов.

`/poll` относится к исходящим ответам и закрыт строгим admin allowlist:

- команда доступна только chat id из `TELEGRAM_ADMIN_CHAT_IDS` и не делает
  fallback на `TELEGRAM_ALLOWED_CHAT_IDS`; если `TELEGRAM_ADMIN_CHAT_IDS`
  пустой, команда отключена;
- при невалидном вводе команда показывает usage или сообщение об ограничении и
  не обращается к Telegram;
- ошибки Telegram (например, отсутствие прав на отправку в чат) возвращаются
  пользователю, а отправка не выполняется.

Команда не взаимодействует с `free-claude-code`. Глобальный
`RateLimitMiddleware` применяется к `/poll` так же, как к другим командам.

### stopPoll

Команда `/stoppoll` вызывает typed aiogram API `Bot.stop_poll()` для метода
Telegram `stopPoll`. По официальной документации метод требует `chat_id` и
`message_id` сообщения с опросом, опционально принимает новый `reply_markup` и
возвращает финальный объект `Poll`. В pinned `aiogram==3.3.0` этот метод
доступен как typed wrapper, поэтому raw Bot API helper не нужен.

Выбран отдельный admin message-management сценарий: оператор закрывает активный
нативный опрос, ранее отправленный этим ботом, по chat/message id. Синтаксис:
`/stoppoll <chat_id> <message_id>`. `chat_id` принимает numeric id или username
канала вида `@channel`, `message_id` должен быть положительным числом. Команда
не требует специальных update types, потому что запускается обычным admin
message update.

Telegram сам проверяет ключевые ограничения: опрос должен быть отправлен ботом,
должен оставаться открытым, а бот должен иметь доступ к целевому чату и
сообщению. При ошибках Telegram, например если poll уже закрыт, сообщение не
является poll или бот больше не имеет доступа к чату, команда возвращает текст
ошибки в admin chat и пишет warning log с target chat/message id. Текст вопроса
и варианты ответа не пишутся в structured logs; success log содержит только
target chat/message id, итоговый poll id и количество options.

`/stoppoll` закрыт строгим admin allowlist:

- команда доступна только chat id из `TELEGRAM_ADMIN_CHAT_IDS` и не делает
  fallback на `TELEGRAM_ALLOWED_CHAT_IDS`; если `TELEGRAM_ADMIN_CHAT_IDS`
  пустой, команда отключена;
- при невалидном вводе команда показывает usage или validation error и не
  обращается к Telegram;
- rollback для уже закрытого poll отсутствует в Bot API: восстановить тот же
  poll как открытый нельзя, можно только отправить новый `/poll`.

Команда не взаимодействует с `free-claude-code`. Глобальный
`RateLimitMiddleware` применяется к `/stoppoll` так же, как к другим командам.

### approveSuggestedPost

Команда `/approvesuggestedpost` вызывает raw Bot API helper для метода Telegram
`approveSuggestedPost`, потому что pinned `aiogram==3.3.0` не содержит typed
wrapper для Bot API 10.0. По официальной документации метод требует `chat_id`
direct messages chat и `message_id` suggested post, опционально принимает
`send_date` как Unix timestamp и возвращает `True` при успехе.

Выбран отдельный admin message-management сценарий: оператор одобряет suggested
post по chat/message id из trusted update или другого operator-controlled
источника. Синтаксис: `/approvesuggestedpost <chat_id> <message_id> [send_date]`.
`chat_id` принимает numeric id или username вида `@channel`, `message_id` должен
быть положительным числом, `send_date` при наличии должен быть положительным Unix
time. Если `send_date` не передан, Telegram использует дату публикации из самой
suggestion.

Telegram сам проверяет ключевые ограничения: целевое сообщение должно быть
approvable suggested post, бот должен иметь необходимые права в direct messages
chat, а указанный `send_date` должен соответствовать правилам Telegram. При
ошибках Telegram команда возвращает текст ошибки в admin chat и пишет warning
log с target chat/message id без пользовательского содержимого suggested post.
Success log содержит только target chat/message id и факт наличия `send_date`.

`/approvesuggestedpost` закрыт строгим admin allowlist:

- команда доступна только chat id из `TELEGRAM_ADMIN_CHAT_IDS` и не делает
  fallback на `TELEGRAM_ALLOWED_CHAT_IDS`; если `TELEGRAM_ADMIN_CHAT_IDS`
  пустой, команда отключена;
- при невалидном вводе команда показывает usage или validation error и не
  обращается к Telegram;
- rollback для уже одобренного suggested post отсутствует в этом helper:
  отмена/изменение публикации должна выполняться отдельным поддерживаемым
  Telegram flow, если он применим к конкретному состоянию сообщения.

Команда не взаимодействует с `free-claude-code`. Глобальный
`RateLimitMiddleware` применяется к `/approvesuggestedpost` так же, как к другим
командам.

### declineSuggestedPost

Команда `/declinesuggestedpost` вызывает raw Bot API helper для метода Telegram
`declineSuggestedPost`, потому что pinned `aiogram==3.3.0` не содержит typed
wrapper для Bot API 10.0. По официальной документации метод требует `chat_id`
direct messages chat и `message_id` suggested post, опционально принимает
`comment` для автора suggested post длиной 0-128 символов и возвращает `True`
при успехе.

Выбран отдельный admin message-management сценарий: оператор отклоняет suggested
post по chat/message id из trusted update или другого operator-controlled
источника. Синтаксис: `/declinesuggestedpost <chat_id> <message_id> [comment]`.
`chat_id` принимает numeric id или username вида `@channel`, `message_id` должен
быть положительным числом, `comment` при наличии передается Telegram после
trim-validation и не может быть длиннее 128 символов.

Telegram сам проверяет ключевые ограничения: целевое сообщение должно быть
declinable suggested post, бот должен иметь `can_manage_direct_messages`
administrator right в соответствующем channel chat, а состояние suggested post
должно позволять отклонение. При ошибках Telegram команда возвращает текст
ошибки в admin chat и пишет warning log с target chat/message id без текста
comment. Success log содержит только target chat/message id и факт наличия
comment.

`/declinesuggestedpost` закрыт строгим admin allowlist:

- команда доступна только chat id из `TELEGRAM_ADMIN_CHAT_IDS` и не делает
  fallback на `TELEGRAM_ALLOWED_CHAT_IDS`; если `TELEGRAM_ADMIN_CHAT_IDS`
  пустой, команда отключена;
- при невалидном вводе команда показывает usage или validation error и не
  обращается к Telegram;
- rollback для уже отклоненного suggested post отсутствует в этом helper:
  повторная отправка или новый suggested post должны выполняться отдельным
  Telegram flow.

Команда не взаимодействует с `free-claude-code`. Глобальный
`RateLimitMiddleware` применяется к `/declinesuggestedpost` так же, как к другим
командам.

### sendContact

Команда `/contact` вызывает typed aiogram API `Bot.send_contact()` для метода
Telegram `sendContact`. По официальной документации метод требует `chat_id`,
`phone_number` и `first_name` контакта и возвращает отправленное `Message`.
Опционально передаются `last_name` и `vcard` (дополнительные данные о контакте
в формате vCard, 0-2048 байт). Параметры соответствуют typed wrapper'у pinned
`aiogram==3.3.0` (Bot API 7.0); более новые поля (`business_connection_id`,
`message_effect_id` и т.п.) в wrapper не входят.

Выбран admin-сценарий исходящего ответа: оператор отправляет в чат настоящий
Telegram-контакт (имя с номером телефона, который получатель может сохранить в
адресную книгу), а не только текстовую интерпретацию. Целевой чат всегда тот,
где вызвана команда. Синтаксис: `/contact <phone_number> <first_name>
[| <last_name>]`. Номер телефона идет первым одним токеном, за ним first_name;
опциональный last_name отделяется вертикальной чертой (`|`). first_name может
содержать пробелы.

Команда сама проверяет validation path до обращения к Telegram: при отсутствии
аргументов, отсутствии first_name или пустом first_name показывается usage; если
last_name-сегмент пустой, last_name считается отсутствующим. Номер телефона и
имя контакта — это персональные данные, которые оператор решил передать, поэтому
в structured logs пишутся только признак наличия last_name/vCard и id
отправленного сообщения, без самого номера и имени.

`/contact` относится к исходящим ответам и закрыт строгим admin allowlist:

- команда доступна только chat id из `TELEGRAM_ADMIN_CHAT_IDS` и не делает
  fallback на `TELEGRAM_ALLOWED_CHAT_IDS`; если `TELEGRAM_ADMIN_CHAT_IDS`
  пустой, команда отключена;
- при невалидном вводе команда показывает usage и не обращается к Telegram;
- ошибки Telegram (например, невалидный номер или отсутствие прав на отправку в
  чат) возвращаются пользователю, а отправка не выполняется.

Команда не взаимодействует с `free-claude-code`. Глобальный
`RateLimitMiddleware` применяется к `/contact` так же, как к другим командам.

### sendDice

Команда `/dice` вызывает typed aiogram API `Bot.send_dice()` для метода
Telegram `sendDice`. По официальной документации метод требует только `chat_id`
и возвращает отправленное `Message`; выпавшее значение выбирает Telegram, и оно
доступно в `Message.dice`. Опциональный `emoji` задает анимацию и должен быть
одним из `🎲`, `🎯`, `🏀`, `⚽`, `🎳` или `🎰` (диапазон значений зависит от
эмодзи: 1-6 для `🎲`, `🎯` и `🎳`, 1-5 для `🏀` и `⚽`, 1-64 для `🎰`); без
аргумента Telegram отправляет `🎲`. Параметры соответствуют typed wrapper'у
pinned `aiogram==3.3.0` (Bot API 7.0); более новые поля
(`business_connection_id`, `message_effect_id` и т.п.) в wrapper не входят.

Выбран admin-сценарий исходящего ответа: оператор отправляет в чат настоящую
анимированную Telegram-кость (анимированный эмодзи со случайным значением), а не
только текстовую интерпретацию. Целевой чат всегда тот, где вызвана команда.
Синтаксис: `/dice [emoji]`. Без аргумента отправляется 🎲; единственный
опциональный аргумент — один из поддерживаемых эмодзи.

Команда сама проверяет validation path до обращения к Telegram: при
неподдерживаемом эмодзи или более чем одном аргументе показывается usage, и
Telegram не вызывается. Кость не несет переданного оператором контента, поэтому
в structured logs пишутся выбранный эмодзи, признак тихой доставки и id
отправленного сообщения.

`/dice` относится к исходящим ответам и закрыт строгим admin allowlist:

- команда доступна только chat id из `TELEGRAM_ADMIN_CHAT_IDS` и не делает
  fallback на `TELEGRAM_ALLOWED_CHAT_IDS`; если `TELEGRAM_ADMIN_CHAT_IDS`
  пустой, команда отключена;
- при невалидном вводе команда показывает usage и не обращается к Telegram;
- ошибки Telegram (например, отсутствие прав на отправку в чат) возвращаются
  пользователю, а отправка не выполняется.

Команда не взаимодействует с `free-claude-code`. Глобальный
`RateLimitMiddleware` применяется к `/dice` так же, как к другим командам.

### sendChecklist

Команда `/checklist` отправляет чеклист — озаглавленный список из 1-30 задач,
которые получатели могут отмечать выполненными, — методом Telegram
`sendChecklist` (введен в Bot API 9.1). По официальной документации метод
отправляет сообщение от имени подключенного business account, поэтому требует
`business_connection_id` (идентификатор живого business connection), `chat_id` и
`checklist` (объект `InputChecklist`) и возвращает отправленное `Message`.
`title` в `InputChecklist` ограничен 1-255 символами, каждый task — 1-100
символами после парсинга entities, а каждый task несет положительный `id`,
уникальный в пределах чеклиста. Так как метод действует от имени business
account, его нельзя включать в обычный чат без business-mode: бот должен быть
подключен к business account, а `business_connection_id` — соответствовать
действующему подключению.

Ключевое отличие от `sendPoll`: pinned `aiogram==3.3.0` (Bot API 7.0) не имеет
typed wrapper для этого метода Bot API 9.1. Поэтому реализация идет через
изолированный raw Bot API helper `bot/services/send_checklist.py`, который сам
собирает JSON-payload (с JSON-сериализацией объекта `checklist`) и POST'ит его на
endpoint `sendChecklist` через `httpx`, не завися от typed aiogram метода. URL
endpoint берется из `bot.session.api.api_url(...)`, чтобы учесть кастомный local
Bot API server, с fallback на cloud-endpoint. Ошибки транспорта и ответы Telegram
с `ok: false` поднимаются как единое исключение `SendChecklistError`.

Выбран admin-сценарий исходящего ответа: оператор отправляет в чат настоящий
Telegram-чеклист от имени подключенного business account, а не только текстовую
интерпретацию. Целевой чат всегда тот, где вызвана команда. Синтаксис:
`/checklist <business_connection_id> <title> | <task> [| <task> ...]`.
Идентификатор подключения идет первым (одним токеном без пробелов), затем
заголовок и задачи, разделенные вертикальной чертой. Обработчик сам присваивает
задачам последовательные `id`, начиная с 1.

Команда сама проверяет validation path до обращения к Telegram: при отсутствии
`business_connection_id`, заголовка или хотя бы одной задачи (а также при пустом
сегменте) показывается usage; при слишком длинном заголовке (>255), количестве
задач вне диапазона 1-30 или слишком длинной задаче (>100) — соответствующее
сообщение, и Telegram не вызывается. Заголовок и тексты задач — переданный
оператором контент, поэтому в structured logs пишутся только количество задач,
признак защиты контента и id отправленного сообщения.

`/checklist` относится к исходящим ответам и закрыт строгим admin allowlist:

- команда доступна только chat id из `TELEGRAM_ADMIN_CHAT_IDS` и не делает
  fallback на `TELEGRAM_ALLOWED_CHAT_IDS`; если `TELEGRAM_ADMIN_CHAT_IDS`
  пустой, команда отключена;
- при невалидном вводе команда показывает usage или сообщение о превышении
  лимитов и не обращается к Telegram;
- ошибки Telegram (например, отсутствующий или истекший `business_connection_id`
  либо недостаточные права бизнес-подключения) возвращаются пользователю, а
  отправка не выполняется.

Команда не взаимодействует с `free-claude-code`. Глобальный
`RateLimitMiddleware` применяется к `/checklist` так же, как к другим командам.

### editMessageChecklist

Команда `/editchecklist` редактирует ранее отправленное checklist-сообщение от
имени подключенного business account методом Telegram `editMessageChecklist`
(Bot API 10.0). По официальной документации метод принимает обязательные
`business_connection_id`, `chat_id`, `message_id` и `checklist` (`InputChecklist`)
и возвращает отредактированное `Message`; опционально поддерживается
`reply_markup` с inline keyboard. Метод относится к business-account flow:
`business_connection_id` должен быть живым подключением, а бот должен иметь
права этого подключения на редактирование целевого checklist message. Для
командного сценария специальных `allowed_updates` не требуется, потому что
оператор запускает обычную admin-команду.

Pinned `aiogram==3.3.0` не имеет typed wrapper для Bot API 10.0
`editMessageChecklist`, поэтому реализация идет через изолированный raw helper
`bot/services/edit_message_checklist.py`. Helper собирает payload,
JSON-сериализует `checklist` и optional `reply_markup`, выбирает endpoint через
`bot.session.api.api_url(...)` с fallback на cloud Bot API и поднимает ошибки
транспорта или Telegram `ok: false` как `EditMessageChecklistError`.

Выбран message-management сценарий: администратор может обновить checklist,
который был отправлен business account, без смешивания с обычным Claude
streaming. Синтаксис команды:
`/editchecklist <business_connection_id> <chat_id> <message_id> <title> | <task> [| <task> ...]`.
`chat_id` и `message_id` указывают целевое сообщение, а replacement checklist
строится так же, как в `/checklist`: title, 1-30 tasks, sequential task ids с 1.
Локальная validation path отклоняет отсутствующие поля, неположительный
`message_id`, пустые сегменты, title длиннее 255 символов, task длиннее 100
символов или число задач вне 1-30 до обращения к Telegram.

Команда доступна только в `TELEGRAM_ADMIN_CHAT_IDS`, не делает fallback на
`TELEGRAM_ALLOWED_CHAT_IDS`, не вызывает `free-claude-code`, и на нее действует
глобальный `RateLimitMiddleware`. Privacy/security impact такой же, как у
`/checklist`: operator-provided title и task text не пишутся в structured logs;
логи содержат target ids, task count и форму ошибки. Rollback выполняется
повторным `/editchecklist` с прежним checklist content или ручным редактированием
от имени подключенного business account в Telegram.

### postStory

Команда `/poststory` публикует photo story от имени managed business account
методом Telegram `postStory` (Bot API 10.0). По официальной документации метод
требует `business_connection_id`, `content` (`InputStoryContent`) и
`active_period`; `active_period` может быть только 21600, 43200, 86400 или
172800 секунд. Дополнительно поддерживаются caption до 2048 символов,
`parse_mode`, `caption_entities`, clickable `areas`, `post_to_chat_page` и
`protect_content`. Для вызова у business-подключения должно быть право
`can_manage_stories`; специальных update types для самой команды не требуется,
так как оператор запускает ее обычным сообщением из admin-чата.

Pinned `aiogram==3.3.0` не имеет typed wrapper для Bot API 10.0 `postStory`,
поэтому реализация использует изолированный raw Bot API helper
`bot/services/post_story.py`. Helper собирает JSON payload, сериализует
`content` в JSON-строку, POST'ит endpoint `postStory` через `httpx` и возвращает
объект `Story` как dict. URL берется из `bot.session.api.api_url(...)` с fallback
на cloud endpoint, чтобы сохранить совместимость с local Bot API server.
Transport errors и ответы Telegram `ok: false` приводятся к `PostStoryError`.

Выбран отдельный admin publishing flow, не смешанный с Claude chat replies:
`/poststory <business_connection_id> <active_period> <photo_file_id> [caption]`.
Команда сейчас сознательно exposes только photo story из Telegram `file_id`;
upload, URL-публикация, story areas и `post_to_chat_page` оставлены для
отдельных расширений, чтобы не размывать минимальный проверяемый сценарий.
Handler валидирует обязательные аргументы, допустимый active period и caption
length до обращения к Telegram.

Privacy/security модель такая же, как у других business admin actions:
`/poststory` доступен только chat id из `TELEGRAM_ADMIN_CHAT_IDS`, не делает
fallback на `TELEGRAM_ALLOWED_CHAT_IDS` и не вызывает `free-claude-code`.
Structured logs не содержат caption text или полного content object; пишутся
business connection id, active period, option flags и returned story id. Ошибки
Telegram по устаревшему `business_connection_id`, отсутствующему
`can_manage_stories`, некорректному media или rate limit возвращаются оператору.
Rollback операционный: удалить или архивировать story в Telegram; отдельный
Bot API `deleteStory` покрывается своей backlog-задачей.

### editStory

Команда `/editstory` редактирует photo story, ранее опубликованную ботом от
имени managed business account, методом Telegram `editStory` (Bot API 10.0).
По официальной документации метод требует `business_connection_id`, `story_id`
и replacement `content` (`InputStoryContent`). Дополнительно поддерживаются
caption до 2048 символов, `parse_mode`, `caption_entities` и clickable `areas`.
Для вызова у business-подключения должно быть право `can_manage_stories`;
специальных update types для самой команды не требуется, так как оператор
запускает ее обычным сообщением из admin-чата.

Pinned `aiogram==3.3.0` не имеет typed wrapper для Bot API 10.0 `editStory`,
поэтому реализация использует изолированный raw Bot API helper
`bot/services/edit_story.py`. Helper собирает JSON payload, сериализует
`content` в JSON-строку, POST'ит endpoint `editStory` через `httpx` и возвращает
объект `Story` как dict. URL берется из `bot.session.api.api_url(...)` с fallback
на cloud endpoint, чтобы сохранить совместимость с local Bot API server.
Transport errors и ответы Telegram `ok: false` приводятся к `EditStoryError`.

Выбран отдельный admin publishing flow, не смешанный с Claude chat replies:
`/editstory <business_connection_id> <story_id> <photo_file_id> [caption]`.
Команда сейчас сознательно exposes только replacement photo story из Telegram
`file_id`; upload, URL-редактирование и story areas оставлены для отдельных
расширений, чтобы минимальный сценарий оставался проверяемым. Handler валидирует
обязательные аргументы, positive `story_id` и caption length до обращения к
Telegram.

Privacy/security модель такая же, как у других business admin actions:
`/editstory` доступен только chat id из `TELEGRAM_ADMIN_CHAT_IDS`, не делает
fallback на `TELEGRAM_ALLOWED_CHAT_IDS` и не вызывает `free-claude-code`.
Structured logs не содержат caption text или полного content object; пишутся
business connection id, исходный story id, наличие caption и returned story id.
Ошибки Telegram по устаревшему `business_connection_id`, отсутствующему
`can_manage_stories`, недоступному story, некорректному media или rate limit
возвращаются оператору. Rollback операционный: повторно вызвать `/editstory` с
прежним media/caption, если они сохранены, либо отредактировать или архивировать
story в Telegram.

### getBusinessConnection

Команда `/businessconnection` получает объект Telegram `BusinessConnection` по
`business_connection_id` методом `getBusinessConnection` (Bot API 10.0). Метод
нужен для business connection и managed-bot сценариев: оператор может проверить
live-подключение, владельца, `user_chat_id`, дату подключения, `can_reply` и
`is_enabled` перед дальнейшими действиями от имени business account.

Pinned `aiogram==3.3.0` не имеет typed wrapper для этого метода, поэтому
реализация идет через изолированный raw Bot API helper
`bot/services/get_business_connection.py`. Helper POST'ит JSON payload
`{"business_connection_id": ...}` на endpoint `getBusinessConnection` через
`httpx`, берет URL через `bot.session.api.api_url(...)` для поддержки local Bot
API server и поднимает транспортные ошибки или Telegram `ok: false` как
`GetBusinessConnectionError`.

Сценарий намеренно узкий и защищенный: `/businessconnection
<business_connection_id>` доступен только chat id из `TELEGRAM_ADMIN_CHAT_IDS` и
не делает fallback на `TELEGRAM_ALLOWED_CHAT_IDS`; при пустом admin allowlist
команда отключена. Значение `business_connection_id` обязательно, должно быть
одним токеном и приходить из live business connection update или другого
доверенного operator source. При отсутствии id показывается usage и Telegram не
вызывается.

Security/privacy impact: команда раскрывает owner и lifecycle metadata
business-подключения, но не управляет токенами, не вызывает managed-bot token
methods и не меняет состояние подключения. В structured logs попадают только
`business_connection_id`, булевы признаки `can_reply`/`is_enabled` и наличие
`user_chat_id`; owner name, username, полный объект и потенциально чувствимые
поля не логируются. Rollback прост: убрать `/businessconnection` из admin
allowlist или очистить `TELEGRAM_ADMIN_CHAT_IDS`, после чего поверхность
выключена без изменения бизнес-подключений.

Команда не взаимодействует с `free-claude-code`. Глобальный
`RateLimitMiddleware` применяется к `/businessconnection` так же, как к другим
командам.

### getBusinessAccountStarBalance

Команда `/businessstarbalance` получает Telegram `StarAmount` для подключенного
business account по `business_connection_id` методом
`getBusinessAccountStarBalance` (Bot API 10.0). Это read-only admin diagnostic
для проверки доступного Stars balance перед отдельными gift/transfer flows.

Pinned `aiogram==3.3.0` не имеет typed wrapper для этого метода, поэтому
реализация идет через изолированный raw Bot API helper
`bot/services/get_business_account_star_balance.py`. Helper POST'ит JSON
payload `{"business_connection_id": ...}` на endpoint
`getBusinessAccountStarBalance` через `httpx`, берет URL через
`bot.session.api.api_url(...)` для поддержки local Bot API server и поднимает
транспортные ошибки или Telegram `ok: false` как
`GetBusinessAccountStarBalanceError`.

Сценарий защищен так же, как остальные business-account команды:
`/businessstarbalance <business_connection_id>` доступен только chat id из
`TELEGRAM_ADMIN_CHAT_IDS` и не делает fallback на `TELEGRAM_ALLOWED_CHAT_IDS`;
при пустом admin allowlist команда отключена. Telegram дополнительно проверяет
ownership подключения, live `business_connection_id` и business right
`can_view_gifts_and_stars`; такие ошибки возвращаются оператору без retry.

Security/privacy impact: команда раскрывает финансовый баланс Telegram Stars,
поэтому результат показывается только в admin-чате. Structured logs пишут
`business_connection_id` и наличие `nanostar_amount`, но не саму сумму Stars.
Команда не вызывает `free-claude-code`, не меняет состояние Telegram и не
выполняет transfer; для перевода Stars должен использоваться отдельный явный
flow.

### transferBusinessAccountStars

Команда `/transferbusinessstars <business_connection_id> <star_count> confirm`
переводит Telegram Stars с баланса подключенного business account на баланс
бота методом `transferBusinessAccountStars` (Bot API 10.0). Метод принимает
live `business_connection_id` и положительный целочисленный `star_count`;
Telegram на своей стороне проверяет, что подключение активно, принадлежит
боту, на балансе достаточно Stars и текущие business rights включают
`can_transfer_stars`.

Pinned `aiogram==3.3.0` не имеет typed wrapper для этого метода, поэтому
реализация идет через изолированный raw Bot API helper
`bot/services/transfer_business_account_stars.py`. Helper POST'ит JSON payload
`{"business_connection_id": ..., "star_count": ...}` на endpoint
`transferBusinessAccountStars` через `httpx`, берет URL через
`bot.session.api.api_url(...)` для поддержки local Bot API server и поднимает
validation errors, транспортные ошибки, невалидный JSON, Telegram `ok: false`
и неожиданный result как `TransferBusinessAccountStarsError`.

Сценарий намеренно отделен от read-only `/businessstarbalance`: сначала
оператор может проверить баланс, затем выполнить перевод только отдельной
командой с явным `confirm`. Команда доступна только chat id из
`TELEGRAM_ADMIN_CHAT_IDS` и не делает fallback на
`TELEGRAM_ALLOWED_CHAT_IDS`; при пустом admin allowlist команда отключена.
Security/privacy impact: команда перемещает финансовую ценность с business
account на баланс бота, поэтому она не вызывается автоматически, не связана с
`free-claude-code` и не использует обычный allowed-chat режим. Structured logs
содержат `business_connection_id`, `star_count` и форму ошибки, но не полный
объект business connection или owner metadata.

Rollback ограничен операционно: сам перевод не откатывается ботом. Для
остановки сценария нужно убрать admin chat из `TELEGRAM_ADMIN_CHAT_IDS`, удалить
handler или отозвать у бота Telegram business right `can_transfer_stars`.

### convertGiftToStars

Команда `/convertgiftstars <business_connection_id> <owned_gift_id> confirm`
конвертирует один regular owned gift подключенного business account в Telegram
Stars методом `convertGiftToStars` (Bot API 10.0). Метод принимает live
`business_connection_id` и `owned_gift_id`; Telegram на своей стороне проверяет,
что подключение активно, принадлежит боту, подарок существует, подходит для
конвертации и текущие business rights позволяют конвертировать gifts to Stars.

Pinned `aiogram==3.3.0` не имеет typed wrapper для этого метода, поэтому
реализация идет через изолированный raw Bot API helper
`bot/services/convert_gift_to_stars.py`. Helper POST'ит JSON payload
`{"business_connection_id": ..., "owned_gift_id": ...}` на endpoint
`convertGiftToStars` через `httpx`, берет URL через
`bot.session.api.api_url(...)` для поддержки local Bot API server и поднимает
validation errors, транспортные ошибки, невалидный JSON, Telegram `ok: false`
и неожиданный result как `ConvertGiftToStarsError`.

Сценарий намеренно отделен от read-only `/businessgifts`: оператор сначала
получает trusted `owned_gift_id`, затем запускает конвертацию отдельной
командой с явным `confirm`. Команда доступна только chat id из
`TELEGRAM_ADMIN_CHAT_IDS` и не делает fallback на
`TELEGRAM_ALLOWED_CHAT_IDS`; при пустом admin allowlist команда отключена.
Security/privacy impact: команда уничтожает исходный gift в пользу Stars,
поэтому она не вызывается автоматически, не связана с `free-claude-code` и не
использует обычный allowed-chat режим. Structured logs содержат
`business_connection_id`, `owned_gift_id` и форму ошибки, но не полный gift
payload или owner metadata.

Rollback ограничен операционно: конвертация не откатывается ботом. Для
остановки сценария нужно убрать admin chat из `TELEGRAM_ADMIN_CHAT_IDS`, удалить
handler или отозвать у бота Telegram business right для конвертации gifts to
Stars.

### upgradeGift

Команда `/upgradegift <business_connection_id> <owned_gift_id> [keep_original_details=true|false] confirm`
повышает один owned gift подключенного business account методом `upgradeGift`
(Bot API 10.0). Метод принимает live `business_connection_id`, `owned_gift_id`
и optional `keep_original_details`; Telegram на своей стороне проверяет, что
подключение активно, принадлежит боту, подарок существует, может быть upgraded,
на business account достаточно Stars и текущие business rights позволяют
transfer/upgrade gifts.

Pinned `aiogram==3.3.0` не имеет typed wrapper для этого метода, поэтому
реализация идет через изолированный raw Bot API helper
`bot/services/upgrade_gift.py`. Helper POST'ит JSON payload
`{"business_connection_id": ..., "owned_gift_id": ...}` с optional
`keep_original_details` на endpoint `upgradeGift` через `httpx`, берет URL через
`bot.session.api.api_url(...)` для поддержки local Bot API server и поднимает
validation errors, транспортные ошибки, невалидный JSON, Telegram `ok: false`
и неожиданный result как `UpgradeGiftError`.

Сценарий намеренно отделен от read-only `/businessgifts` и от
`/convertgiftstars`: оператор сначала получает trusted `owned_gift_id`, затем
запускает upgrade отдельной командой с явным `confirm`. Команда доступна только
chat id из `TELEGRAM_ADMIN_CHAT_IDS` и не делает fallback на
`TELEGRAM_ALLOWED_CHAT_IDS`; при пустом admin allowlist команда отключена.
Security/privacy impact: команда тратит Stars business account и изменяет gift,
поэтому она не вызывается автоматически, не связана с `free-claude-code` и не
использует обычный allowed-chat режим. Structured logs содержат
`business_connection_id`, `owned_gift_id`, optional `keep_original_details` и
форму ошибки, но не полный gift payload или owner metadata.

Rollback ограничен операционно: upgrade не откатывается ботом. Для остановки
сценария нужно убрать admin chat из `TELEGRAM_ADMIN_CHAT_IDS`, удалить handler
или отозвать у бота Telegram business right для transfer/upgrade gifts.

### readBusinessMessage

Команда `/readbusinessmessage <business_connection_id> <message_id>` помечает
одно сообщение подключенного business account как прочитанное методом
`readBusinessMessage` (Bot API 10.0). Метод принимает только live
`business_connection_id` и `message_id`; Telegram на своей стороне проверяет,
что сообщение принадлежит указанному business connection, что подключение еще
активно и что текущие права бота позволяют выполнить операцию.

Pinned `aiogram==3.3.0` не имеет typed wrapper для этого метода, поэтому
реализация идет через изолированный raw Bot API helper
`bot/services/read_business_message.py`. Helper POST'ит JSON payload
`{"business_connection_id": ..., "message_id": ...}` на endpoint
`readBusinessMessage` через `httpx`, берет URL через
`bot.session.api.api_url(...)` для поддержки local Bot API server и ожидает
Telegram result `true`. Транспортные ошибки, невалидный JSON, Telegram
`ok: false` и неожиданный result поднимаются как `ReadBusinessMessageError`.

Сценарий изолирован от остальных business-account методов: команда не читает
профиль, gifts, Stars balance и не вызывает `free-claude-code`. Локальная
валидация проверяет, что `business_connection_id` передан одним токеном, а
`message_id` является положительным целым числом; при ошибке ввода показывается
usage и Telegram не вызывается. Required update types для самой команды не
отличаются от обычных message updates, но значения должны приходить из live
business connection updates или другого доверенного operator source.

Security/privacy impact: команда меняет состояние прочитанности сообщения,
поэтому доступна только chat id из `TELEGRAM_ADMIN_CHAT_IDS` и не делает
fallback на `TELEGRAM_ALLOWED_CHAT_IDS`; при пустом admin allowlist команда
отключена. Structured logs содержат только `business_connection_id`,
`message_id` и форму ошибки; содержимое сообщения, owner-поля и полный ответ
Telegram не логируются. Rollback операционный: убрать admin chat из
`TELEGRAM_ADMIN_CHAT_IDS` или удалить handler/helper; уже выставленный read
state в Telegram обратным действием не откатывается.

Глобальный `RateLimitMiddleware` применяется к `/readbusinessmessage` так же,
как к другим командам.

### setBusinessAccountName

Команда `/setbusinessaccountname <business_connection_id> <first_name>
[last_name]` меняет имя подключенного business account методом
`setBusinessAccountName` (Bot API 10.0). Метод принимает live
`business_connection_id`, обязательный `first_name` и опциональный `last_name`;
Telegram на своей стороне проверяет, что подключение активно, принадлежит
боту и текущие business rights позволяют менять профиль.

Pinned `aiogram==3.3.0` не имеет typed wrapper для этого метода, поэтому
реализация идет через изолированный raw Bot API helper
`bot/services/set_business_account_name.py`. Helper POST'ит JSON payload
`{"business_connection_id": ..., "first_name": ..., "last_name": ...}` на
endpoint `setBusinessAccountName` через `httpx`, берет URL через
`bot.session.api.api_url(...)` для поддержки local Bot API server и ожидает
Telegram result `true`. Если `last_name` не передан, поле не добавляется в
payload. Транспортные ошибки, невалидный JSON, Telegram `ok: false` и
неожиданный result поднимаются как `SetBusinessAccountNameError`.

Сценарий намеренно ограничен простой CLI-формой: `first_name` и `last_name`
парсятся как одиночные токены длиной до 64 символов каждый. При ошибке ввода
показывается usage и Telegram не вызывается. Значение `business_connection_id`
должно приходить из live business connection update или другого доверенного
operator source.

Security/privacy impact: команда меняет публичные profile metadata business
account, поэтому доступна только chat id из `TELEGRAM_ADMIN_CHAT_IDS` и не
делает fallback на `TELEGRAM_ALLOWED_CHAT_IDS`; при пустом admin allowlist
команда отключена. Structured logs содержат только `business_connection_id`,
признак наличия `last_name` и форму ошибки; сами значения имени не логируются.
Rollback операционный: вернуть прежнее имя через Telegram или отключить
admin chat до дальнейших изменений.

### setBusinessAccountUsername

Команда `/setbusinessaccountusername <business_connection_id> <username>`
меняет публичный username подключенного business account методом
`setBusinessAccountUsername` (Bot API 10.0). Метод принимает live
`business_connection_id` и новый `username`; Telegram на своей стороне
проверяет, что подключение активно, принадлежит боту, текущие business rights
позволяют менять профиль, а username валиден и доступен.

Pinned `aiogram==3.3.0` не имеет typed wrapper для этого метода, поэтому
реализация идет через изолированный raw Bot API helper
`bot/services/set_business_account_username.py`. Helper POST'ит JSON payload
`{"business_connection_id": ..., "username": ...}` на endpoint
`setBusinessAccountUsername` через `httpx`, берет URL через
`bot.session.api.api_url(...)` для поддержки local Bot API server и ожидает
Telegram result `true`. Транспортные ошибки, невалидный JSON, Telegram
`ok: false` и неожиданный result поднимаются как
`SetBusinessAccountUsernameError`.

Сценарий намеренно ограничен простой CLI-формой: `username` парсится как
одиночный токен, допускается ввод с префиксом `@`, после нормализации длина
должна быть 5-32 символа. При ошибке ввода показывается usage и Telegram не
вызывается. Значение `business_connection_id` должно приходить из live business
connection update или другого доверенного operator source.

Security/privacy impact: команда меняет публичные profile metadata business
account, поэтому доступна только chat id из `TELEGRAM_ADMIN_CHAT_IDS` и не
делает fallback на `TELEGRAM_ALLOWED_CHAT_IDS`; при пустом admin allowlist
команда отключена. Structured logs содержат только `business_connection_id` и
форму ошибки; сам username не логируется. Rollback операционный: вернуть
прежний username через Telegram или отключить
поверхность, убрав admin chat из `TELEGRAM_ADMIN_CHAT_IDS`/удалив handler.

### setBusinessAccountBio

Команда `/setbusinessaccountbio <business_connection_id> <bio|clear>` меняет
или очищает публичный bio подключенного business account методом
`setBusinessAccountBio` (Bot API 10.0). Метод принимает live
`business_connection_id` и опциональный `bio` длиной 0-140 символов; Telegram
на своей стороне проверяет, что подключение активно, принадлежит боту и
текущие business rights включают `can_change_bio`.

Pinned `aiogram==3.3.0` не имеет typed wrapper для этого метода, поэтому
реализация идет через изолированный raw Bot API helper
`bot/services/set_business_account_bio.py`. Helper POST'ит JSON payload
`{"business_connection_id": ..., "bio": ...}` на endpoint
`setBusinessAccountBio` через `httpx`, берет URL через
`bot.session.api.api_url(...)` для поддержки local Bot API server и ожидает
Telegram result `true`. Если `bio` не передан helper'у, поле не добавляется в
payload; CLI-команда использует keyword `clear`, чтобы явно отправить пустой
bio и очистить профиль. Транспортные ошибки, невалидный JSON, Telegram
`ok: false` и неожиданный result поднимаются как
`SetBusinessAccountBioError`.

Сценарий намеренно ограничен admin CLI-формой: `bio` может содержать пробелы,
но ограничен 140 символами; пустой bio вводится только как `clear`, чтобы не
смешивать usage error и очистку. При ошибке ввода показывается usage и
Telegram не вызывается. Значение `business_connection_id` должно приходить из
live business connection update или другого доверенного operator source.

Security/privacy impact: команда меняет публичные profile metadata business
account, поэтому доступна только chat id из `TELEGRAM_ADMIN_CHAT_IDS` и не
делает fallback на `TELEGRAM_ALLOWED_CHAT_IDS`; при пустом admin allowlist
команда отключена. Structured logs содержат только `business_connection_id`,
признак наличия `bio` и форму ошибки; сам bio не логируется. Rollback
операционный: вернуть прежний bio через Telegram, выполнить `clear` или
отключить поверхность, убрав admin chat из `TELEGRAM_ADMIN_CHAT_IDS`/удалив
handler.

### setBusinessAccountProfilePhoto

Команда `/setbusinessaccountprofilephoto <business_connection_id> <photo_path> [public=true|false]`
меняет static JPG profile photo подключенного business account методом
`setBusinessAccountProfilePhoto` (Bot API 10.0). Метод принимает live
`business_connection_id`, объект `InputProfilePhoto` и опциональный
`is_public`; Telegram на своей стороне проверяет, что подключение активно,
принадлежит боту и текущие business rights включают `can_edit_profile_photo`.
Флаг `public=true` задает публичную fallback-фотографию, видимую даже когда
основная фотография скрыта privacy settings.

Pinned `aiogram==3.3.0` не имеет typed wrapper для этого метода, поэтому
реализация идет через изолированный raw multipart Bot API helper
`bot/services/set_business_account_profile_photo.py`. Helper POST'ит multipart
payload на endpoint `setBusinessAccountProfilePhoto` через `httpx`, берет URL
через `bot.session.api.api_url(...)` для поддержки local Bot API server и
отправляет `photo={"type":"static","photo":"attach://photo"}` вместе с новым
локальным JPG upload. Транспортные ошибки, невалидный JSON, Telegram
`ok: false` и неожиданный result поднимаются как
`SetBusinessAccountProfilePhotoError`.

Сценарий намеренно ограничен admin CLI-формой: `photo_path` должен быть
локальным файлом, доступным процессу бота; Telegram profile photos нельзя
переиспользовать по URL или `file_id`, нужен fresh upload. При ошибке ввода
показывается usage и Telegram не вызывается. Значение `business_connection_id`
должно приходить из live business connection update или другого доверенного
operator source.

Security/privacy impact: команда меняет публичные profile metadata business
account, поэтому доступна только chat id из `TELEGRAM_ADMIN_CHAT_IDS` и не
делает fallback на `TELEGRAM_ALLOWED_CHAT_IDS`; при пустом admin allowlist
команда отключена. Structured logs содержат `business_connection_id`,
локальный path, `is_public` и форму ошибки; содержимое файла не логируется.
Rollback операционный: повторно установить прежнюю фотографию через эту команду,
изменить профиль через Telegram или отключить поверхность, убрав admin chat из
`TELEGRAM_ADMIN_CHAT_IDS`/удалив handler.

Команда `/removebusinessaccountprofilephoto <business_connection_id> [public=true|false] confirm`
удаляет main или public fallback profile photo подключенного business account
методом `removeBusinessAccountProfilePhoto` (Bot API 10.0). Метод принимает
live `business_connection_id` и опциональный `is_public`; Telegram на своей
стороне проверяет, что подключение активно, принадлежит боту и текущие
business rights включают `can_edit_profile_photo`.

Pinned `aiogram==3.3.0` не имеет typed wrapper для этого метода, поэтому
реализация идет через изолированный raw Bot API helper
`bot/services/remove_business_account_profile_photo.py`. Helper POST'ит JSON
payload на endpoint `removeBusinessAccountProfilePhoto` через `httpx`, берет
URL через `bot.session.api.api_url(...)` для поддержки local Bot API server и
поднимает транспортные ошибки, невалидный JSON, Telegram `ok: false` и
неожиданный result как `RemoveBusinessAccountProfilePhotoError`.

Сценарий намеренно ограничен admin CLI-формой и требует явный `confirm`.
Значение `business_connection_id` должно приходить из live business connection
update или другого доверенного operator source. Security/privacy impact:
команда меняет публичные profile metadata business account, поэтому доступна
только chat id из `TELEGRAM_ADMIN_CHAT_IDS` и не делает fallback на
`TELEGRAM_ALLOWED_CHAT_IDS`; при пустом admin allowlist команда отключена.
Structured logs содержат `business_connection_id`, `is_public` и форму ошибки.
Rollback операционный: повторно установить прежнюю фотографию через
`/setbusinessaccountprofilephoto`, изменить профиль через Telegram или
отключить поверхность, убрав admin chat из `TELEGRAM_ADMIN_CHAT_IDS`/удалив
handler.

Команда `/setbusinessaccountgiftsettings <business_connection_id>
show_gift_button=true|false unlimited_gifts=true|false
limited_gifts=true|false unique_gifts=true|false
premium_subscription=true|false gifts_from_channels=true|false` меняет
incoming gift privacy settings подключенного business account методом
`setBusinessAccountGiftSettings` (Bot API 10.0). Метод принимает live
`business_connection_id`, обязательный boolean `show_gift_button` и полный
объект `AcceptedGiftTypes`; Telegram на своей стороне проверяет, что
подключение активно, принадлежит боту и текущие business rights включают
`can_change_gift_settings`.

Pinned `aiogram==3.3.0` не имеет typed wrapper для этого метода, поэтому
реализация идет через изолированный raw Bot API helper
`bot/services/set_business_account_gift_settings.py`. Helper POST'ит JSON
payload на endpoint `setBusinessAccountGiftSettings` через `httpx`, берет URL
через `bot.session.api.api_url(...)` для поддержки local Bot API server и
поднимает validation errors, транспортные ошибки, невалидный JSON, Telegram
`ok: false` и неожиданный result как
`SetBusinessAccountGiftSettingsError`.

Сценарий намеренно ограничен admin CLI-формой. Все пять флагов
`AcceptedGiftTypes` передаются явно, чтобы оператор и ревью видели полный
эффект изменения. Security/privacy impact: команда меняет gift privacy
business account, поэтому доступна только chat id из
`TELEGRAM_ADMIN_CHAT_IDS` и не делает fallback на
`TELEGRAM_ALLOWED_CHAT_IDS`; при пустом admin allowlist команда отключена.
Structured logs содержат `business_connection_id`, `show_gift_button`, число
включенных типов подарков и форму ошибки. Rollback операционный: повторно
запустить команду с прежними значениями, изменить настройки через Telegram или
отключить поверхность, убрав admin chat из `TELEGRAM_ADMIN_CHAT_IDS`/удалив
handler.

Команда `/businessgifts <business_connection_id>
[exclude_unsaved=true|false] [exclude_saved=true|false]
[exclude_unlimited=true|false] [exclude_limited=true|false]
[exclude_unique=true|false] [sort_by_price=true|false] [offset=<offset>]
[limit=1..100]` получает страницу `OwnedGifts` подключенного business account
методом `getBusinessAccountGifts` (Bot API 10.0). Метод принимает live
`business_connection_id`, опциональные фильтры сохраненности и типов подарков,
`sort_by_price`, pagination `offset` и `limit` от 1 до 100. Required update
types для самого вызова не нужны, но `business_connection_id` должен прийти из
business connection update или другого доверенного operator source. Telegram
на своей стороне проверяет, что подключение активно, принадлежит боту и текущие
business rights позволяют просматривать gifts/Stars.

Pinned `aiogram==3.3.0` не имеет typed wrapper для этого метода, поэтому
реализация идет через изолированный raw Bot API helper
`bot/services/get_business_account_gifts.py`. Helper POST'ит JSON payload на
endpoint `getBusinessAccountGifts` через `httpx`, берет URL через
`bot.session.api.api_url(...)` для поддержки local Bot API server и поднимает
validation errors, транспортные ошибки, невалидный JSON, Telegram `ok: false`
и неожиданный result как `GetBusinessAccountGiftsError`.

Сценарий строго read-only и отделен от convert/upgrade/transfer gift flows:
команда только отображает до 10 элементов и next offset, а операции с
ценностью требуют отдельных явных команд. Security/privacy impact: список
owned gifts раскрывает активы business account, поэтому команда доступна
только chat id из `TELEGRAM_ADMIN_CHAT_IDS` и не делает fallback на
`TELEGRAM_ALLOWED_CHAT_IDS`; при пустом admin allowlist команда отключена.
Structured logs содержат `business_connection_id`, количество элементов,
наличие `next_offset` и форму ошибки, но не полный gift payload. Rollback
операционный: прекратить использовать команду, убрать admin chat из
`TELEGRAM_ADMIN_CHAT_IDS`, удалить handler или ограничить business rights в
Telegram. Интеграционные проверки opt-in, потому что нужен реальный bot token
и live business connection id.

Глобальный `RateLimitMiddleware` применяется к `/setbusinessaccountname`,
`/setbusinessaccountusername`, `/setbusinessaccountbio`,
`/setbusinessaccountprofilephoto`, `/removebusinessaccountprofilephoto` и
`/setbusinessaccountgiftsettings` так же, как к другим командам.
`/businessgifts` также проходит через общий rate-limit pipeline команд.
`/transferbusinessstars` также проходит через общий rate-limit pipeline команд.

Команда `/transfergift <business_connection_id> <owned_gift_id>
<new_owner_chat_id> [star_count=<stars>] confirm` передает уникальный gift,
которым владеет подключенный business account, другому user/channel chat
методом `transferGift` (Bot API 10.0). Метод принимает live
`business_connection_id`, `owned_gift_id`, обязательный integer
`new_owner_chat_id` и опциональный `star_count` для оплаты transfer fee
Telegram Stars. Required update types для самого вызова не нужны, но
`business_connection_id` и `owned_gift_id` должны прийти из business connection
update, `/businessgifts` или другого доверенного operator source. Telegram на
своей стороне проверяет, что подключение активно, принадлежит боту, gift
является transferable unique gift, новый владелец допустим, а текущие business
rights включают возможность transfer/upgrade gifts; если fee не prepaid,
также нужны Stars на business balance и право использовать их.

Pinned `aiogram==3.3.0` не имеет typed wrapper для `transferGift`, поэтому
реализация идет через изолированный raw Bot API helper
`bot/services/transfer_gift.py`. Helper POST'ит JSON payload на endpoint
`transferGift` через `httpx`, берет URL через `bot.session.api.api_url(...)`
для поддержки local Bot API server и поднимает validation errors,
транспортные ошибки, невалидный JSON, Telegram `ok: false` и неожиданный
result как `TransferGiftError`. Успешным считается только Telegram result
`true`.

Сценарий намеренно отделен от read-only `/businessgifts` и от
`/convertgiftstars`/`/upgradegift`: оператор сначала проверяет ownership и fee,
затем запускает отдельную команду с обязательным `confirm`. Security/privacy
impact: команда меняет владельца ценного актива и может тратить Telegram
Stars, поэтому доступна только chat id из `TELEGRAM_ADMIN_CHAT_IDS` и не делает
fallback на `TELEGRAM_ALLOWED_CHAT_IDS`; при пустом admin allowlist команда
отключена. Structured logs содержат `business_connection_id`, `owned_gift_id`,
target chat id, `star_count` и форму ошибки, но не полный gift payload.
Rollback операционный: перевод не может быть отменен ботом; нужно договориться
с новым владельцем о встречном transfer или отключить поверхность, убрав admin
chat из `TELEGRAM_ADMIN_CHAT_IDS`/удалив handler.
`/transfergift` также проходит через общий rate-limit pipeline команд.

Команда `/chatgifts <chat_id|@channelusername>
[exclude_unsaved=true|false] [exclude_saved=true|false]
[exclude_unlimited=true|false] [exclude_limited_upgradable=true|false]
[exclude_limited_non_upgradable=true|false]
[exclude_from_blockchain=true|false] [exclude_unique=true|false]
[sort_by_price=true|false] [offset=<offset>] [limit=1..100]` получает страницу
`OwnedGifts` channel chat методом `getChatGifts`. Метод принимает numeric
channel id или `@channelusername`, опциональные фильтры сохраненности и типов
подарков, blockchain filter, `sort_by_price`, pagination `offset` и `limit` от
1 до 100. Required update types для самого вызова не нужны; Telegram
ограничивает метод channel chats и может требовать `can_post_messages` admin
right для полной видимости.

Pinned `aiogram==3.3.0` не имеет typed wrapper для этого метода, поэтому
реализация идет через изолированный raw Bot API helper
`bot/services/get_chat_gifts.py`. Helper POST'ит JSON payload на endpoint
`getChatGifts` через `httpx`, берет URL через `bot.session.api.api_url(...)`
для поддержки local Bot API server и поднимает validation errors, транспортные
ошибки, невалидный JSON, Telegram `ok: false` и неожиданный result как
`GetChatGiftsError`.

Сценарий строго read-only и отделен от convert/upgrade/transfer gift flows:
команда только отображает до 10 элементов и next offset, а операции с ценностью
требуют отдельных явных команд. Security/privacy impact: список owned gifts
раскрывает активы channel chat, поэтому команда доступна только chat id из
`TELEGRAM_ADMIN_CHAT_IDS` и не делает fallback на `TELEGRAM_ALLOWED_CHAT_IDS`;
при пустом admin allowlist команда отключена. Structured logs содержат
`chat_id`, количество элементов, наличие `next_offset` и форму ошибки, но не
полный gift payload. Rollback операционный: прекратить использовать команду,
убрать admin chat из `TELEGRAM_ADMIN_CHAT_IDS`, удалить handler или ограничить
admin rights бота в Telegram. Интеграционные проверки opt-in, потому что нужен
реальный bot token и channel chat с gifts.

### getManagedBotToken

Команда `/managedbottoken <managed_bot_user_id>` получает строковый токен
управляемого Telegram-бота методом `getManagedBotToken` (Bot API 9.6). Метод
принимает только `user_id` управляемого бота; этот id должен приходить из
trusted operator source, например update `managed_bot` или сообщения с
`managed_bot_created`. Для получения самого update в polling/webhook
конфигурации нужно включать update type `managed_bot`, когда оператор строит
полный lifecycle flow.

Pinned `aiogram==3.3.0` не имеет typed wrapper для managed-bot token lifecycle,
поэтому реализация идет через изолированный raw Bot API helper
`bot/services/get_managed_bot_token.py`. Helper POST'ит JSON payload
`{"user_id": ...}` на endpoint `getManagedBotToken` через `httpx`, берет URL
через `bot.session.api.api_url(...)` для поддержки local Bot API server и
поднимает транспортные ошибки или Telegram `ok: false` как
`GetManagedBotTokenError`.

Сценарий намеренно вынесен в отдельный защищенный admin surface: команда
доступна только chat id из `TELEGRAM_ADMIN_CHAT_IDS`, не делает fallback на
`TELEGRAM_ALLOWED_CHAT_IDS` и отключена при пустом admin allowlist. `user_id`
валидируется локально как положительное целое число; при ошибке usage
показывается до обращения к Telegram. Telegram дополнительно проверяет, что
вызывающий бот имеет право управлять указанным ботом.

Security/privacy impact: успешный ответ содержит live bot token, поэтому токен
показывается только в ответе admin-чата и никогда не пишется в structured logs.
Логи содержат только `user_id`, тип/описание ошибки и длину токена при успехе.
Команда не вызывает `free-claude-code` и не меняет token lifecycle state.
Rollback при раскрытии токена выполняется через `replaceManagedBotToken` или
BotFather-ротацию; текущая команда только читает существующий токен.

`RateLimitMiddleware` применяется к `/managedbottoken` так же, как к другим
командам. Telegram permission, unknown managed-bot, transport и rate-limit
ошибки возвращаются оператору в admin chat.

### getManagedBotAccessSettings

Команда `/managedbotaccess <managed_bot_user_id>` получает объект
`BotAccessSettings` управляемого Telegram-бота методом
`getManagedBotAccessSettings` (Bot API 10.0). Метод принимает только `user_id`
управляемого бота; этот id должен приходить из trusted operator source,
например update `managed_bot` или сообщения с `managed_bot_created`. Для самой
команды не нужен отдельный update type, потому что ее запускает обычное
сообщение администратора. Update type `managed_bot` нужен только в полном
lifecycle flow, где оператор собирает id управляемого бота из Telegram updates.

По официальной документации результат содержит boolean
`is_access_restricted` и опциональный массив `added_users`. Если доступ
ограничен, владелец бота всегда сохраняет доступ, а `added_users` описывает
дополнительных пользователей allowlist. Pinned `aiogram==3.3.0` не имеет typed
wrapper для этого метода, поэтому реализация идет через изолированный raw Bot
API helper `bot/services/get_managed_bot_access_settings.py`. Helper POST'ит
JSON payload `{"user_id": ...}` на endpoint `getManagedBotAccessSettings`
через `httpx`, берет URL через `bot.session.api.api_url(...)` для поддержки
local Bot API server и поднимает транспортные ошибки или Telegram `ok: false`
как `GetManagedBotAccessSettingsError`.

Сценарий намеренно вынесен в отдельный защищенный admin surface: команда
доступна только chat id из `TELEGRAM_ADMIN_CHAT_IDS`, не делает fallback на
`TELEGRAM_ALLOWED_CHAT_IDS` и отключена при пустом admin allowlist. `user_id`
валидируется локально как положительное целое число; при ошибке usage
показывается до обращения к Telegram. Telegram дополнительно проверяет, что
вызывающий бот имеет право управлять указанным ботом.

Security/privacy impact: успешный ответ раскрывает access allowlist
управляемого бота. Ответ admin-чата показывает restricted flag, количество
пользователей и, если Telegram вернул `added_users`, краткие user ids/display
names. Structured logs не содержат полные user objects, имена или usernames:
логируются только `user_id`, `is_access_restricted` и `added_users_count`.
Команда не вызывает `free-claude-code`, не читает и не меняет токены, а
rollback для этой read-only поверхности состоит в удалении команды из admin
surface или последующем изменении доступа через `setManagedBotAccessSettings`.

`RateLimitMiddleware` применяется к `/managedbotaccess` так же, как к другим
командам. Telegram permission, unknown managed-bot, transport и rate-limit
ошибки возвращаются оператору в admin chat.

### setManagedBotAccessSettings

Команда `/setmanagedbotaccess <managed_bot_user_id> <restricted|open>
[added_user_id ...] confirm` изменяет объект `BotAccessSettings` управляемого
Telegram-бота методом `setManagedBotAccessSettings` (Bot API 10.0). Метод
принимает `user_id` управляемого бота и settings object с boolean
`is_access_restricted` и опциональным списком `added_users`. `restricted`
отправляет `is_access_restricted=true` и переданные positive integer user ids
как allowlist, а `open` отправляет `is_access_restricted=false` без allowlist.

Pinned `aiogram==3.3.0` не имеет typed wrapper для этого метода, поэтому
реализация идет через изолированный raw Bot API helper
`bot/services/set_managed_bot_access_settings.py`. Helper POST'ит JSON payload
`{"user_id": ..., "settings": ...}` на endpoint
`setManagedBotAccessSettings` через `httpx`, берет URL через
`bot.session.api.api_url(...)` для поддержки local Bot API server и поднимает
транспортные ошибки или Telegram `ok: false` как
`SetManagedBotAccessSettingsError`. Успешным считается только Telegram result
`true`; неожиданный результат трактуется как ошибка.

Сценарий вынесен в отдельный защищенный admin surface: команда доступна только
chat id из `TELEGRAM_ADMIN_CHAT_IDS`, не делает fallback на
`TELEGRAM_ALLOWED_CHAT_IDS` и отключена при пустом admin allowlist. `user_id` и
`added_user_id` валидируются локально как положительные целые числа; при ошибке
usage показывается до обращения к Telegram. Telegram дополнительно проверяет,
что вызывающий бот имеет право управлять указанным ботом.

Security/privacy impact: команда меняет, кто может получить доступ к
управляемому боту, поэтому требует literal `confirm`. Перед изменением оператор
должен получить текущее состояние через `/managedbotaccess`; rollback
выполняется повторным запуском `/setmanagedbotaccess` с прежним restricted flag
и прежними user ids. Ответ admin-чата показывает итоговый restricted flag и
allowlist ids, а structured logs содержат только `user_id`,
`is_access_restricted` и `added_users_count`.

`RateLimitMiddleware` применяется к `/setmanagedbotaccess` так же, как к другим
командам. Telegram permission, unknown managed-bot, transport и rate-limit
ошибки возвращаются оператору в admin chat.

### sendChatAction

`sendChatAction` показывает в чате transient-статус (например, `typing…`),
который сообщает пользователю, что бот занят. По официальной документации метод
требует `chat_id` и `action`, возвращает `True` и не создает сообщения: Telegram
сбрасывает статус примерно через пять секунд или как только бот отправит
сообщение. Реализация идет через typed aiogram API `Bot.send_chat_action()` в
`bot/services/send_chat_action.py`; `action` должен быть одним из поддерживаемых
значений (`typing`, `upload_photo`, `record_video`, `upload_video`,
`record_voice`, `upload_voice`, `upload_document`, `choose_sticker`,
`find_location`, `record_video_note`, `upload_video_note`), а неподдерживаемое
значение отклоняется исключением `SendChatActionError` до обращения к Telegram.
Опциональные `message_thread_id` (forum topic) и `business_connection_id`
соответствуют typed wrapper'у pinned `aiogram==3.3.0` (Bot API 7.0).

Выбран пользовательский сценарий из scope issue: показывать typing/upload
action, пока Claude/proxy обрабатывает заметно долгий запрос. Поскольку Telegram
сбрасывает статус через ~5 секунд, helper `keep_chat_action` — это async context
manager, который отправляет action сразу и обновляет его в фоновой задаче, пока
выполняется обернутый блок. `bot/handlers/chat.py` оборачивает обработку Claude
(и streaming, и non-streaming ветки) в `_typing_indicator`, который показывает
`typing…` до готовности ответа. Поведение управляется флагом
`TELEGRAM_CHAT_ACTION_ENABLED` (по умолчанию `true`); при `false` индикатор не
показывается и поведение остается прежним. Ошибки Telegram при обновлении
индикатора логируются и проглатываются, чтобы сбой отображения статуса не ломал
саму обработку запроса, а фоновая задача всегда отменяется при выходе из блока.

Дополнительно admin-команда `/chataction [action]` запускает action вручную (в
основном для проверки). Синтаксис: без аргумента показывается `typing`, а
единственный опциональный аргумент должен быть одним из поддерживаемых action.
Команда сама проверяет validation path до обращения к Telegram: при
неподдерживаемом action или более чем одном аргументе показывается usage, и
Telegram не вызывается. Action не несет переданного оператором контента, поэтому
в structured logs пишутся выбранный action, целевой чат и признаки forum
topic/business connection.

`/chataction` относится к исходящим ответам и закрыт строгим admin allowlist:

- команда доступна только chat id из `TELEGRAM_ADMIN_CHAT_IDS` и не делает
  fallback на `TELEGRAM_ALLOWED_CHAT_IDS`; если `TELEGRAM_ADMIN_CHAT_IDS`
  пустой, команда отключена;
- при невалидном вводе команда показывает usage и не обращается к Telegram;
- ошибки Telegram (например, отсутствие прав на отправку в чат) возвращаются
  пользователю.

Автоматический `typing…`-индикатор не требует admin-прав и работает для обычных
пользователей в рамках уже разрешенных чатов. Глобальный `RateLimitMiddleware`
применяется к `/chataction` так же, как к другим командам.

### sendMessageDraft

`sendMessageDraft` (Bot API 10.0) стримит частичное сообщение пользователю, пока
ответ еще генерируется. По официальной документации метод требует `chat_id`
**private chat** и ненулевой `draft_id`, принимает опциональные `text` (0-4096
символов после парсинга entities; пустой текст показывает плейсхолдер
«Thinking…»), `message_thread_id`, `parse_mode`/`entities` и возвращает `True`.
Draft — **эфемерный**: это временный ~30-секундный предпросмотр, поэтому после
завершения генерации финальный текст все равно нужно сохранить обычным
`sendMessage`. Изменения draft с одним и тем же `draft_id` анимируются, поэтому в
рамках одного ответа переиспользуется единый id. С 1 марта 2026 метод доступен
всем ботам, а с 8 мая 2026 разрешен пустой `text`.

Поскольку pinned `aiogram==3.3.0` (Bot API 7.0) не имеет typed wrapper для этого
метода Bot API 10.0, реализация — изолированный raw Bot API helper в
`bot/services/send_message_draft.py`: он POST-ит JSON на endpoint
`sendMessageDraft` через `httpx`, не завися от typed aiogram метода. URL берется
из сессии бота, поэтому local Bot API server тоже поддерживается. Нулевой
`draft_id` и слишком длинный `text` отклоняются исключением
`SendMessageDraftError` до обращения к Telegram; transport-ошибки и ответы
Telegram `ok: false` поднимаются тем же исключением. Текст draft несет
пользовательский/Claude-контент, поэтому в structured logs пишутся только
структурные метаданные (чат, `draft_id`, длина текста, признак плейсхолдера и
forum topic), но не сам текст.

Выбран сценарий из scope issue: использовать эфемерный draft preview как
альтернативу частым `editMessageText` во время генерации ответа. В
`bot/handlers/chat.py` функция `handle_streaming_with_draft` сразу показывает
плейсхолдер «Thinking…», затем по мере генерации обновляет draft частичным
текстом (обновления throttled до `DRAFT_UPDATE_INTERVAL_SECONDS`, чтобы не
заваливать эндпоинт мелкими дельтами), а по завершении сохраняет финальный ответ
обычными `sendMessage`. Ошибки показа эфемерного preview логируются и
проглатываются, чтобы сбой предпросмотра не ломал сам ответ. Draft-стриминг
включается флагом `TELEGRAM_MESSAGE_DRAFT_ENABLED` (по умолчанию `false`) и
применяется только в private chats (метод работает только в них); остальные чаты
сохраняют прежний edit-based streaming, а при `false` поведение не меняется.

Дополнительно admin-команда `/messagedraft [text]` запускает draft вручную (в
основном для проверки): без текста показывается плейсхолдер «Thinking…», а
опциональный текст ограничен 4096 символами с валидацией до обращения к Telegram.
`draft_id` берется из `message_id` (всегда положительный, значит ненулевой).

`/messagedraft` относится к исходящим ответам и закрыт строгим admin allowlist:

- команда доступна только chat id из `TELEGRAM_ADMIN_CHAT_IDS` и не делает
  fallback на `TELEGRAM_ALLOWED_CHAT_IDS`; если `TELEGRAM_ADMIN_CHAT_IDS`
  пустой, команда отключена;
- слишком длинный текст отклоняется с сообщением об ошибке и не обращается к
  Telegram;
- ошибки Telegram (например, чат не private или отсутствие прав) возвращаются
  пользователю.

Автоматический draft-стриминг не требует admin-прав и работает для обычных
пользователей в private chats в рамках уже разрешенных чатов. Глобальный
`RateLimitMiddleware` применяется к `/messagedraft` так же, как к другим
командам.

### sendMediaGroup

Команда `/mediagroup` вызывает typed aiogram API `Bot.send_media_group()` для
метода Telegram `sendMediaGroup`. По официальной документации метод требует
`chat_id` и `media` (массив из 2-10 элементов `InputMediaPhoto`,
`InputMediaVideo`, `InputMediaDocument` или `InputMediaAudio`) и возвращает
список отправленных `Message`. Telegram разрешает только определенные сочетания
типов в одном альбоме: документы группируются с документами, аудио — с аудио, а
фото и видео можно смешивать; передача элементов одного типа поэтому всегда дает
валидное сочетание. Параметры соответствуют typed wrapper'у pinned
`aiogram==3.3.0` (Bot API 7.0).

Выбран admin-сценарий исходящего медиа: оператор отправляет несколько медиа в
чат как единый альбом, а не отдельными сообщениями или только текстовой
интерпретацией. Целевой чат всегда тот, где вызвана команда. Синтаксис:
`/mediagroup <type> <url_or_file_id> <url_or_file_id> [<url_or_file_id> ...] [caption <text>]`.
`type` — один из `photo`, `video`, `document`, `audio`, и все элементы альбома
одного типа. Медиа передаются как URL, которые Telegram скачивает, или `file_id`
уже загруженных на серверы Telegram файлов.

Единый caption strategy: опциональная подпись следует за литеральным ключевым
словом `caption`, остаток сообщения становится текстом подписи (может содержать
пробелы) и применяется к альбому через `caption` только у первого элемента — так
Telegram отображает подпись альбома. Тип проверяется по списку поддерживаемых,
количество элементов — на диапазон 2-10, а длина caption — на лимит 1024 символа
до обращения к Telegram, чтобы validation path не зависел от ошибки Telegram.
Сам helper `bot/services/send_media_group.py` — тонкий typed-обертка, который
пишет в structured logs количество элементов и id отправленных сообщений.

`/mediagroup` относится к исходящему медиа и закрыт строгим admin allowlist:

- команда доступна только chat id из `TELEGRAM_ADMIN_CHAT_IDS` и не делает
  fallback на `TELEGRAM_ALLOWED_CHAT_IDS`; если `TELEGRAM_ADMIN_CHAT_IDS`
  пустой, команда отключена;
- при отсутствии типа или медиа команда показывает usage, при неподдерживаемом
  типе — сообщение о допустимых типах, при количестве вне диапазона 2-10 —
  сообщение о допустимом диапазоне, а при слишком длинном caption — сообщение о
  превышении лимита, и во всех случаях не обращается к Telegram;
- ошибки Telegram (например, недоступный чат или неверный `file_id`)
  возвращаются пользователю, а отправка не выполняется.

Команда не взаимодействует с `free-claude-code`. Глобальный
`RateLimitMiddleware` применяется к `/mediagroup` так же, как к другим командам.

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
между участниками группы. Если Telegram присылает официальный Guest Mode update
с `Message.guest_query_id`, финальный ответ отправляется через
`answerGuestQuery`, поэтому бот может вернуть ответ на `guest_message`, не
являясь полноценным участником чата.

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
- `TELEGRAM_ADMIN_CHAT_IDS`;
- `TELEGRAM_BOT_NAME`;
- `TELEGRAM_BOT_NAME_LANGUAGE_CODE`;
- `TELEGRAM_BOT_SHORT_DESCRIPTION`;
- `TELEGRAM_BOT_SHORT_DESCRIPTION_LANGUAGE_CODE`;
- `TELEGRAM_BOT_DESCRIPTION`;
- `TELEGRAM_BOT_DESCRIPTION_LANGUAGE_CODE`;
- `API_SECRET_TOKEN`;
- `RATE_LIMIT_REQUESTS_PER_MINUTE`;
- `LOG_LEVEL`.

`TELEGRAM_ALLOWED_CHAT_IDS` парсится как comma-separated список целых chat id.
Если список пустой, бот доступен во всех чатах.

`TELEGRAM_ADMIN_CHAT_IDS` парсится тем же способом и ограничивает доступ к
admin-командам `/webhook` и `/deletewebhook`. Для диагностики и lifecycle
команд при пустом списке используется fallback на `TELEGRAM_ALLOWED_CHAT_IDS`;
если оба списка пустые, эти команды недоступны. Для деструктивных `/logout`,
`/close`, для message-relay `/forward`, `/forwards`, `/copy`, `/copies` и для
исходящего медиа `/photo`, `/audio`, `/livephoto`, `/document`, `/video`,
`/videonote`, `/animation`, `/sticker`, `/voice`, `/paidmedia`, `/location`, `/venue`,
`/poll`, `/contact`, `/dice`, `/chataction`, `/messagedraft` и `/checklist`
fallback не применяется: команды требуют непустой `TELEGRAM_ADMIN_CHAT_IDS`,
иначе они отключены. Автоматический `typing…`-индикатор (управляемый
`TELEGRAM_CHAT_ACTION_ENABLED`), draft-стриминг (управляемый
`TELEGRAM_MESSAGE_DRAFT_ENABLED`) и startup sync/audit имени и описания бота
(управляемый `TELEGRAM_BOT_NAME`/`TELEGRAM_BOT_NAME_LANGUAGE_CODE` и
`TELEGRAM_BOT_DESCRIPTION`/`TELEGRAM_BOT_DESCRIPTION_LANGUAGE_CODE`) admin-прав
не требуют и работают для обычных пользователей в уже разрешенных чатах.

## Безопасность и ограничения доступа

Текущие защитные механизмы:

- webhook secret token при заданном `API_SECRET_TOKEN`;
- optional whitelist чатов через `TELEGRAM_ALLOWED_CHAT_IDS`;
- admin/ops allowlist для `/webhook` и `/deletewebhook` через
  `TELEGRAM_ADMIN_CHAT_IDS` с fallback на общий whitelist;
- строгий admin allowlist без fallback и обязательное подтверждение
  `/logout confirm` для деструктивного выхода из cloud Bot API;
- строгий admin allowlist без fallback и обязательное подтверждение
  `/close confirm` для деструктивного закрытия bot instance;
- строгий admin allowlist без fallback для `/forward` и `protect_content` по
  умолчанию, чтобы пересланный контент нельзя было переслать или сохранить
  дальше;
- строгий admin allowlist без fallback для `/forwards` и `protect_content` по
  умолчанию для пакетной пересылки с сохранением album grouping;
- строгий admin allowlist без fallback для `/copy` и `protect_content` по
  умолчанию, чтобы скопированный контент нельзя было переслать или сохранить
  дальше;
- строгий admin allowlist без fallback для `/copies` и `protect_content` по
  умолчанию для пакетного копирования без ссылки на источник с сохранением
  album grouping;
- строгий admin allowlist без fallback для `/photo`, чтобы только операторы
  могли заставить бота публиковать произвольные изображения как фото;
- строгий admin allowlist без fallback для `/audio`, чтобы только операторы
  могли заставить бота публиковать произвольные аудиофайлы как музыкальные
  треки;
- строгий admin allowlist без fallback для `/livephoto`, чтобы только операторы
  могли заставить бота публиковать произвольные live photo как видео с обложкой;
- строгий admin allowlist без fallback для `/document`, чтобы только операторы
  могли заставить бота публиковать произвольные файлы как документы;
- строгий admin allowlist без fallback для `/paidmedia`, чтобы только операторы
  могли заставить бота публиковать произвольное платное медиа с ценой в Telegram
  Stars;
- per-user rate limit в sliding window на 60 секунд;
- guest mode для групп;
- экранирование HTML в LLM-ответах перед Telegram HTML.

Ограничения:

- `API_SECRET_TOKEN` опционален на уровне настроек, хотя для webhook режима он
  практически обязателен;
- rate limit хранится в памяти и сбрасывается при рестарте;
- `/webhook` показывает webhook URL и последние ошибки доставки, а
  `/deletewebhook` меняет состояние доставки updates, поэтому эти команды
  нельзя оставлять доступными в публичных группах;
- `/logout` деструктивен (выход из cloud Bot API на 10 минут), поэтому требует
  явного admin allowlist и подтверждения, и его нельзя открывать публично;
- `/close` деструктивен (закрытие bot instance на текущем Bot API сервере),
  поэтому требует явного admin allowlist и подтверждения, и его нельзя
  открывать публично;
- `/forward` переносит чужой контент между чатами, поэтому требует явного admin
  allowlist и по умолчанию защищает пересланную копию `protect_content`; его
  нельзя открывать публично;
- `/forwards` переносит пакет чужих сообщений между чатами с сохранением album
  grouping, поэтому требует явного admin allowlist и по умолчанию защищает
  пересланные копии `protect_content`; его нельзя открывать публично;
- `/copy` переносит чужой контент между чатами без ссылки на источник, поэтому
  требует явного admin allowlist и по умолчанию защищает скопированное сообщение
  `protect_content`; его нельзя открывать публично;
- `/copies` переносит пакет чужих сообщений между чатами без ссылки на источник
  с сохранением album grouping, поэтому требует явного admin allowlist и по
  умолчанию защищает скопированные сообщения `protect_content`; его нельзя
  открывать публично;
- `/photo` заставляет бота публиковать произвольное изображение по URL или
  `file_id`, поэтому требует явного admin allowlist; его нельзя открывать
  публично;
- `/audio` заставляет бота публиковать произвольный аудиофайл по URL или
  `file_id`, поэтому требует явного admin allowlist; его нельзя открывать
  публично;
- `/livephoto` заставляет бота публиковать произвольное live photo по `file_id`,
  поэтому требует явного admin allowlist; его нельзя открывать публично;
- `/document` заставляет бота публиковать произвольный файл по URL или `file_id`,
  поэтому требует явного admin allowlist; его нельзя открывать публично;
- `/paidmedia` заставляет бота публиковать произвольное платное медиа с ценой в
  Telegram Stars по URL или `file_id`, поэтому требует явного admin allowlist;
  его нельзя открывать публично;
- нет persistent audit log, admin panel или метрик;
- нет отдельной проверки размера входных файлов перед скачиванием и обработкой.

## Наблюдаемость

`structlog` настроен на JSON output. `LoggingMiddleware` логирует входящие
сообщения, callback query, inline query и неизвестные update types.

`fetch_webhook_info()` логирует `webhook_info_fetched` с агрегированными
полями статуса без webhook URL и текста delivery error. При ошибке Telegram API
логируется `webhook_info_fetch_failed` с типом исключения.

`delete_webhook()` логирует `webhook_deleted` с флагом
`drop_pending_updates` и boolean результатом без bot token или webhook URL. При
ошибке Telegram API логируется `webhook_delete_failed` с типом исключения.

`perform_log_out()` логирует `bot_logged_out` с результатом успешного вызова;
при ошибке Telegram API логируется `bot_log_out_failed` с типом исключения.

`perform_close()` логирует `bot_closed` с результатом успешного вызова; при
ошибке Telegram API логируется `bot_close_failed` с типом исключения.

`perform_leave_chat()` логирует `leave_chat_succeeded` с `chat_id` и
результатом успешного вызова; при ошибке Telegram API логируется
`leave_chat_failed` с `chat_id` и типом исключения.

`perform_forward_message()` логирует `message_forwarded` с `chat_id`,
`from_chat_id`, `message_id`, флагом `protect_content` и id новой копии; при
ошибке Telegram API логируется `forward_message_failed` с типом исключения,
`from_chat_id` и `message_id`.

`perform_forward_messages()` логирует `messages_forwarded` с `chat_id`,
`from_chat_id`, `message_ids`, флагом `protect_content` и `forwarded_count`; при
ошибке Telegram API логируется `forward_messages_failed` с типом исключения,
`from_chat_id` и `message_ids`.

`perform_copy_message()` логирует `message_copied` с `chat_id`, `from_chat_id`,
`message_id`, флагом `protect_content` и id новой копии; при ошибке Telegram API
логируется `copy_message_failed` с типом исключения, `from_chat_id` и
`message_id`.

`perform_copy_messages()` логирует `messages_copied` с `chat_id`, `from_chat_id`,
`message_ids`, флагами `protect_content`, `remove_caption` и `copied_count`; при
ошибке Telegram API логируется `copy_messages_failed` с типом исключения,
`from_chat_id` и `message_ids`.

`perform_send_photo()` логирует `photo_sent` с `chat_id`, флагами `has_caption`,
`has_spoiler`, `protect_content` и id отправленного сообщения; при ошибке
Telegram API логируется `send_photo_failed` с типом исключения и `chat_id`. URL
или `file_id` фото в логи не попадают.

`perform_send_audio()` логирует `audio_sent` с `chat_id`, флагами `has_caption`,
`has_performer`, `has_title`, `protect_content` и id отправленного сообщения;
при ошибке Telegram API логируется `send_audio_failed` с типом исключения и
`chat_id`. URL или `file_id` аудио в логи не попадают.

`perform_send_live_photo()` логирует `live_photo_sent` с `chat_id`, флагами
`has_caption`, `has_spoiler`, `protect_content` и id отправленного сообщения;
при ошибке транспорта или ответе Telegram с `ok: false` логируется
`send_live_photo_failed` с типом исключения либо `error_code`/описанием и
`chat_id`. `file_id` live photo и обложки в логи не попадают.

`perform_send_document()` логирует `document_sent` с `chat_id`, флагами
`has_caption`, `has_thumbnail`, `disable_content_type_detection`,
`protect_content` и id отправленного сообщения; при ошибке Telegram API
логируется `send_document_failed` с типом исключения и `chat_id`. URL или
`file_id` документа в логи не попадают.

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
- форматирование `WebhookInfo`, вызов typed aiogram `get_webhook_info()`,
  обработку Telegram API ошибок и allowlist для `/webhook`;
- вызов typed aiogram `delete_webhook()`, `drop_pending_updates` parsing,
  обработку Telegram API ошибок, validation path и allowlist для
  `/deletewebhook`;
- вызов typed aiogram `log_out()`, обработку Telegram API ошибок, admin
  allowlist и требование подтверждения для `/logout`;
- вызов typed aiogram `close()`, обработку Telegram API ошибок (включая
  429/`TelegramRetryAfter`), admin allowlist и требование подтверждения для
  `/close`;
- вызов typed aiogram `leave_chat()`, обработку Telegram API ошибок
  (`TelegramBadRequest`/`TelegramForbiddenError`), строгий admin allowlist,
  парсинг `chat_id`, validation path и требование подтверждения для
  `/leavechat`;
- вызов typed aiogram `forward_message()`, обработку Telegram API ошибок
  (`TelegramBadRequest`/`TelegramForbiddenError`), admin allowlist, парсинг
  аргументов, `protect_content` по умолчанию и переключение через `share` для
  `/forward`;
- вызов typed aiogram `forward_messages()`, обработку Telegram API ошибок
  (`TelegramBadRequest`/`TelegramForbiddenError`), admin allowlist, парсинг
  списка message ids (нечисловые, нарушение строгого порядка, дубли, лимит
  1-100), `protect_content` по умолчанию, переключение через `share` и отчет о
  числе фактически пересланных сообщений для `/forwards`;
- вызов typed aiogram `copy_message()`, обработку Telegram API ошибок
  (`TelegramBadRequest`/`TelegramForbiddenError`), admin allowlist, парсинг
  аргументов, `protect_content` по умолчанию и переключение через `share` для
  `/copy`;
- вызов typed aiogram `copy_messages()`, обработку Telegram API ошибок
  (`TelegramBadRequest`/`TelegramForbiddenError`), admin allowlist, парсинг
  списка message ids (нечисловые, нарушение строгого порядка, дубли, лимит
  1-100), `protect_content` по умолчанию, переключение через `share`,
  `remove_caption` через `nocaption` и отчет о числе фактически скопированных
  сообщений для `/copies`;
- вызов typed aiogram `send_photo()`, обработку Telegram API ошибок
  (`TelegramBadRequest`/`TelegramForbiddenError`), admin allowlist, парсинг
  photo-аргумента и caption с пробелами, validation path для слишком длинного
  caption и отправку с caption и без него для `/photo`;
- вызов typed aiogram `send_audio()`, обработку Telegram API ошибок
  (`TelegramBadRequest`/`TelegramForbiddenError`), admin allowlist, парсинг
  audio-аргумента и caption с пробелами, validation path для слишком длинного
  caption и отправку с caption и без него для `/audio`;
- raw Bot API helper `send_live_photo()`: формирование payload и URL, ответ
  Telegram с `ok: false` (`SendLivePhotoError`), ошибку транспорта, admin
  allowlist, парсинг двух `file_id`-аргументов и caption с пробелами, validation
  path для слишком длинного caption и отправку с caption и без него для
  `/livephoto`;
- вызов typed aiogram `ban_chat_member()`, обработку Telegram API ошибок
  (`TelegramBadRequest`/`TelegramForbiddenError`), строгий admin allowlist,
  парсинг `chat_id`, `user_id`, `until_date_unix`, `revoke=true|false` и
  validation path для неверных аргументов `/banchatmember`;
- вызов typed aiogram `ban_chat_sender_chat()`, обработку Telegram API ошибок
  (`TelegramBadRequest`/`TelegramForbiddenError`), строгий admin allowlist,
  парсинг `chat_id`, `sender_chat_id` и validation path для неверных
  аргументов `/banchatsenderchat`;
- вызов typed aiogram `unban_chat_member()`, обработку Telegram API ошибок
  (`TelegramBadRequest`/`TelegramForbiddenError`), строгий admin allowlist,
  парсинг `chat_id`, `user_id`, `only_if_banned=true|false` и validation path
  для неверных аргументов `/unbanchatmember`;
- вызов typed aiogram `restrict_chat_member()`, обработку Telegram API ошибок
  (`TelegramBadRequest`/`TelegramForbiddenError`), строгий admin allowlist,
  парсинг `chat_id`, `user_id`, preset, `until_date_unix`,
  `independent=true|false` и validation path для неверных аргументов
  `/restrictchatmember`;
- вызов typed aiogram `set_chat_permissions()`, обработку Telegram API ошибок
  (`TelegramBadRequest`/`TelegramForbiddenError`), строгий admin allowlist,
  парсинг `chat_id`, preset (`closed`, `text`, `media`, `open`),
  `independent=true|false` и validation path для неверных аргументов
  `/setchatpermissions`;
- вызов typed aiogram `promote_chat_member()`, обработку Telegram API ошибок
  (`TelegramBadRequest`/`TelegramForbiddenError`), строгий admin allowlist,
  парсинг `chat_id`, `user_id`, preset (`moderator`, `manager`, `demote`) и
  validation path для неверных аргументов `/promotechatmember`;
- вызов typed aiogram `create_chat_invite_link()` или raw Bot API fallback для
  `createChatInviteLink`, обработку Telegram API ошибок, строгий admin
  allowlist, парсинг `chat_id`, `name`, `expire_date`, `member_limit`,
  `creates_join_request` и validation path для неверных аргументов
  `/createchatinvitelink`;
- вызов typed aiogram `approve_chat_join_request()` или raw Bot API fallback для
  `approveChatJoinRequest`, обработку Telegram API ошибок, строгий admin
  allowlist, парсинг `chat_id` и `user_id`, локальную validation path и raw
  Telegram error path для `/approvechatjoinrequest`;
- вызов typed aiogram `decline_chat_join_request()` или raw Bot API fallback для
  `declineChatJoinRequest`, обработку Telegram API ошибок, строгий admin
  allowlist, парсинг `chat_id` и `user_id`, локальную validation path и raw
  Telegram error path для `/declinechatjoinrequest`;
- вызов typed aiogram `send_document()`, обработку Telegram API ошибок
  (`TelegramBadRequest`/`TelegramForbiddenError`), admin allowlist, парсинг
  document-аргумента и caption с пробелами, validation path для слишком длинного
  caption и отправку с caption и без него для `/document`;
- извлечение текста из plain text и поведение на неизвестном MIME;
- rate limit middleware;
- Markdown/HTML форматирование, удаление mention и разбивку Telegram сообщений.

Integration tests описаны для живого proxy, но сейчас всегда skipped через
module-level `pytestmark`.

Локальная проверка на Python 3.14.4:

```text
python -m pytest -v
133 passed, 2 skipped
```

На более старых рантаймах (например, Python 3.12) дополнительно появляются
предупреждения о pydantic deprecated `__fields__` при использовании
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
11. Покрытие Telegram Bot API ограничено четырнадцатью методами; official Guest
    Mode, callback flows, rich outbound media, bot profile/commands management,
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
9. Добавить следующий слой Telegram API: `sendChatAction`, `setMyCommands`,
   `answerCallbackQuery`, полноценный `answerInlineQuery` и rich outbound media
   методы.
