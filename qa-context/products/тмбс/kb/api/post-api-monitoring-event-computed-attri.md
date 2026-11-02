# POST /api/monitoring-event/computed-attribute/script-generation — генерация скрипта события мониторинга на основании выч

> POST-метод администратора, который по вычисляемому атрибуту бизнес-сервиса генерирует и возвращает строкой SQL-код события мониторинга.

### Описание
- Наименование метода: Генерация скрипта события мониторинга на основании вычисляемого атрибута. Метод возвращает строку — сгенерированный SQL-код для события мониторинга. (2-POST _api_monitoring-event_computed-attribute_script-generation)
- История изменений: версия 1.0, автор @Kalinina D.А., 19 июн. 2026, «Создание страницы». (2-POST _api_monitoring-event_computed-attribute_script-generation)
- Оглавление документа: Описание метода, История изменений, Входные параметры, Пример запроса, Выходные параметры, Пример ответа, Логика работы. Раздел «Логика работы» во фрагменте содержит только хвост SQL из примера ответа (`metrics.object != monitoring_events.externalId and severity != 'NORMAL'` и `limit 1`). (2-POST _api_monitoring-event_computed-attribute_script-generation)

### Роли и права
- Роли: Администратор. Авторизация: JWT (token) пользователя. (2-POST _api_monitoring-event_computed-attribute_script-generation)

### API и интеграции
- URL: /api/monitoring-event/computed-attribute/script-generation; метод HTTP: POST. (2-POST _api_monitoring-event_computed-attribute_script-generation)
- Swagger: https://trmonbs-admin-service.ppmon.test.sfera-t1.ru/swagger-ui/index.html#/MonitoringEventController (2-POST _api_monitoring-event_computed-attribute_script-generation)
- http-статус в ответе: 200. Обрабатываемые ошибки: 400, 403, 409, 423, 500. (2-POST _api_monitoring-event_computed-attribute_script-generation)
- Выходные параметры: строка — сгенерированный SQL-код для события мониторинга. (2-POST _api_monitoring-event_computed-attribute_script-generation)

### Поля и элементы
- Тело запроса. Для каждого поля указан тип вычисляемого атрибута, к которому оно применимо.
- bsId — int32, идентификатор бизнес-сервиса; Все; обязательный «+»; пример 123.
- computedAttributeDto — object, вычисляемый атрибут; Все; обязательный «+». Вложенные поля:
  - id — int32, идентификатор; Все.
  - computedAttributeId — int32, сквозной идентификатор; Все.
  - name — string, имя; Все.
  - description — string, описание; Все.
  - status — string, статус; Все.
  - mcId — int64, ID карточки мониторинга; Все.
  - calculationMethod — string, методика расчета; Все.
  - groups — array<object>, список групп; Все: id (int32, идентификатор группы), value (string, значение группы).
  - type — string, тип (GENERAL, TIMED, COMPLETENESS, STRING); Все.
  - script — string, код вычисляемого атрибута; GENERAL, STRING.
  - unit — object, единица измерения: для TIMED — string, для GENERAL — object, для COMPLETENESS — object. Вложенные: id (int32; GENERAL, COMPLETENESS), value (string, название, например "COUNT"; GENERAL, COMPLETENESS, TIMED).
  - intervals — array<object>, интервалы критичности; GENERAL, COMPLETENESS, TIMED. Вложенные: id (int32; GENERAL, TIMED), active (boolean; GENERAL, TIMED), minValue (int64; GENERAL), maxValue (int64; GENERAL), value (int64, порог в секундах; TIMED), autogeneration (boolean, флаг автоматической генерации события; GENERAL, TIMED), notificationGroupName (string, название группы оповещения; GENERAL, TIMED), type (string: NORMAL, WARNING, CRITICAL; GENERAL, TIMED).
  - automaticEvent — object, автоматическое событие мониторинга (если есть); GENERAL, COMPLETENESS, TIMED. Содержит monitoringEvent: id (int32), monitoringCardRowId (int64, ID карточки мониторинга), name, description, type, status (string), tags (array<object>: code, name, description, type — string), uploadToZSM (boolean, флаг выгрузки в ЗСМ), eventScript (string, код события), alertedObjectUrlTemplate (string, шаблон ссылки на дашборд), calculationIntervalInMinutes (int32, частота выполнения в минутах); а также sendIntervalValue (int32, значение интервала повторной отправки) и sendIntervalUnit (string, интервал повторной отправки).
- В примере запроса есть поле transactionType = "TRANSACTIONAL", в таблице параметров не описано.
- Пример запроса: {"bsId":1073741824,"computedAttributeDto":{"id":1073741824,"computedAttributeId":1073741824,"name":"string","mcId":9007199254740991,"calculationMethod":"string","description":"string","status":"DRAFT","groups":[{"id":1073741824,"value":"string"}],"type":"GENERAL","transactionType":"TRANSACTIONAL","automaticEvent":{"monitoringEvent":{"id":1073741824,"monitoringCardRowId":9007199254740991,"name":"string","description":"string","type":"MANUAL","status":"DRAFT","tags":[{"code":"string","name":"string","description":"string","type":"COMPUTED_ATTRIBUTE"}],"uploadToZSM":true,"eventScript":"string","alertedObjectUrlTemplate":"string","calculationIntervalInMinutes":1073741824},"sendIntervalValue":1073741824,"sendIntervalUnit":"MINUTE"}}} (2-POST _api_monitoring-event_computed-attribute_script-generation)

### Сценарии
- Пример ответа (SQL): CTE `metrics` (case по metric_value > 0 → 'WARNING', иначе 'NORMAL' как severity; выборка из default.bs_6606_metric_distributed md где metric_id = 20363 и md.insert_timestamp > toDateTime(now(), 'Europe/Moscow') - toIntervalMinute(19)); CTE `monitoring_events` (externalId из default.bs_6606_monitoring_event_distributed me, где externalId != '' и insert_timestamp > now() - interval '7 DAY'); итоговый select: 'TRmonBS' as application, 'Бизнес-сервис' as category, severity, '6606' as ciName, 'Волков(базовый)' as serviceName, title/alertText '2099 Транзакционный мониторинг - Волков(базовый). Новая метрика1', metricName, metricValue, timeAlertCreated, metric_object as object, metric_object as originalData, insert_timestamp, metrics.object as externalId; from metrics left join monitoring_events on metrics.object = monitoring_events.externalId; where metrics.object != monitoring_events.externalId and severity != 'NORMAL'; limit 1. (2-POST _api_monitoring-event_computed-attribute_script-generation)

### Сообщения и ошибки
- Ошибки: 400, 403, 409, 423, 500; успешный ответ — 200. Расшифровка кодов не приведена. (2-POST _api_monitoring-event_computed-attribute_script-generation)

### Открытые вопросы
- Нет текстового описания алгоритма генерации в разделе «Логика работы». (2-POST _api_monitoring-event_computed-attribute_script-generation)
- Не описаны значения и смысл кодов 400, 403, 409, 423, 500. (2-POST _api_monitoring-event_computed-attribute_script-generation)
- transactionType есть в примере запроса, но отсутствует в таблице входных параметров. (2-POST _api_monitoring-event_computed-attribute_script-generation)
