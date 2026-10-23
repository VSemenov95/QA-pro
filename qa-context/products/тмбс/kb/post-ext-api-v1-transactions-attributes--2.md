# POST /ext-api/v1/transactions-attributes — приём событий мониторинга от ТМБС для обработки в ЗСМ

> Метод POST /ext-api/v1/transactions-attributes принимает события мониторинга от ТМБС (микросервис trmon-ecm-integration-service) для дальнейшей обработки в ЗСМ.

### Описание
- URL: /ext-api/v1/transactions-attributes; метод HTTP: POST; наименование: Приём событий мониторинга от ТМБС для дальнейшей обработки в ЗСМ; способ авторизации: JWT (token) пользователя; ссылка на swagger: -; обработка ошибок: http-статус коды в ответе 200. ([Интеграция ТМБС-ЗСМ]  POST _listener-tbpm-s-rest-v1_alert-3)
- История изменений: версия 1.0, автор @Kalinina D.А., 15 мая 2026, «Создание страницы», номер задачи не указан. ([Интеграция ТМБС-ЗСМ]  POST _listener-tbpm-s-rest-v1_alert-3)
- Оглавление документа: Описание метода, История изменений, Входные параметры, Пример запроса, Выходные параметры, Переменные окружения (ТМБС), влияющие на отправку, Ход сценария, Ошибки, Контракт. ([Интеграция ТМБС-ЗСМ]  POST _listener-tbpm-s-rest-v1_alert-3)

### Поля и элементы
- Входные параметры (все в body, значение по умолчанию «-»; + = обязательный):
  - title (string) — Заголовок. Обязательный (+). Пример: "Количество операций всего превысило порог > 5 со значением 6".
  - application (string) — Источник: приложение или агент, который получил метрику. Пример: "TRmonBS".
  - category (string) — Категория уровня мониторинга. Пример: "Бизнес-сервис".
  - alertText (string) — Описание события. Пример: "Время ожидания события между системами ИС1 и ИС2 достигло критического значения 10 минут".
  - externalId (string) — id, который присваивает система источник. Пример: "12345".
  - severity (string) — Уровень критичности. Одно из значений: Critical, Warning, Normal. Обязательный (+). Пример: "Critical".
  - ciName (string) — Имя объекта мониторинга, на которое оказывается влияние. Примеры: «ИС/Бизнес-сервис. Пример» / "Сервис авторизации" (в документе примеры вынесены отдельным столбцом, порядок соответствия не вполне однозначен).
  - ciType (string) — Тип объект мониторинга. Пример: "Бизнес-сервис".
  - metricName (string) — Имя метрики. Пример: "Имя метрики из каталога метрик".
  - metricValue (string) — Значение метрики. Пример: "27".
  - timeCreated (string) — Время создания события в источнике. Обязательный (+). Пример в документе: "12019-11-14T00:55:31.820Z".
  - metricKey (string) — Ключ экземпляра метрики. Пример: "ping_packet_loss_percent".
  - alertId (string) — id события, пришедшего от системы источника. Пример: "metric1".
  - originalData (object (JSON)) — Исходная информация (сюда положить весь объект по событию).
  - additionalAttributes (object (JSON)) — Массив из атрибутов, которые не нашли сопоставления в стандарте событий.
  - customAttributes (object (JSON)) — Пользовательские атрибуты, специфичные для интеграции.
    - ppbpNotificationGroup (string) — соответствует полю «Группа оповещений» на FE. Если не указана, присылать атрибут ppbpNotificationGroup с пустой строкой.
  Остальные поля необязательные. ([Интеграция ТМБС-ЗСМ]  POST _listener-tbpm-s-rest-v1_alert-3)
- Пример запроса: {"title":"string","application":"string","category":"string","alertText":"string","externalId":"string","severity":"string","ciName":"string","ciType":"string","metricName":"string","metricValue":"string","timeCreated":"2026-03-04T14:08:59.623Z","metricKey":"string","alertId":"string","originalData":{},"additionalAttributes":{},"customAttributes":{"ppbpNotificationGroup":"string"}} ([Интеграция ТМБС-ЗСМ]  POST _listener-tbpm-s-rest-v1_alert-3)

### Бизнес-правила и ограничения
- Обязательные поля (в контракте TbpmEventDto, required): severity, timeCreated, title. ([Интеграция ТМБС-ЗСМ]  POST _listener-tbpm-s-rest-v1_alert-3)
- severity: Critical, Warning, Normal. ([Интеграция ТМБС-ЗСМ]  POST _listener-tbpm-s-rest-v1_alert-3)
- Если «Группа оповещений» не указана, в customAttributes присылается ppbpNotificationGroup с пустой строкой. ([Интеграция ТМБС-ЗСМ]  POST _listener-tbpm-s-rest-v1_alert-3)
- При успешном ответе (200) событие считается отправленным. ([Интеграция ТМБС-ЗСМ]  POST _listener-tbpm-s-rest-v1_alert-3)

### API и интеграции
- Выходные параметры: 200 — Успешный ответ. ([Интеграция ТМБС-ЗСМ]  POST _listener-tbpm-s-rest-v1_alert-3)
- Переменные окружения (ТМБС): tm.monitoringevent.ecm.switch.useCoreService = true (переключатель формата и адреса отправки); tm.monitoringevent.ecm.services.alert.host = <base_url>/listener-tbpm-s-rest-v1/alert (полный URL эндпоинта ЗСМ); TM_MONITORINGEVENT_APPLICATIONNAME = TRmonBS (имя приложения-источника); TM_MONITORINGEVENT_KEYGENERATION_SOURCECOLUMNS (порядок полей для генерации metricKey). ([Интеграция ТМБС-ЗСМ]  POST _listener-tbpm-s-rest-v1_alert-3)
- Контракт OpenAPI 3.0.1: title «Core Event Listener API», description «API для приёма событий мониторинга от различных систем», version 1.0.0; путь /listener-tbpm-s-rest-v1/alert, post; tags: Alert Events Listener; summary: «Приём событий от ТМБС (транзакционный мониторинг)»; operationId: processTbpmEvents; requestBody required: true, application/json, схема TbpmEventDto. Ответы: '200' — «Событие успешно принято»; '400' — «Ошибка валидации запроса»; '429' — «Слишком много запросов». TbpmEventDto (object): required severity, timeCreated, title; string: title, application, category, alertText, externalId, severity, ciName, ciType, metricName, metricValue, metricKey, alertId; timeCreated — string, format date-time; originalData, additionalAttributes, customAttributes — ссылки на схему JsonNode (type: object). ([Интеграция ТМБС-ЗСМ]  POST _listener-tbpm-s-rest-v1_alert-3)

### Сообщения и ошибки
- Ошибка №1: код 400 — Ошибка валидации (неверный формат, отсутствие обязательных полей); пример текста: -. ([Интеграция ТМБС-ЗСМ]  POST _listener-tbpm-s-rest-v1_alert-3)
- Ошибка №2: код 429 — Слишком много запросов (превышена частота); пример текста: -. ([Интеграция ТМБС-ЗСМ]  POST _listener-tbpm-s-rest-v1_alert-3)

### Роли и права
- Роль: Администратор ТМБС. Авторизация: JWT (token) пользователя, заголовок Authorization: Bearer <token>. ([Интеграция ТМБС-ЗСМ]  POST _listener-tbpm-s-rest-v1_alert-3)

### Сценарии
- 1) Сервис формирует событие мониторинга на основе метрики или вычисляемого атрибута (SQL-запрос из конфигурации метрики). 2) Микросервис trmon-ecm-integration-service: a) проверяет флаг tm.monitoringevent.ecm.switch.useCoreService = true; b) берёт целевой URL из tm.monitoringevent.ecm.services.alert.host; c) формирует JSON по TbpmEventDto: title — строка из SQL; application — из env TM_MONITORINGEVENT_APPLICATIONNAME; timeCreated — поле timeAlertCreated из SQL; metricKey — SHA256-хеш от полей из TM_MONITORINGEVENT_KEYGENERATION_SOURCECOLUMNS; customAttributes — включает ppbpNotificationGroup из конфигурации карточки мониторинга (если не задан — пустая строка); d) отправляет POST с заголовком Authorization: Bearer <token>. 3) При ответе 200 событие считается отправленным. ([Интеграция ТМБС-ЗСМ]  POST _listener-tbpm-s-rest-v1_alert-3)

### Открытые вопросы
- Ссылка на swagger не указана («-»); номер задачи в истории изменений не указан. ([Интеграция ТМБС-ЗСМ]  POST _listener-tbpm-s-rest-v1_alert-3)

### Расхождения между документами
- Путь в описании метода (/ext-api/v1/transactions-attributes) и в контракте (/listener-tbpm-s-rest-v1/alert) различаются; в документе не объясняется.
- Описание и название документа расходятся с существующим разделом базы знаний с тем же URL (поиск вычисляемых атрибутов по идентификаторам транзакций).
