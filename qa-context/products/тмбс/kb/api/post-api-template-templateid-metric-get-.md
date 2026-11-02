# POST /api/template/{templateId}/metric/get-params — получение параметров шаблона и сохранённых значений для метрик, созд

> Метод POST /api/template/{templateId}/metric/get-params возвращает список параметров шаблона и сохранённые значения параметров для указанных метрик, созданных из этого шаблона.

### Описание
- Наименование метода: «Возвращает список параметров шаблона и сохранённые значения для указанных метрик, созданных из этого шаблона». (POST _api_template_{templateId}_metric_get-params-7)
- URL: /api/template/{templateId}/metric/get-params; метод HTTP: POST; способ авторизации: JWT (token) пользователя. (POST _api_template_{templateId}_metric_get-params-7)
- Ссылка на swagger: TBD. (POST _api_template_{templateId}_metric_get-params-7)
- История изменений: версия 1.0, автор @Kalinina D.А., дата 02 июл. 2026, описание «Создание страницы», задача PPBP-2309 [SA] Аналитика по функционалу "Массовые операции над сущностями созданными из шаблона". (POST _api_template_{templateId}_metric_get-params-7)

### Поля и элементы
- Входные параметры (все обязательные):
  1. templateId, int64, «Идентификатор шаблона», path, обязательный: +, по умолчанию: нет, пример: 1851.
  2. metricIds, array [int], «Идентификаторы метрик», body, обязательный: +, по умолчанию: нет, пример: 101, 102, 103. (POST _api_template_{templateId}_metric_get-params-7)
- Выходные параметры (все обязательные, «+»):
  1. entities, array [object], «Список метрик с параметрами».
  2. entityRowId, int, «Идентификатор метрики».
  3. entityName, string, «Название метрики».
  4. monitoringCardRowId, int, «Идентификатор карточки мониторинга».
  5. businessServiceId, int, «Идентификатор бизнес-сервиса».
  6. syncTemplateParameters, array [object], «Параметры метрики».
  7. code, string, «Код параметра».
  8. name, string, «Название параметра».
  9. type, string, «Тип данных параметра».
  10. value, string, «Значение параметра». (POST _api_template_{templateId}_metric_get-params-7)

### Бизнес-правила и ограничения
- Логика работы:
  1. Проверить, что шаблон в статусе ACTIVE.
  2. Загрузить параметры шаблона (template_parameters) по templateId.
  3. Для каждого Id: a. проверить, что сущность существует и имеет template_id = templateId; b. получить сохранённые параметры из таблицы applied_template_parameters.
  4. Сформировать ответ. (POST _api_template_{templateId}_metric_get-params-7)

### API и интеграции
- Пример запроса: {"metricIds": [101, 102, 103]} (POST _api_template_{templateId}_metric_get-params-7)
- Пример ответа (http-статус 200): {"entities":[{"entityRowId":101,"entityName":"Название вычисляемого атрибута","monitoringCardRowId":42,"businessServiceId":1234,"syncTemplateParameters":[{"code":"param1","name":"Параметр 1","type":"NUMBER","value":"11"}]},{"entityRowId":102,"entityName":"Другое название вычисляемого атрибута","monitoringCardRowId":43,"businessServiceId":12354,"syncTemplateParameters":[{"code":"param2","name":"Параметр 2","type":"NUMBER","value":"20"}]}]} (POST _api_template_{templateId}_metric_get-params-7)
- http-статус коды в ответе: 200. (POST _api_template_{templateId}_metric_get-params-7)

### Сообщения и ошибки
- Обработка ошибок: 400, 403, 404, 500. (POST _api_template_{templateId}_metric_get-params-7)
- 400: «Ошибка в запросе». 403: «Недостаточно прав». 404: «Ресурс не найден». Для 500 текст в документе не приведён. (POST _api_template_{templateId}_metric_get-params-7)

### Роли и права
- Роли: Администратор. Авторизация: JWT (token) пользователя. (POST _api_template_{templateId}_metric_get-params-7)

### Открытые вопросы
- Ссылка на swagger: TBD. (POST _api_template_{templateId}_metric_get-params-7)
- В примере ответа в поле entityName для метрик указаны значения «Название вычисляемого атрибута» и «Другое название вычисляемого атрибута». (POST _api_template_{templateId}_metric_get-params-7)
- Условия возврата 400, 403, 404 в логике работы не описаны. (POST _api_template_{templateId}_metric_get-params-7)
