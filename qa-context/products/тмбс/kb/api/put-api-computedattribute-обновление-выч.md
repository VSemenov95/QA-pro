# PUT /api/computedAttribute/ — обновление вычисляемого атрибута

> Метод PUT /api/computedAttribute/ обновляет вычисляемый атрибут карточки мониторинга ТМБС (с привязкой к сервису), принимает его полное описание в теле запроса и возвращает обновлённый атрибут.

### Описание
- Наименование метода: «Обновление вычисляемого атрибута»; URL: /api/computedAttribute/; метод HTTP: PUT (PUT _api_computedAttribute_-4)
- Swagger: https://trmonbs-admin-service.ppmon.dev.sfera-t1.ru/swagger-ui/index.html#/ComputedAttributeController/updateComputedAttribute (PUT _api_computedAttribute_-4)
- Оглавление документа: Описание метода, История изменений, Входные параметры, Пример запроса, Выходные параметры, Пример ответа, Логика работы (PUT _api_computedAttribute_-4)
- История изменений: версия 1.0, @Perekin D.С., 27 апр. 2026 — создание страницы, задача PPBP-1997 [SA] ТМБС. Отправка отклонений в сторонние системы; версия 1.1, @Perekin D.С., 26 авг. 2026 — доработка контракта в рамках принадлежности выч. атрибута к сервису (изменения подсвечены зелёным цветом), задача PPBP-2528 [Аналитика] ТМБС. Подготовка артефактов для 4 варианта реализации (PUT _api_computedAttribute_-4)

### Поля и элементы
- Входные параметры (все в Request body): computedAttributeId (int32) — сквозной идентификатор выч. атрибута; id (int32) — идентификатор выч. атрибута; name (string) — имя; mcId (int64) — ID карточки мониторинга (первичный ключ); calculationMethod (string) — методика расчёта; description (string) — описание; status (string) — статус; type (string) — тип; transactionType (string) — класс; sendDeviation (boolean) — признак отправки отклонений; normalValueTimeoutInSeconds (int32) — таймаут ожидания состояния Normal в секундах (PUT _api_computedAttribute_-4)
- groups (array<object>): id (int32) — идентификатор группы вычисляемого атрибута; value (string) — значение группы (PUT _api_computedAttribute_-4)
- unit (object) — единицы измерения: id (int32), value (string) (PUT _api_computedAttribute_-4)
- service (object): id (int4) — идентификатор сервиса; name (string) — наименование; code (string) — код (PUT _api_computedAttribute_-4)
- startPoint (object): checkpointId (int32) — идентификатор контрольной точки; script (string) — код метрики (PUT _api_computedAttribute_-4)
- valueCalculation (object): valueScript (string); checkpointIds (array<string>), Items int32; intervals (array<object>) (PUT _api_computedAttribute_-4)
- intervals (array<object>), также на верхнем уровне: id (int32) — идентификатор интервала; active (boolean) — идентификатор состояния интервала; minValue (int64) — минимальное значение; maxValue (int64) — максимальное значение; type (string) — тип интервала критичности; sendDeviation (boolean) — признак отправки отклонений (PUT _api_computedAttribute_-4)
- Примеры значений: у одного из первых полей «1233»; service.id «8488», service.name «Сервис платежей», service.code «CI3000162»; у sendDeviation колонки «false true» (PUT _api_computedAttribute_-4)
- Колонки «Обязательный», «Значение по умолчанию», «Пример» заполнены «+»/«-», сопоставить с полями достоверно нельзя (PUT _api_computedAttribute_-4)
- Выходные параметры: computedAttributeId (int32) — сквозной идентификатор; id (int32); name (string); mcId (int64) — ID карточки мониторинга; calculationMethod (string); description (string); status (string) — без описания; groups (array<object>) с id (int32) и value (string); type (string); transactionType (string); service (object: id int4, name, code); valueCalculation (object: valueScript, checkpointIds array<string>, Items int32); intervals (array<object>: id, active, minValue, maxValue, type, sendDeviation — описания как во входных); normalValueTimeoutInSeconds (int32); intervals указан в таблице повторно. Значения service в примере: id 8488, name «Сервис платежей», code «CI3000162» (PUT _api_computedAttribute_-4)

### Бизнес-правила и ограничения
- В примере запроса скрипты содержат переменные ${}; комментарий скрипта: «-- произведите замену переменных ${}» (PUT _api_computedAttribute_-4)
- В примере запроса интервалы NORMAL, WARNING, CRITICAL содержат поле key; у NORMAL sendDeviation false, у WARNING и CRITICAL — true (PUT _api_computedAttribute_-4)
- Раздел «Логика работы» (стр. 8) содержит только JSON, текстового описания логики нет (PUT _api_computedAttribute_-4)

### API и интеграции
- Авторизация: JWT (token) пользователя; HTTP-статус в ответе: 200; обработка ошибок: 400, 403, 409, 423, 500 (PUT _api_computedAttribute_-4)
- Пример запроса: {"id":null,"name":"Новый вычисляемый атрибут12","groups":[],"mcId":1851,"unit":null,"description":"","calculationMethod":"","transactionType":"TRANSACTIONAL","type":"COMPLETENESS","status":"DRAFT","startPoint":{"script":"-- произведите замену переменных ${}\n select min(event_time) from data\n where event_stage in ('${payment_1}', '${payment_2}')"},"service":{"id":8488,"name":"Сервис платежей","code":"CI3000162"},"valueCalculation":{"valueScript":"-- произведите замену переменных ${}\n select count(1) from data\n where event_stage in ('${payment_3}')","checkpointIds":[],"intervals":[{"id":null,"type":"NORMAL","active":true,"minValue":1,"maxValue":2,"key":"moit5db0erkb4giq49b","sendDeviation":false},{"id":null,"type":"WARNING","active":false,"minValue":null,"maxValue":null,"key":"moit5db0ulj3iy4zr4k","sendDeviation":true},{"id":null,"type":"CRITICAL","active":false,"minValue":null,"maxValue":null,"key":"moit5db0budo4juv5cq","sendDeviation":true}]},"normalValueTimeoutInSeconds":10} (PUT _api_computedAttribute_-4)
- Пример ответа: {"сomputedAttributeId":970,"id":2796,"computedAttributeId":970,"name":"Timeout","mcId":1851,"calculationMethod":"","description":"","status":"MONITORING","groups":[],"type":"TIMED","transactionType":"TRANSACTIONAL","unit":"MINUTES","service":{"id":8488,"name":"Сервис платежей","code":"CI3000162"},"intervals":[{"id":2662,"active":true,"value":181,"type":"WARNING","sendDeviation":true},{"id":2661,"active":false,"value":null,"type":"CRITICAL","sendDeviation":true}],"startPoint":{"checkpointId":4416,"script":"select min(event_time) from data"},"endPoint":{"checkpointId":null,"script":" select min(event_time) from data\r\n where event_stage in ('not existing')"}} (PUT _api_computedAttribute_-4)

### Роли и права
- Роль: Администратор; авторизация: JWT (token) пользователя (PUT _api_computedAttribute_-4)

### Открытые вопросы
- Пример запроса содержит id: null и status: DRAFT, хотя метод обновляющий; в документе не поясняется (PUT _api_computedAttribute_-4)
- Пример ответа содержит поля (endPoint, value в интервалах, unit строкой, дублирующий ключ «сomputedAttributeId»), отсутствующие в таблице выходных параметров, и не содержит valueCalculation и normalValueTimeoutInSeconds из таблицы (PUT _api_computedAttribute_-4)
- Сопоставление признаков обязательности, значений по умолчанию и примеров с полями не читается (PUT _api_computedAttribute_-4)
