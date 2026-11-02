# POST /api/monitoring-event/{eventId}/upload-to-zsm-state — изменение признака выгрузки события мониторинга в ЗСМ

> Метод POST /api/monitoring-event/{eventId}/upload-to-zsm-state изменяет признак выгрузки события мониторинга в ЗСМ (флаг uploadToZSM) и возвращает данные события со связанными объектами.

### Описание
- URL: /api/monitoring-event/{eventId}/upload-to-zsm-state; метод HTTP: POST (2-POST _api_monitoring-event_{eventId}_upload-to-zsm-state)
- Ссылка на swagger: https://trmonbs-admin-service.ppmon.test.sfera-t1.ru/swagger-ui/index.html#/MonitoringEventController (2-POST _api_monitoring-event_{eventId}_upload-to-zsm-state)
- История изменений: версия 1.0, автор @Kalinina D.А., 19 июн. 2026, «Создание страницы»; номер задачи не указан (2-POST _api_monitoring-event_{eventId}_upload-to-zsm-state)
- Оглавление страницы: Описание метода, История изменений, Входные параметры, Пример запроса, Выходные параметры, Пример ответа, Логика работы (2-POST _api_monitoring-event_{eventId}_upload-to-zsm-state)

### Поля и элементы
- Входные параметры (значений по умолчанию нет): authorization — string, JWT (token) пользователя, header, обязательный (+); eventId — int32, идентификатор события мониторинга, path, обязательный (+), пример: 123; uploadToZSM — boolean, флаг выгрузки события в ЗСМ (true/false), body, обязательный (+), пример: true (2-POST _api_monitoring-event_{eventId}_upload-to-zsm-state)
- Выходные параметры (+ обязательный, - необязательный): status — string, статус события мониторинга (+); monitoringEvent — object, основная информация о событии (+); linkedMetric — object, связанная метрика (если есть) (-); linkedComputedAttribute — object, связанный вычисляемый атрибут (если есть) (-); notificationGroup — string, название группы оповещений (-) (2-POST _api_monitoring-event_{eventId}_upload-to-zsm-state)
- monitoringEvent: id — int32, идентификатор события (+); monitoringCardRowId — int64, ID карточки мониторинга (+); name — string, название события (+); description — string, описание (-); type — string, тип события (MANUAL или AUTO) (+); status — string, статус события (+); tags — array<object>, список тегов (-); uploadToZSM — boolean, признак выгрузки события в ЗСМ (+); eventScript — string, SQL-код события мониторинга (-); alertedObjectUrlTemplate — string, шаблон ссылки на дашборд (-); calculationIntervalInMinutes — int32, частота выполнения запроса в минутах (+) (2-POST _api_monitoring-event_{eventId}_upload-to-zsm-state)
- tags: code — string, код тега; name — string, название тега; description — string, описание тега; type — string, тип тега (например, MONITORING_EVENT) (2-POST _api_monitoring-event_{eventId}_upload-to-zsm-state)
- linkedMetric: id — int32, идентификатор метрики; metricId — int32, сквозной идентификатор метрики; name — string, имя метрики; description — string, описание метрики; status — string, статус метрики; exportToKafka — boolean, признак экспорта во внешнюю систему (2-POST _api_monitoring-event_{eventId}_upload-to-zsm-state)
- linkedComputedAttribute: id — int32, идентификатор вычисляемого атрибута; metricId — int32, сквозной идентификатор вычисляемого атрибута; name — string, имя вычисляемого атрибута; description — string, описание вычисляемого атрибута (2-POST _api_monitoring-event_{eventId}_upload-to-zsm-state)
- Обязательность отдельных полей внутри tags, linkedMetric и linkedComputedAttribute в извлечённом тексте таблицы читается неоднозначно (2-POST _api_monitoring-event_{eventId}_upload-to-zsm-state)

### API и интеграции
- Способ авторизации: JWT (token) пользователя (2-POST _api_monitoring-event_{eventId}_upload-to-zsm-state)
- http-статус коды в ответе: 200; обработка ошибок: 400, 403, 409, 423, 500 (2-POST _api_monitoring-event_{eventId}_upload-to-zsm-state)
- Пример запроса (body): {"uploadToZSM": true} (2-POST _api_monitoring-event_{eventId}_upload-to-zsm-state)
- Пример ответа: {"status":"DRAFT","monitoringEvent":{"id":1073741824,"monitoringCardRowId":9007199254740991,"name":"string","description":"string","type":"MANUAL","status":"DRAFT","tags":[{"code":"string","name":"string","description":"string","type":"COMPUTED_ATTRIBUTE"}],"uploadToZSM":true,"eventScript":"string","alertedObjectUrlTemplate":"string","calculationIntervalInMinutes":1073741824},"linkedMetric":{"id":1073741824,"metricId":1073741824,"name":"string","description":"string","status":"DRAFT","exportToKafka":true},"linkedComputedAttribute":{"id":1073741824,"metricId":1073741824,"name":"string","description":"string"},"notificationGroup":"string"} (2-POST _api_monitoring-event_{eventId}_upload-to-zsm-state)
- В примере ответа linkedMetric, linkedComputedAttribute и notificationGroup показаны на верхнем уровне ответа, а в таблице выходных параметров linkedMetric и linkedComputedAttribute следуют за полями monitoringEvent (2-POST _api_monitoring-event_{eventId}_upload-to-zsm-state)

### Сообщения и ошибки
- Обрабатываемые ошибки: 400, 403, 409, 423, 500; тексты сообщений в документе не приведены (2-POST _api_monitoring-event_{eventId}_upload-to-zsm-state)

### Роли и права
- Роли: Администратор (2-POST _api_monitoring-event_{eventId}_upload-to-zsm-state)

### Открытые вопросы
- Раздел «Логика работы» не заполнен (2-POST _api_monitoring-event_{eventId}_upload-to-zsm-state)
- Наименование метода в документе указано как «Создание нового события мониторинга» (в тексте документа «мининторинга»); оно не соответствует назначению URL (upload-to-zsm-state) и параметру uploadToZSM, в документе это не поясняется (2-POST _api_monitoring-event_{eventId}_upload-to-zsm-state)
