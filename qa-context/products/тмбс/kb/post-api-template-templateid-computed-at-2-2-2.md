# POST /api/template/{templateId}/computed-attribute/update — получение параметров шаблона и сохранённых значений для вычи

> POST-метод API, возвращающий список параметров шаблона и сохранённые значения параметров для указанных вычисляемых атрибутов, созданных из этого шаблона.

### Описание
- Наименование метода: «Возвращает список параметров шаблона и сохранённые значения для указанных выч. атрибутов, созданных из этого шаблона». (POST _api_template_{templateId}_computed-attribute_get-params-8)
- URL: /api/template/{templateId}/computed-attribute/update; метод HTTP: POST; ссылка на swagger: TBD. (POST _api_template_{templateId}_computed-attribute_get-params-8)
- История изменений: версия 1.0, автор @Kalinina D.А., дата 02 июл. 2026, «Создание страницы», задача PPBP-2309 [SA] Аналитика по функционалу "Массовые операции над сущностями созданными из шаблона". (POST _api_template_{templateId}_computed-attribute_get-params-8)

### Бизнес-правила и ограничения
- Логика работы: 1) проверить, что шаблон в статусе ACTIVE; 2) загрузить параметры шаблона (template_parameters) по templateId; 3) для каждого Id: a) проверить, что сущность существует и имеет template_id = templateId; b) получить сохранённые параметры из таблицы applied_template_parameters; 4) сформировать ответ. (POST _api_template_{templateId}_computed-attribute_get-params-8)

### API и интеграции
- Авторизация: JWT (token) пользователя. (POST _api_template_{templateId}_computed-attribute_get-params-8)
- Обработка ошибок: 400, 403, 404, 500; http-статус кода в ответе: 200. (POST _api_template_{templateId}_computed-attribute_get-params-8)
- Входные параметры (значения по умолчанию не заданы): 1) templateId, int64, «Идентификатор шаблона», path, обязательный (+); 2) computedAttributeIds, array [int], «идентификаторы вычисляемых атрибутов», body, обязательный (+), пример: 101, 102, 103. В таблице также виден пример 1851 для templateId (по сохранившемуся фрагменту страницы 3). (POST _api_template_{templateId}_computed-attribute_get-params-8)
- Пример запроса (body): {"computedAttributeIds": [101, 102, 103]} (POST _api_template_{templateId}_computed-attribute_get-params-8)
- Выходные параметры (все обязательные, +): entities, array [object], «Список выч. атрибутов с параметрами»; entityRowId, int, «Идентификатор вычисляемого атрибута»; entityName, string, «Название вычисляемого атрибута»; monitoringCardRowId, int, «Идентификатор карточки мониторинга»; businessServiceId, int, «Идентификатор бизнес-сервиса»; syncTemplateParameters, array [object], «Параметры шаблона»; code, string, «Код параметра»; name, string, «Название параметра»; type, string, «Тип данных параметра»; value, string, «Значение параметра». (POST _api_template_{templateId}_computed-attribute_get-params-8)
- Пример ответа: {"entities":[{"entityRowId":101,"entityName":"Название вычисляемого атрибута","monitoringCardRowId":42,"businessServiceId":1234,"syncTemplateParameters":[{"code":"param1","name":"Параметр 1","type":"NUMBER","value":"11"}]},{"entityRowId":102,"entityName":"Другое название вычисляемого атрибута","monitoringCardRowId":43,"businessServiceId":3525,"syncTemplateParameters":[{"code":"param2","name":"Параметр 2","type":"NUMBER","value":"20"}]}]} (POST _api_template_{templateId}_computed-attribute_get-params-8)

### Сообщения и ошибки
- 400: «Ошибка в запросе»; 403: «Недостаточно прав»; 404: «Ресурс не найден». (POST _api_template_{templateId}_computed-attribute_get-params-8)
- Код 500 указан в обработке ошибок, текст сообщения не приведён. (POST _api_template_{templateId}_computed-attribute_get-params-8)

### Роли и права
- Роли: Администратор; авторизация: JWT (token) пользователя. (POST _api_template_{templateId}_computed-attribute_get-params-8)

### Открытые вопросы
- Имя файла содержит «get-params», а в поле URL указан путь, оканчивающийся на /update; соответствие не уточнено. (POST _api_template_{templateId}_computed-attribute_get-params-8)
- Ссылка на swagger: TBD; текст ошибки 500 не указан. (POST _api_template_{templateId}_computed-attribute_get-params-8)
