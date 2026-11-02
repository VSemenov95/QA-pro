# POST /ext-api/v1/transactions-events — поиск событий в бизнес-сервисе по идентификаторам транзакций

> Внешний метод POST /ext-api/v1/transactions-events ТМБС синхронно возвращает события бизнес-сервиса по списку идентификаторов транзакций за период с фильтром по контрольным точкам и усечением ответа по размеру.

### Описание
- URL: /ext-api/v1/transactions-events; метод HTTP: POST; наименование: Поиск событий в бизнес-сервисе по идентификаторам транзакций за определенный период времени (29-POST _ext-api_v1_transactions-events)
- Авторизация: JWT (token) пользователя; запрос должен содержать JWT-токен с полем sub. Swagger: -. Ответ синхронный, http-статус в ответе: 200 ОК (29-POST _ext-api_v1_transactions-events)
- История изменений: версия 1.0, автор @Kalinina D.А., 15 мая 2026, «Создание страницы» (29-POST _ext-api_v1_transactions-events)

### Поля и элементы
- Входные параметры (все в body):
- apiBsCode — string, обязательный; ИД бизнес-сервиса, пример BS8; заполняется значением ciId (ИД КЕ сервиса/цепочки сервисов). Для БС платежей ЮЛ нет зарегистрированной КЕ, поэтому пока используется значение 8; где маппинг на КЕ есть — соответствующие ИД КЕ. Контракт: minLength 1, maxLength 255 (29-POST _ext-api_v1_transactions-events)
- transactionIds — array<string uuid>, обязательный; список идентификаторов транзакций; пример ["uuid1","uuid2"]; pattern элемента ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ (29-POST _ext-api_v1_transactions-events)
- eventTimeFrom — string, обязательный; фильтр >; формат YYYY-MM-DD (контракт: format date); пример 2026-05-15 (29-POST _ext-api_v1_transactions-events)
- eventStages — array<string>, необязательный; список КТ («Список имен контрольных точек»); пример ["p0_uasp_trmon_troc_transactions","p1_uasp_trmon_troc_transactions"]; minItems 1, maxItems 25000, элемент minLength 1, maxLength 255 (29-POST _ext-api_v1_transactions-events)
- Выходные параметры: data — array<object>, обязательный («Список полученных транзакций», maxItems 25000); data[].transactionId — string uuid, пример 09c5e44f-9aea-4079-97fa-89411beee001; data[].events — array<object>, maxItems 25000, каждое событие — StringMap (Map<String, String>, maxProperties 1000, значения string minLength 0, maxLength 2000); truncatedIds — array<string>, ИД транзакций, отброшенных при превышении размера ответа, maxItems 25000 (29-POST _ext-api_v1_transactions-events)
- Поля события в примере: uuid, eventStage, eventType, eventTime, emdStatus, dataResponseText. В контракте data, events и transactionId обязательны; additionalProperties: false (29-POST _ext-api_v1_transactions-events)
- Пример запроса: {"apiBsCode":"BS8","transactionIds":["09c5e44f-9aea-4079-97fa-89411beee001","af9bd94b-c9e7-4b12-a2af-7e3123836f70"],"eventTimeFrom":"2026-12-20","eventStages":["p0_uasp_trmon_troc_transactions","p1_uasp_trmon_troc_transactions"]} (29-POST _ext-api_v1_transactions-events)
- Пример ответа: {"data":[{"transactionId":"09c5e44f-9aea-4079-97fa-89411beee001","events":[{"uuid":"001","eventStage":"p0_uasp_trmon_troc_transactions","eventType":"stage","eventTime":"2026-12-21T09:15:30Z","emdStatus":"READING_REQUEST","dataResponseText":"Операция разрешена"}]}],"truncatedIds":["09c5e44f-9aea-4079-97fa-89411beee001","af9bd94b-c9e7-4b12-a2af-7e3123836f70"]} (29-POST _ext-api_v1_transactions-events)

### Бизнес-правила и ограничения
- Переменные окружения: CONFIG_INTEGRATION_REST_TRANSACTIONS_BATCH_MAX_SIZE = 100 (может быть выставлено любое число по итогам нагрузочного тестирования) — максимум транзакций в запросе; CONFIG_INTEGRATION_REST_RESPONSE_MAX_SIZE_IN_KB = 900 — максимальный размер ответа; CONFIG_INTEGRATION_REST_EVENT_RESPONSE_FIELDS_<bs_id> — маппинг имен колонок таблицы bs_{id}_event_distributed на названия полей ответа, пример: {"имя_колонки":"псевдоним","uuid":"transactionUuid","event_stage":"eventStage","event_type":"eventType","event_time":"eventTime","emd_status":"emdStatus","data_response_text":"dataResponseText"} (29-POST _ext-api_v1_transactions-events)
- В событие включаются только поля из белого списка (CONFIG_INTEGRATION_REST_EVENT_RESPONSE_FIELDS_<bs_id>); если полей не осталось, событие не добавляется в events (29-POST _ext-api_v1_transactions-events)
- Если событий не найдено — пустой массив data (29-POST _ext-api_v1_transactions-events)
- При превышении размера ответа сервис отбрасывает целые транзакции и добавляет их id в truncatedIds (29-POST _ext-api_v1_transactions-events)

### API и интеграции
- Таблица событий: bs_{bs_id}_event_distributed. Запрос: transaction_id IN (transactionIds) AND event_time > eventTimeFrom; если eventStages не пуст — дополнительно AND event_stage IN (eventStages) (29-POST _ext-api_v1_transactions-events)
- Контракт OpenAPI 3.0.1: title «2099.ppbp-transactionsEvents-s-rest-v1», description «API для поиска событий по списку транзакций», version 1.0.0; контакт: Абросимов Руслан Викторович (https://start.vtb.ru/service/phonebook/contact/70159327, rabrosimov@vtb.ru); tags ExternalApiController; summary «Получить список событий по транзакциям»; operationId getTransactionEvents (29-POST _ext-api_v1_transactions-events)
- Серверы: IFT — https://api.iftppbp.test.vtb.ru; PREPROD — https://api.app-ppbp.oslb-app01.test.vtb.ru; PROD — https://api.trmonbs.region.vtb.ru (29-POST _ext-api_v1_transactions-events)
- requestBody обязательный, application/json, ExternalApiTransactionEventsRequestDto: «Запрос на получение событий транзакций по бизнес-сервису, идентификаторам транзакций, временному фильтру и стадиям событий»; обязательные поля: apiBsCode, eventTimeFrom, transactionIds (29-POST _ext-api_v1_transactions-events)
- Ответы: 200 «Успешный ответ с данными транзакций и отброшенными идентификаторами» (ExternalApiTransactionEventsResponseDto); 400 «Некорректный запрос» (ServerErrorDto); 500 «Внутренняя ошибка сервиса» (ServerErrorDto) (29-POST _ext-api_v1_transactions-events)
- ServerErrorDto: errorCode — integer, «Внутренний код ошибки», minimum 1, maximum 99999; errorMessage — string, «Сообщение об ошибке сервиса», minLength 1, maxLength 10000 (29-POST _ext-api_v1_transactions-events)

### Сообщения и ошибки
- Лог (WARNING) при усечении: "Размер ответа превышает {CONFIG_INTEGRATION_REST_RESPONCE_MAX_SIZE_IN_KB} Кб, были отброшены следующие транзакции: af9bd94b-c9e7-4b12-a2af-7e3123836f70, 09c5e44f-9aea-4079-97fa-89411beee001" (29-POST _ext-api_v1_transactions-events)
- №1, 400 — Отсутствуют или неверны обязательные параметры. "errorMessage": "[externalApiTransactionSearchRequestDto.apiBsCode, apiBsCode]; arguments []; default message [apiBsCode]]; default message [must not be null]]" (29-POST _ext-api_v1_transactions-events)
- №2, 400 — Превышено максимальное количество transactionId в запросе. "errorMessage": "[externalApiTransactionSearchRequestDto.transactionIds,transactionIds]; arguments []; default message [transactionIds]]; default message [maximum size exceeded]]" (29-POST _ext-api_v1_transactions-events)
- №3, 400 — Неверный формат даты. "errorMessage": "[externalApiTransactionAttributesRequestDto.transactionDateFrom,transactionDateFrom]; arguments []; default message [transactionDateFrom]]; default message [invalid date format]]" (29-POST _ext-api_v1_transactions-events)
- №4, 400 — Неизвестный apiBsCode. "errorMessage": "[externalApiTransactionSearchRequestDto.apiBsCode, apiBsCode]; arguments []; default message [apiBsCode]]; default message [not found]]" (29-POST _ext-api_v1_transactions-events)
- №5, 500 — Найдено два или более бизнес-сервиса с одинаковым apiBsCode. "errorMessage": "Internal Server Error" (29-POST _ext-api_v1_transactions-events)

### Роли и права
- Роль: Внешний пользователь; JWT (token) пользователя с полем sub (29-POST _ext-api_v1_transactions-events)

### Сценарии
- 1) Система отправляет запрос к POST /ext-api/v1/transactions-events сервиса ТМБС с JWT-токеном с полем sub. 2) Валидация: нет apiBsCode, transactionIds или eventTimeFrom — ошибка №1; transactionIds менее 1 или более CONFIG_INTEGRATION_REST_TRANSACTIONS_BATCH_MAX_SIZE элементов — №2; формат eventTimeFrom неверный — №3. 3) apiBsCode не найден — №4. 4) Два или более БС с одинаковым apiBsCode — №5. 5) Запрос к bs_{bs_id}_event_distributed (условия выше); нет событий — пустой data; иначе события группируются по transactionId в объекты { transactionId, events }; для каждого события берутся только поля белого списка, пустые события не добавляются. 6) При превышении размера ответа — усечение целыми транзакциями, truncatedIds, лог WARNING. 7) Синхронный ответ 200 ОК (29-POST _ext-api_v1_transactions-events)

### Открытые вопросы
- Описание data: «Массив событий для инструкции» (29-POST _ext-api_v1_transactions-events)
- В примере ответа truncatedIds содержит id транзакции, которая одновременно присутствует в data (29-POST _ext-api_v1_transactions-events)
- Описание eventTimeFrom: «Время транзакции», в контракте — «Дата транзакции», формат YYYY-MM-DD (29-POST _ext-api_v1_transactions-events)

### Расхождения между документами
- Лимит transactionIds: в описании и сценарии от 1 до 100 (CONFIG_INTEGRATION_REST_TRANSACTIONS_BATCH_MAX_SIZE), в контракте maxItems 25000
- Имя переменной размера ответа: CONFIG_INTEGRATION_REST_RESPONSE_MAX_SIZE_IN_KB и CONFIG_INTEGRATION_REST_RESPONCE_MAX_SIZE_IN_KB
- В примерах ошибок №1–№4 DTO externalApiTransactionSearchRequestDto / externalApiTransactionAttributesRequestDto и поле transactionDateFrom, а в контракте ExternalApiTransactionEventsRequestDto и eventTimeFrom
- Пример eventTimeFrom: в примере запроса 2026-12-20, в таблице параметров 2026-05-15
