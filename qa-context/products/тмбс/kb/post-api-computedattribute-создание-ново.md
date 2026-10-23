# POST /api/computedAttribute/ — создание нового вычисляемого атрибута

> POST /api/computedAttribute/ — метод создания нового вычисляемого атрибута (с привязкой к сервису) в карточке мониторинга ТМБС, доступный администратору по JWT.

### Описание
- URL: /api/computedAttribute/; метод HTTP: POST; наименование метода: Создание нового вычисляемого атрибута; способ авторизации: JWT (token) пользователя (POST _api_computedAttribute_-6)
- Swagger: https://trmonbs-admin-service.ppmon.dev.sfera-t1.ru/swagger-ui/index.html#/ComputedAttributeController/createComputedAttribute (POST _api_computedAttribute_-6)
- История изменений: версия 1.0, @Perekin D.С., 27 апр. 2026 — создание страницы; задача PPBP-1997 [SA] ТМБС. Отправка отклонений в сторонние системы. Версия 1.1, @Perekin D.С., 26 авг. 2026 — доработка контракта в рамках принадлежности выч. атрибута к сервису (изменения подсвечены зелёным); задача PPBP-2528 [Аналитика] ТМБС. Подготовка артефактов для 4 варианта реализации (POST _api_computedAttribute_-6)

### Роли и права
- Роли: Администратор; авторизация: JWT (token) пользователя (POST _api_computedAttribute_-6)

### API и интеграции
- Входные параметры (Request body): id (int32) — идентификатор выч. атрибута; name (string) — имя; mcId (int64) — ID карточки мониторинга (первичный ключ); calculationMethod (string) — методика расчёта; description (string) — описание; status (string) — статус; type (string) — тип; transactionType (string) — класс; unit (object): id (int32) идентификатор единицы измерения, value (string) значение единицы измерения (POST _api_computedAttribute_-6)
- groups (array<object>): id (int32) — идентификатор группы вычисляемого атрибута; value (string) — значение группы (POST _api_computedAttribute_-6)
- service (object): id (int4) — идентификатор сервиса (пример: 8488); name (string) — наименование сервиса (пример: Сервис платежей); code (string) — код сервиса (пример: CI3000162) (POST _api_computedAttribute_-6)
- startPoint (object): checkpointId (int32) — идентификатор контрольной точки; script (string) — код метрики (POST _api_computedAttribute_-6)
- valueCalculation (object): valueScript (string); checkpointIds (array<string>), items int32; intervals (array<object>); normalValueTimeoutInSeconds (int32) — таймаут ожидания состояния Normal в секундах (POST _api_computedAttribute_-6)
- intervals (array<object>), в valueCalculation и на верхнем уровне запроса: id (int32) — идентификатор интервала; active (boolean) — идентификатор состояния интервала; minValue (int64) — минимальное значение интервала; maxValue (int64) — максимальное значение интервала; type (string) — тип интервала критичности; sendDeviation (boolean) — признак отправки отклонений (значения в таблице: false, true) (POST _api_computedAttribute_-6)
- В таблице расположение всех параметров — Request body; в колонке «Пример» для одного параметра указано 1233 (id/mcId — по тексту однозначно не определяется); отметки обязательности («+»/«-») в извлечённом тексте разнесены с названиями параметров, сопоставить их нельзя (POST _api_computedAttribute_-6)
- Пример запроса: {"id":null,"name":"Новый вычисляемый атрибут12","groups":[],"mcId":1851,"unit":null,"description":"","calculationMethod":"","transactionType":"TRANSACTIONAL","type":"COMPLETENESS","status":"DRAFT","startPoint":{"script":"-- произведите замену переменных ${}\n select min(event_time) from data\n where event_stage in ('${payment_1}', '${payment_2}')"},"service":{"id":8488,"name":"Сервис платежей","code":"CI3000162"},"valueCalculation":{"valueScript":"-- произведите замену переменных ${}\n select count(1) from data\n where event_stage in ('${payment_3}')","checkpointIds":[],"intervals":[{"id":null,"type":"NORMAL","active":true,"minValue":1,"maxValue":2,"key":"moit5db0erkb4giq49b","sendDeviation":false},{"id":null,"type":"WARNING","active":false,"minValue":null,"maxValue":null,"key":"moit5db0ulj3iy4zr4k","sendDeviation":true},{"id":null,"type":"CRITICAL","active":false,"minValue":null,"maxValue":null,"key":"moit5db0budo4juv5cq","sendDeviation":true}]},"normalValueTimeoutInSeconds":10} (POST _api_computedAttribute_-6)
- Выходные параметры: computedAttributeId (int32) — сквозной идентификатор выч. атрибута; id (int32); name; mcId (int64) — ID карточки мониторинга; calculationMethod; description; status (string); groups (id int32, value string); type; transactionType; service (id, name, code); valueCalculation (valueScript, checkpointIds, intervals, normalValueTimeoutInSeconds — описания как во входных); intervals (id, active, minValue, maxValue, type, sendDeviation) (POST _api_computedAttribute_-6)
- Пример ответа: {"сomputedAttributeId":970,"id":2796,"computedAttributeId":970,"name":"Timeout","mcId":1851,"calculationMethod":"","description":"","status":"MONITORING","groups":[],"type":"TIMED","transactionType":"TRANSACTIONAL","unit":"MINUTES","service":{"id":8488,"name":"Сервис платежей","code":"CI3000162"},"intervals":[{"id":2662,"active":true,"value":181,"type":"WARNING","sendDeviation":true},{"id":2661,"active":false,"value":null,"type":"CRITICAL","sendDeviation":true}],"startPoint":{"checkpointId":4416,"script":"select min(event_time) from data"},"endPoint":{"checkpointId":null,"script":" select min(event_time) from data\r\n where event_stage in ('not existing')"}} (POST _api_computedAttribute_-6)

### Сообщения и ошибки
- Успешный ответ: http-статус 200; обработка ошибок: 400, 403, 409, 423, 500 (POST _api_computedAttribute_-6)

### Бизнес-правила и ограничения
- Скрипты в примере запроса содержат плейсхолдеры ${}; комментарий в скрипте: «-- произведите замену переменных ${}» (POST _api_computedAttribute_-6)
- В примере запроса: transactionType «TRANSACTIONAL», type «COMPLETENESS», status «DRAFT»; типы интервалов: NORMAL, WARNING, CRITICAL; в интервалах есть поле key; normalValueTimeoutInSeconds: 10 (POST _api_computedAttribute_-6)
- В примере ответа: status «MONITORING», type «TIMED», unit «MINUTES»; присутствуют startPoint и endPoint (checkpointId, script); интервалы содержат поле value (POST _api_computedAttribute_-6)

### Открытые вопросы
- В примере ответа поле computedAttributeId дублируется (первое написано с кириллической «с») (POST _api_computedAttribute_-6)
- Раздел «Логика работы» не содержит описания (только пример ответа); страница 9 пустая (POST _api_computedAttribute_-6)
- Пример ответа и таблица параметров расходятся: в примере есть unit строкой, endPoint, value в интервалах, которых нет в таблице выходных параметров (POST _api_computedAttribute_-6)
