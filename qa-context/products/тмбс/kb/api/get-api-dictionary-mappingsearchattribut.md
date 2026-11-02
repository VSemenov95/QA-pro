# GET /api/dictionary/mappingSearchAttributes/ — получение списка атрибутов поиска для маппинга на технические атрибуты

> GET-метод справочника, возвращающий администратору список атрибутов поиска (code, name, type) для маппинга на технические атрибуты КТ, данные берутся из переменной окружения ppbp-admin-service.

### Описание
- URL: /api/dictionary/mappingSearchAttributes/; метод HTTP: GET; наименование: Получение списка атрибутов поиска для маппинга на технические атрибуты (3-GET _api_dictionary_mappingSearchAttributes_)
- Способ авторизации: JWT (token) пользователя; ссылка на swagger: - (3-GET _api_dictionary_mappingSearchAttributes_)
- http-статус коды в ответе: 200 (3-GET _api_dictionary_mappingSearchAttributes_)
- История изменений: версия 1.0, автор @Perekin D.С., 26 мая 2026, «Создание страницы», задача PPBP-1958 [Аналитика] ТМБС. Реализовать механизм маппинга полей запроса на атрибуты КТ (3-GET _api_dictionary_mappingSearchAttributes_)
- Оглавление страницы: Описание метода, История изменений, Входные параметры, Пример запроса, Выходные параметры, Пример ответа, Логика работы (3-GET _api_dictionary_mappingSearchAttributes_)

### Поля и элементы
- Входной параметр authorization: string, «JWT (token) пользователя», расположение header, обязательный (+), значение по умолчанию - (3-GET _api_dictionary_mappingSearchAttributes_)
- Выходной параметр data: array<object>, обязательный (+), значение по умолчанию - (3-GET _api_dictionary_mappingSearchAttributes_)
- code: string, «Код атрибута поиска», пример ClientextId (3-GET _api_dictionary_mappingSearchAttributes_)
- name: string, «Текстовое значение атрибута поиска», пример «Идентификатор организации в ДБО» (3-GET _api_dictionary_mappingSearchAttributes_)
- В примере ответа у каждого элемента есть поле type (в таблице выходных параметров не описано): значения "string" и "DATE" (3-GET _api_dictionary_mappingSearchAttributes_)

### Бизнес-правила и ограничения
- Логика работы: 1. Получить запрос; 2. Взять необходимые данные из переменной окружения ppbp-admin-service - CONFIG_INTEGRATION_REST_SEARCH_ATTRIBUTES_LIST; 3. Сформировать DTO и отправить (3-GET _api_dictionary_mappingSearchAttributes_)

### API и интеграции
- Пример запроса (URL): 'https://trmonbs-admin-service.ppmon.dev.sfera-t1.ru/api/dictionary/searchMappingAttributes/ (в примере слова searchMappingAttributes вместо mappingSearchAttributes) (3-GET _api_dictionary_mappingSearchAttributes_)
- Источник данных: переменная окружения сервиса ppbp-admin-service CONFIG_INTEGRATION_REST_SEARCH_ATTRIBUTES_LIST (3-GET _api_dictionary_mappingSearchAttributes_)
- Пример ответа (code — name — type): ClientextId — «Идентификатор организации в ДБО» — string; transactionId — «Идентификатор транзакции/инструкции» — string; instructionId — «Идентификатор инструкции» — string; accountLast4 — «Последние 4 цифры счета» — string; amount — «Сумма платежа» — string; documentNumber — «Номер платежного документа» — string; mdm — «MDM-код» — string; id_rs — «Идентификатор РС счета» — string; payDate — «Дата Платежа» — DATE (3-GET _api_dictionary_mappingSearchAttributes_)

### Сообщения и ошибки
- Успешный ответ: http-статус 200 (3-GET _api_dictionary_mappingSearchAttributes_)
- Обработка ошибок: 400, 403, 404, 409, 423, 500 (3-GET _api_dictionary_mappingSearchAttributes_)

### Роли и права
- Роли: Администратор (3-GET _api_dictionary_mappingSearchAttributes_)

### Открытые вопросы
- В примере запроса путь /api/dictionary/searchMappingAttributes/, а в описании метода /api/dictionary/mappingSearchAttributes/ (3-GET _api_dictionary_mappingSearchAttributes_)
- Поле type есть в примере ответа, но отсутствует в таблице выходных параметров (3-GET _api_dictionary_mappingSearchAttributes_)
- Тело примера запроса не приведено, кроме URL (3-GET _api_dictionary_mappingSearchAttributes_)
