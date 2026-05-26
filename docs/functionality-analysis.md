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
`sendPoll`, `sendContact`, `sendDice`, `sendChecklist`, `sendChatAction`,
`sendMessageDraft`, `getUserProfilePhotos`, `setMessageReaction`,
`setUserEmojiStatus`, `getUserProfileAudios`, `banChatMember`,
`unbanChatMember`, `restrictChatMember`, `promoteChatMember`,
`approveChatJoinRequest`, `createChatInviteLink`, `editChatInviteLink`,
`setChatPhoto`, `deleteChatPhoto`, `pinChatMessage`, `unpinChatMessage` и
`unpinAllChatMessages` остается 127 пока не
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
| `sendVoice` | `bot/services/send_voice.py`, `/voice` в `bot/handlers/commands.py` | Admin-flow отправки голосового сообщения в текущий чат как проигрываемого аудиоклипа (в виде waveform) по URL или `file_id`, а не только текстовой интерпретации. |
| `sendPaidMedia` | `bot/services/send_paid_media.py`, `/paidmedia` в `bot/handlers/commands.py` | Admin-flow отправки платного фото в текущий чат, доступ к которому пользователи оплачивают Telegram Stars, по URL или `file_id`, через изолированный raw Bot API helper, так как pinned `aiogram==3.3.0` не имеет typed wrapper для этого метода Bot API 7.6. |
| `sendLocation` | `bot/services/send_location.py`, `/location` в `bot/handlers/commands.py` | Admin-flow отправки точки на карте в текущий чат как настоящей Telegram-локации по широте и долготе, через typed aiogram API; у локаций нет caption, координаты валидируются по диапазонам и не пишутся в structured logs. |
| `sendMediaGroup` | `bot/services/send_media_group.py`, `/mediagroup` в `bot/handlers/commands.py` | Admin-flow отправки 2-10 медиа в текущий чат как единого альбома (media group) по URL или `file_id`, через typed aiogram API; все элементы одного типа (photo/video/document/audio), единый caption применяется к первому элементу. |
| `sendVenue` | `bot/services/send_venue.py`, `/venue` в `bot/handlers/commands.py` | Admin-flow отправки заведения (venue) — именованного места с названием и адресом, закрепленного на карте — в текущий чат по широте, долготе, title и address, через typed aiogram API; координаты валидируются по диапазонам, а сами координаты, title и address не пишутся в structured logs. |
| `sendPoll` | `bot/services/send_poll.py`, `/poll` в `bot/handlers/commands.py` | Admin-flow отправки нативного опроса (poll) — интерактивного вопроса с 2-10 вариантами ответа — в текущий чат, через typed aiogram API; длины вопроса (до 300) и вариантов (до 100) и их количество валидируются до обращения к Telegram, а сам вопрос и варианты ответа не пишутся в structured logs. |
| `sendContact` | `bot/services/send_contact.py`, `/contact` в `bot/handlers/commands.py` | Admin-flow отправки телефонного контакта (contact) — имени с номером телефона, который получатель может сохранить в адресную книгу — в текущий чат, через typed aiogram API; phone_number и first_name обязательны, last_name опционален, а номер телефона и имя контакта не пишутся в structured logs. |
| `sendDice` | `bot/services/send_dice.py`, `/dice` в `bot/handlers/commands.py` | Admin-flow отправки анимированной кости (dice) — анимированного эмодзи со случайным значением, которое выбирает Telegram — в текущий чат, через typed aiogram API; опциональный emoji ограничен набором 🎲/🎯/🏀/⚽/🎳/🎰 и валидируется до обращения к Telegram, без аргумента отправляется 🎲. |
| `sendChecklist` | `bot/services/send_checklist.py`, `/checklist` в `bot/handlers/commands.py` | Admin-flow отправки чеклиста (checklist) — озаглавленного списка из 1-30 задач — в текущий чат от имени подключенного business account, через изолированный raw Bot API helper, так как pinned `aiogram==3.3.0` не имеет typed wrapper для этого метода Bot API 9.1; требует `business_connection_id`, длины title (до 255) и задач (до 100) и их количество валидируются до обращения к Telegram, а title и тексты задач не пишутся в structured logs. |
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
| `pinChatMessage` | `bot/services/pin_chat_message.py`, `/pinchatmessage` в `bot/handlers/commands.py` | Admin-flow закрепления сообщения в группе, супергруппе или канале по `chat_id`, `message_id` и optional notification flag (`silent`, `loud`), через typed aiogram API `Bot.pin_chat_message`; команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS` без fallback и deny-by-default при пустом списке, бот должен быть администратором целевого чата с `can_pin_messages` в группах/супергруппах или `can_edit_messages` в каналах; специальных update types не требуется, так как сценарий запускается обычной командой из admin-чата, rollback выполняется ручным откреплением или `/unpinchatmessage`, а ошибки Telegram по правам, неизвестному чату или сообщению возвращаются оператору. |
| `unpinChatMessage` | `bot/services/unpin_chat_message.py`, `/unpinchatmessage` в `bot/handlers/commands.py` | Admin-flow открепления конкретного или последнего закрепленного сообщения в группе, супергруппе или канале по `chat_id` и optional `message_id`, через typed aiogram API `Bot.unpin_chat_message`; команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS` без fallback и deny-by-default при пустом списке, бот должен быть администратором целевого чата с `can_pin_messages` в группах/супергруппах или `can_edit_messages` в каналах; специальных update types не требуется, так как сценарий запускается обычной командой из admin-чата, rollback выполняется ручным повторным закреплением, а ошибки Telegram по правам, неизвестному чату или незакрепленному сообщению возвращаются оператору. |
| `unpinAllChatMessages` | `bot/services/unpin_all_chat_messages.py`, `/unpinallchatmessages` в `bot/handlers/commands.py` | Admin-flow массового открепления всех закрепленных сообщений в группе, супергруппе или канале по `chat_id`, через typed aiogram API `Bot.unpin_all_chat_messages`; команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS` без fallback и deny-by-default при пустом списке, бот должен быть администратором целевого чата с `can_pin_messages` в группах/супергруппах или `can_edit_messages` в каналах; специальных update types не требуется, так как сценарий запускается обычной командой из admin-чата, rollback выполняется ручным повторным закреплением нужных сообщений, а ошибки Telegram по правам или неизвестному чату возвращаются оператору. |
| `promoteChatMember` | `bot/services/promote_chat_member.py`, `/promotechatmember` в `bot/handlers/commands.py` | Admin-flow повышения или понижения пользователя в группе, супергруппе или канале по `chat_id`, `user_id` и preset (`moderator`, `manager`, `demote`), через typed aiogram API; команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS` без fallback и deny-by-default при пустом списке, бот должен быть администратором целевого чата с правом `can_promote_members` и может выдавать только свои права; ошибки Telegram возвращаются оператору. |
| `getChatMemberCount` | `bot/services/get_chat_member_count.py`, `/getchatmembercount` в `bot/handlers/commands.py` | Admin-flow получения количества участников группы, супергруппы или канала по `chat_id`, через typed aiogram API `Bot.get_chat_member_count`; команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS` без fallback и deny-by-default при пустом списке, бот должен иметь доступ к целевому чату, обычно быть его участником; специальных update types не требуется, так как сценарий запускается обычной командой из admin-чата, а ошибки Telegram по неизвестному чату, отсутствующему доступу или rate limit возвращаются оператору. |
| `getChatAdministrators` | `bot/services/get_chat_administrators.py`, `/getchatadministrators` в `bot/handlers/commands.py` | Admin-flow аудита администраторов группы, супергруппы или канала по `chat_id`, через typed aiogram API `Bot.get_chat_administrators`; команда закрыта строгим `TELEGRAM_ADMIN_CHAT_IDS` без fallback и deny-by-default при пустом списке, бот должен иметь доступ к целевому чату и может требовать administrator status в зависимости от типа чата и privacy settings; ответ выводит количество администраторов, user id, display name, username, status, custom title, anonymity flag и включенные admin rights, специальных update types не требуется, так как сценарий запускается обычной командой из admin-чата, а ошибки Telegram по неизвестному чату, отсутствующему доступу, недостаточным правам или rate limit возвращаются оператору. |
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

1. Lifecycle и диагностика: явная настройка `allowed_updates`,
   диагностика конфликтов между webhook и long polling.
2. Профиль и команды бота: `setMyCommands`, `deleteMyCommands`,
   `getMyCommands`, `setMyName`, `getMyName`, `setMyDescription`,
   `getMyDescription`, `setMyShortDescription`, `getMyShortDescription`,
   `setMyProfilePhoto`, `removeMyProfilePhoto`, `setChatMenuButton`,
   `getChatMenuButton`, `setMyDefaultAdministratorRights`,
   `getMyDefaultAdministratorRights`.
3. Более богатые ответы пользователю: `sendChatAction`,
   `sendChecklist`,
   `sendMessageDraft`, `setMessageReaction` (все четыре уже интегрированы).
4. Управление сообщениями: `editMessageCaption`, `editMessageMedia`,
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
   `setChatPermissions`, `exportChatInviteLink`, `createChatInviteLink`,
   `editChatInviteLink`, остальные invite-link методы, join-request методы,
   `pinChatMessage`, `unpinAllChatMessages`, forum-topic методы и
   `leaveChat`.
7. Пользовательский контекст Telegram: `getUserProfilePhotos` (уже интегрирован),
   `setUserEmojiStatus` (уже интегрирован), `getUserProfileAudios`,
   `getUserChatBoosts`, `getUserPersonalChatMessages`.
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
  получить список моделей из proxy;
- `/model <model_id>` сохраняет выбранную модель в in-memory настройках
  пользователя;
- `/settings` показывает текущую модель, streaming flag, guest mode и лимит
  запросов;
- `/webhook` показывает диагностику Telegram webhook для разрешенных
  admin/ops чатов;
- `/deletewebhook [drop_pending_updates=true|false]` удаляет Telegram webhook
  для разрешенных admin/ops чатов перед переходом на polling или local Bot API;
- `/logout` выполняет защищенный выход бота из cloud Bot API сервера для
  admin-чатов и требует явного подтверждения `/logout confirm`;
- `/close` выполняет защищенное закрытие bot instance на текущем Bot API
  сервере для admin-чатов и требует явного подтверждения `/close confirm`;
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
- `/clear` очищает историю разговора для пары `(chat_id, user_id)`.

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
- `TELEGRAM_ADMIN_CHAT_IDS`;
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
`/videonote`, `/animation`, `/voice`, `/paidmedia`, `/location`, `/venue`,
`/poll`, `/contact`, `/dice`, `/chataction`, `/messagedraft` и `/checklist`
fallback не применяется: команды требуют непустой `TELEGRAM_ADMIN_CHAT_IDS`,
иначе они отключены. Автоматический `typing…`-индикатор (управляемый
`TELEGRAM_CHAT_ACTION_ENABLED`) и draft-стриминг (управляемый
`TELEGRAM_MESSAGE_DRAFT_ENABLED`) admin-прав не требуют и работают для обычных
пользователей в уже разрешенных чатах.

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
   `answerCallbackQuery`, полноценный `answerInlineQuery`, `answerGuestQuery`
   и rich outbound media методы.
