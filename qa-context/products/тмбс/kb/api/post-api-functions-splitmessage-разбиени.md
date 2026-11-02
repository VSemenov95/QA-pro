# POST /api/functions/splitMessage — разбиение исходного сообщения события

> Метод POST /api/functions/splitMessage разбивает исходное сообщение события по массиву, заданному путём splitPath, с обогащением (WITH_ENRICHMENT) или без него (WITHOUT_ENRICHMENT).

### Описание
- URL: /api/functions/splitMessage; метод HTTP: POST; наименование: «Разбиение исходного сообщения события» (POST _api_functions_splitMessage -3)
- Способ авторизации: JWT (token) пользователя (POST _api_functions_splitMessage -3)
- Ссылка на swagger: https://trmonbs-admin-service.ppmon.dev.sfera-t1.ru/swagger-ui/index.html#/FunctionsController/splitMessage (POST _api_functions_splitMessage -3)
- История изменений: версия 1.0, автор @Perekin D.С., 29 янв. 2026, «Создание страницы», задача PPBP-1629 [Analytics][SA] Доработки конструктора создания технических атрибутов в источники данных (POST _api_functions_splitMessage -3)
- Оглавление: Описание метода, История изменений, Входные параметры, Пример запроса, Выходные параметры, Пример ответа, Коды ответа, Логика работы (POST _api_functions_splitMessage -3)
- Обработка ошибок: 400, 401, 403, 500; http-статус коды в ответе: 200 (POST _api_functions_splitMessage -3)

### Бизнес-правила и ограничения
- splitType принимает значения WITH_ENRICHMENT, WITHOUT_ENRICHMENT (указаны в колонке «Значение по умолчанию»; какое из них по умолчанию, однозначно не следует) (POST _api_functions_splitMessage -3)
- WITHOUT_ENRICHMENT: из массива arr вида [{"k":"v1"},{"k":"v2"},{"k":"v3"}] возвращается список из трёх строк: "{\n \"k\" : \"v1\"\n}", "{\n \"k\" : \"v2\"\n}", "{\n \"k\" : \"v3\"\n}" (POST _api_functions_splitMessage -3)
- WITH_ENRICHMENT: каждый элемент ответа — полное исходное сообщение, в котором массив arr содержит только один соответствующий элемент (v1, v2 или v3); поля в примере ответа: createDate, qrcodeid, action, status, amount, status_base_localizedname, last_modify_date, payer_name, payer_account, receiver_name, receiver_account, transactionUuid, arr (POST _api_functions_splitMessage -3)
- Раздел «Логика работы» присутствует, но пуст (POST _api_functions_splitMessage -3)

### API и интеграции
**Входные параметры**
- authorization — string, «JWT (token) пользователя», header, обязательный (+), по умолчанию (-)
- message — string, «Пример события, который нужно сплитовать», body, обязательный (+), по умолчанию (-)
- splitType — string, «Тип обработки массива данных», body, обязательный (+), значения: WITH_ENRICHMENT, WITHOUT_ENRICHMENT
- splitPath — string, «Путь к массиву», body, обязательный (+), по умолчанию (-)
(POST _api_functions_splitMessage -3)

**Пример запроса**
- body: message (JSON-событие в виде экранированной строки с полями created_date "28-08-2023 01:11:57.419148", qrcodeid "5415b462-caeb-4f97-8e32-6822dbd9eaba", action "PREPARATION", status "PROCESSING", amount "6d0399a5-cc66-4701-b821-c179968f6a09", status_base_localizedname "Запрос проведения платежа", last_modify_date, payer_name "PAYER", payer_account, receiver_name "RECEIVER", receiver_account, paymentid, status_check_dostupnost "WAITING", timestamp_check_dostupnost, status_check_block "WAITING", timestamp_check_block, transactionUuid "fcc3def9-6b00-4fe9-9a96-3c4f26eb8707" и "arr": [{"key":"1"},{"key":"2"},{"key":"3"}]), splitType "WITH_ENRICHMENT", splitPath "arr" (POST _api_functions_splitMessage -3)
- Для WITHOUT_ENRICHMENT пример массива: "arr": [{"k": "v1"},{"k": "v2"},{"k": "v3"}] (POST _api_functions_splitMessage -3)

**Выходные параметры**
- content — object, «Полученный объект данных, в рамках которого выполнялся сплит массива», обязательность и значение по умолчанию не заданы (-); пример: ["{\n \"k\" : \"v1\"\n}", "{\n \"k\" : \"v2\"\n}", "{\n \"k\" : \"v3\"\n}"] (POST _api_functions_splitMessage -3)

### Сообщения и ошибки
- 200 / ОК / «Операция выполнена успешно» / Разьединение (сплит) массива успешно выполнен (POST _api_functions_splitMessage -3)
- 400 / BadRequest / «Ошибка в синтаксисе запроса (не передан обязательный входной параметр / неверно задано значение входного параметра)» / Ошибка формата запроса (POST _api_functions_splitMessage -3)
- 403 / Forbidden / «Нет прав для доступа к данным метода» / Доступ запрещен (согласно ролевой модели) (POST _api_functions_splitMessage -3)
- 500 / — / «Сервис временно недоступен» / Внутренняя ошибка сервера (POST _api_functions_splitMessage -3)
- В таблице также есть строки «409 Conflict» и «423 Locked», а рядом со строкой 500 текст «Доступ запрещен (согласно ролевой модели)»; из-за разрыва таблицы сообщения и сценарии не восстановить (POST _api_functions_splitMessage -3)
- Код 401 указан в «Обработке ошибок», но отдельной строки в таблице кодов нет (POST _api_functions_splitMessage -3)

### Роли и права
- JWT (token) пользователя передаётся в header authorization; поле «Роли*» присутствует, но не заполнено; при отсутствии прав по ролевой модели — 403 Forbidden (POST _api_functions_splitMessage -3)

### Открытые вопросы
- Не заполнены поле «Роли» и раздел «Логика работы» (POST _api_functions_splitMessage -3)
- Неясно, какое значение splitType по умолчанию (POST _api_functions_splitMessage -3)
- Неясны сообщения и сценарии для 409 Conflict и 423 Locked и строка для 401 (POST _api_functions_splitMessage -3)
