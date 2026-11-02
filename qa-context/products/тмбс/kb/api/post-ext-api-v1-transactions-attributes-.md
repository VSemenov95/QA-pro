# POST /ext-api/v1/transactions-attributes — поиск вычисляемых атрибутов в бизнес-сервисе по идентификаторам транзакций

> Внешний REST-метод POST /ext-api/v1/transactions-attributes возвращает вычисляемые атрибуты бизнес-сервиса по списку идентификаторов транзакций за период с усечением ответа по размеру.

### Описание
- URL: /ext-api/v1/transactions-attributes; метод HTTP: POST; наименование: Поиск вычисляемых атрибутов в бизнес-сервисе по идентификаторам транзакций за определенный период времени; авторизация: JWT (token) пользователя; ссылка на swagger: -; http-статус коды в ответе: 200 (POST _ext-api_v1_transactions-attributes-40)
- История изменений: версия 1.0, автор @Kalinina D.А., 15 мая 2026, «Создание страницы» (номер задачи не указан) (POST _ext-api_v1_transactions-attributes-40)

### Роли и права
- Роли: Внешний пользователь. Запрос должен содержать JWT-токен с полем sub (POST _ext-api_v1_transactions-attributes-40)

### Поля и элементы
- Входные (все в body, обязательные, без значений по умолчанию): apiBsCode (string) — идентификатор бизнес-сервиса, пример 8, заполняется значением ciId (ИД КЕ сервиса/цепочки сервисов); т.к. для БС платежей ЮЛ нет зарегистрированной КЕ, пока используется значение 8; где маппинг на КЕ есть — соответствующие ИД КЕ (POST _ext-api_v1_transactions-attributes-40)
- transactionIds (array<string uuid>) — список идентификаторов транзакций, от 1 до 100, пример ["uuid1","uuid2"] (POST _ext-api_v1_transactions-attributes-40)
- transactionDateFrom (string) — дата транзакции (фильтр >), формат YYYY-MM-DD, пример 2026-05-15 (POST _ext-api_v1_transactions-attributes-40)
- Пример запроса: {"apiBsCode":"BS8","transactionIds":["09c5e44f-9aea-4079-97fa-89411beee001","af9bd94b-c9e7-4b12-a2af-7e3123836f70"],"transactionDateFrom":"2026-12-20"} (POST _ext-api_v1_transactions-attributes-40)
- Выходные: data (array<object>, обязательный) — данные по запрошенным транзакциям: transactionId (string uuid, пример 09c5e44f-9aea-4079-97fa-89411beee001); attributes (array<object>): name (string, пример amount), value (string, строковое значение, пример 3000) (POST _ext-api_v1_transactions-attributes-40)
- truncatedIds (array<string>) — идентификаторы транзакций, отброшенные при превышении размера ответа, пример ["uuid1","uuid2"] (POST _ext-api_v1_transactions-attributes-40)
- Пример ответа: data с двумя транзакциями. 09c5e44f-…001: «Уникальный идентификатор инструкции»: 5412ac0a7bd047b68bb4c3fa8143f0c9; «Время начала платежа»: 2026-04-10 11:15:40; «МДМ»: 1129054142; «Организация в ДБО»: 200052023; «ИНН плательщика»: 7700121232; «Система-источник»: DBO; «ИС»: 2212 Расчетные операции ЮЛ инструкция; «Тип платежной инструкции»: Рублевое платежное поручение; «Номер платежного документа»: 54516; «Номер счета плательщика»: 4070281072******0009; «ИД счета плательщика»: 87ab5d70-192d-4c9c-976d-9ef10bec52c8; «Сумма платежа»: 14884.64; «Тип получателя»: Outbound; «Номер счета получателя»: 0322464345******7300; «ИД счета зачисления»: 87ab5d70-192d-4c9c-976d-9ef10bec52c8; «Последний статус»: REJECTED; «Причина отклонения»: Отказ в выполнении продуктовой операции из-за наличия неоплаченной картотеки. af9bd94b-…f70: «Сумма платежа»: 3000.00; «Последний статус»: SUCCESS; «Номер платежного документа»: 1789 (POST _ext-api_v1_transactions-attributes-40)

### Бизнес-правила и ограничения
- Переменные окружения: CONFIG_INTEGRATION_REST_TRANSACTIONS_BATCH_MAX_SIZE = 100 (может быть выставлено любое число по итогам нагрузочного тестирования) — макс. число транзакций в запросе; CONFIG_INTEGRATION_REST_RESPONSE_MAX_SIZE_IN_KB = 900 — макс. размер ответа; CONFIG_INTEGRATION_REST_ATTRIBUTE_RESPONSE_FIELDS_<bs_id> — список имён возвращаемых атрибутов, пример: "Уникальный идентификатор инструкции", "Время начала платежа" (POST _ext-api_v1_transactions-attributes-40)
- Выборка из таблицы bs_{bs_id}_attribute_distributed; условие: transaction_uuid IN (transactionIds) AND transaction_time > transactionDateFrom (POST _ext-api_v1_transactions-attributes-40)
- Строковые значения — в колонке transaction_attribute_value_string, не строковые — в transaction_attribute_value (POST _ext-api_v1_transactions-attributes-40)
- В таблице несколько исторических записей по транзакции и атрибуту; решить через final или сложный запрос (самые поздние по insert_time) (POST _ext-api_v1_transactions-attributes-40)
- Только атрибуты из белого списка (env CONFIG_INTEGRATION_REST_ATTRIBUTE_RESPONSE_FIELDS_<bs_id>); имена конвертируются в attribute_id (POST _ext-api_v1_transactions-attributes-40)
- Группировка по transactionId; для каждой группы массив attributes: { "name": "<код_атрибута>", "value": "<строковое_значение>" } (POST _ext-api_v1_transactions-attributes-40)
- 0 найденных записей — пустой массив data (POST _ext-api_v1_transactions-attributes-40)
- При превышении размера ответа отбрасываются целые транзакции, их id добавляются в truncatedIds, лог WARNING. Текст лога: "Размер ответа превышает {CONFIG_INTEGRATION_REST_RESPONCE_MAX_SIZE_IN_KB} Кб, были отброшены следующие транзакции: af9bd94b-c9e7-4b12-a2af-7e3123836f70, 09c5e44f-9aea-4079-97fa-89411beee001" (POST _ext-api_v1_transactions-attributes-40)
- Ответ синхронный, 200 ОК (POST _ext-api_v1_transactions-attributes-40)

### Сценарии
- 1) Система отправляет POST-запрос в ТМБС (JWT с sub). 2) ТМБС валидирует: нет apiBsCode, transactionIds или transactionDateFrom — ошибка № 1; transactionIds меньше 1 или больше CONFIG_INTEGRATION_REST_TRANSACTIONS_BATCH_MAX_SIZE — № 2; неверный формат transactionDateFrom — № 3; [opt] apiBsCode не найден — № 4; [opt] два и более БС с одинаковым apiBsCode — № 6. 3) Обращение к bs_{bs_id}_attribute_distributed. 4) 0 записей — пустой data, иначе группировка по transactionId. 5) Для каждого атрибута отбор по белому списку; не найден ни один id атрибута из списка — № 5. 6) [opt] превышение размера — усечение, truncatedIds, WARNING. 7) Синхронно 200 ОК (POST _ext-api_v1_transactions-attributes-40)

### Сообщения и ошибки
- № 1, 400: Отсутствуют или неверны обязательные параметры; errorMessage вида "[externalApiTran… apiBsCode,apiBsC… message [apiBsCo… not be null]]" (default message [must not be null]; текст обрезан) (POST _ext-api_v1_transactions-attributes-40)
- № 2, 400: Превышено максимальное количество transactionId в запросе; errorMessage содержит transactionIds и default message [maximum size exceeded] (частично обрезан) (POST _ext-api_v1_transactions-attributes-40)
- № 3, 400: Неверный формат даты; errorMessage содержит transactionDateFrom и default message [invalid date format] (частично обрезан) (POST _ext-api_v1_transactions-attributes-40)
- № 4, 400: Неизвестный apiBsCode; errorMessage содержит apiBsCode и default message [not found] (частично обрезан) (POST _ext-api_v1_transactions-attributes-40)
- № 5, 400: Не найден id атрибута из списка CONFIG_INTEGRATION_REST_ATTRIBUTE_RESPONSE_FIELDS_<bs_id>; errorMessage содержит attributes,code и [not found] (частично обрезан) (POST _ext-api_v1_transactions-attributes-40)
- № 6, 500: Найдено два или более бизнес-сервиса с одинаковым apiBsCode; "errorMessage": "Internal Server Error" (POST _ext-api_v1_transactions-attributes-40)
- В примерах встречаются DTO externalApiTransactionSearchRequestDto и ExternalApiTransactionAttributesRequestDto (POST _ext-api_v1_transactions-attributes-40)

### API и интеграции
- Контракт OpenAPI 3.0.1: title 2099.ppbp-transactionsAttributes-s-rest-v1; description «API получение вычисляемых атрибутов транзакций по бизнес-сервису»; version 1.0.0. Серверы: IFT https://api.iftppbp.test.vtb.ru; PREPROD https://api.app-ppbp.oslb-app01.test.vtb.ru; PROD https://api.trmonbs.region.vtb.ru (POST _ext-api_v1_transactions-attributes-40)
- Путь post, тег ExternalApiController, summary «Получить список атрибутов по транзакциям», operationId getTransactionAttributes; requestBody required application/json ExternalApiTransactionAttributesRequestDto. Ответы: 200 «Успешный ответ с данными транзакций и отброшенными идентификаторами» (ExternalApiTransactionAttributesResponseDto); 400 «Некорректный запрос» и 500 «Внутренния ошибка сервиса» (ServerErrorDto) (POST _ext-api_v1_transactions-attributes-40)
- ServerErrorDto: errorCode integer 1–99999 «Внутренний код ошибки»; errorMessage string, minLength 1, maxLength 10000 «Сообщение об ошибке сервиса»; additionalProperties false (POST _ext-api_v1_transactions-attributes-40)
- Request DTO (required: apiBsCode, transactionIds, transactionDateFrom): apiBsCode string 1–255 «Идентификатор бизнес-сервиса (код)»; transactionIds array minItems 1, items pattern ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ «Список идентификаторов транзакций»; transactionDateFrom string format date «Дата транзакции (фильтр >), формат YYYY-MM-DD»; additionalProperties false (POST _ext-api_v1_transactions-attributes-40)
- Response DTO: data array (items ExternalApiTransactionAttributesDto), maxItems 25000; truncatedIds array maxItems 25000, items с тем же uuid pattern; additionalProperties false. AttributesDto: transactionId (uuid pattern), attributes maxItems 25000 (ExternalApiTransactionAttributeValueDto). ValueDto (required name, value): name string 0–255 «Наименование вычисляемого атрибута»; value string 0–2000 «Строковое значение атрибута» (POST _ext-api_v1_transactions-attributes-40)

### Открытые вопросы
- Номер задачи в истории изменений не указан; ссылка на swagger отсутствует (POST _ext-api_v1_transactions-attributes-40)
- В примере запроса apiBsCode = "BS8", в комментарии к параметру — 8 (POST _ext-api_v1_transactions-attributes-40)
- В примере ответа truncatedIds содержит те же идентификаторы, что и data (POST _ext-api_v1_transactions-attributes-40)

### Расхождения между документами
- Максимум transactionIds: описание и бизнес-логика — от 1 до 100 (BATCH_MAX_SIZE), контракт — maxItems 25000
- Имя переменной размера ответа: RESPONSE_MAX_SIZE_IN_KB и RESPONCE_MAX_SIZE_IN_KB
