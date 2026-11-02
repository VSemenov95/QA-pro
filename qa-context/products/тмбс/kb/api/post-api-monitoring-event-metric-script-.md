# POST /api/monitoring-event/metric/script-generation — генерация скрипта события мониторинга на основании метрики

> Метод POST /api/monitoring-event/metric/script-generation генерирует SQL-код события мониторинга на основании переданной метрики бизнес-сервиса и возвращает его строкой.

### Описание
- Наименование метода: «Генерация скрипта события мониторинга на основании метрики». Метод генерирует SQL-код события мониторинга на основании метрики. (2-POST _api_monitoring-event_metric_script-generation)
- Версия документа 1.0, автор @Kalinina D.А., 19 июн. 2026, описание изменений: «Создание страницы». (2-POST _api_monitoring-event_metric_script-generation)
- Оглавление страницы: Описание метода, История изменений, Входные параметры, Пример запроса, Выходные параметры, Пример ответа, Логика работы. Раздел «Логика работы» содержит только окончание примера SQL (from metrics left join monitoring_events ... limit 1); текстового описания логики нет. (2-POST _api_monitoring-event_metric_script-generation)

### Поля и элементы
Входные параметры:
- `bsId` — int32, идентификатор бизнес-сервиса, обязательный (+), пример 123. (2-POST _api_monitoring-event_metric_script-generation)
- `metricDto` — object, Метрика, обязательный (+). Значений по умолчанию нет. (2-POST _api_monitoring-event_metric_script-generation)
  - `id` int32 — идентификатор метрики; `metricId` int32 — сквозной идентификатор метрики; `name` string — имя; `description` string — описание; `status` string — статус; `exportToKafka` boolean — признак экспорта во внешнюю систему; `mcId` int64 — ID карточки мониторинга; `calculationMethod` string — методика расчета; `script` string — код метрики; `calculationPeriod` int32 — период расчёта метрики в минутах.
  - `metricSchedule` object — расписание расчёта: `type` string (MINUTE, HOUR, DAY, WEEK, MONTH); `timeHour` int32 — час (для HOUR/DAY/WEEK/MONTH); `timeMinute` int32 — минута; `weekDay` int32 — день недели (0 - воскресенье, 6 - суббота); `monthDay` int32 — день месяца (1–28).
  - `unit` object: `id` int32 — идентификатор единицы измерения; `value` string — название (например, "COUNT").
  - `intervals` array<object> — интервалы критичности: `id` int32; `active` boolean — активен ли интервал; `minValue` int64; `maxValue` int64; `autogeneration` boolean — флаг автоматической генерации события; `notificationGroupName` string — название группы оповещения; `type` string (NORMAL, WARNING, CRITICAL).
  - `automaticEvent` object — автоматическое событие мониторинга (если есть): `monitoringEvent` object: `id` int32; `monitoringCardRowId` int64 — ID карточки мониторинга; `name`; `description`; `type` — тип события; `status`; `tags` array<object> (`code` — код тега, `name` — название, `description` — описание, `type` — тип); `uploadToZSM` boolean — флаг выгрузки в ЗСМ; `eventScript` string — код события мониторинга; `alertedObjectUrlTemplate` string — шаблон ссылки на дашборд; `calculationIntervalInMinutes` int32 — частота выполнения в минутах. Также `sendIntervalValue` int32 — значение интервала повторной отправки; `sendIntervalUnit` string — интервал повторной отправки.
- Пример запроса: {"bsId":1073741824,"metricDto":{"id":1073741824,"metricId":1073741824,"name":"string","description":"string","status":"DRAFT","exportToKafka":true,"mcId":9007199254740991,"calculationMethod":"string","script":"string","calculationPeriod":1073741824,"metricSchedule":{"type":"MINUTE","timeHour":23,"timeMinute":59,"weekDay":6,"monthDay":1},"unit":{"id":1073741824,"value":"string"},"intervals":[{"id":1073741824,"active":true,"minValue":9007199254740991,"maxValue":9007199254740991,"autogeneration":true,"notificationGroupName":"string","type":"NORMAL"}],"automaticEvent":{"monitoringEvent":{"id":1073741824,"monitoringCardRowId":9007199254740991,"name":"string","description":"string","type":"MANUAL","status":"DRAFT","tags":[{"code":"string","name":"string","description":"string","type":"COMPUTED_ATTRIBUTE"}],"uploadToZSM":true,"eventScript":"string","alertedObjectUrlTemplate":"string","calculationIntervalInMinutes":1073741824},"sendIntervalValue":1073741824,"sendIntervalUnit":"MINUTE"}}} (2-POST _api_monitoring-event_metric_script-generation)
- Выходные параметры: метод возвращает строку — сгенерированный SQL-код для события мониторинга. (2-POST _api_monitoring-event_metric_script-generation)

### Бизнес-правила и ограничения
- Сгенерированный SQL в примере ответа состоит из двух CTE: `metrics` и `monitoring_events`. (2-POST _api_monitoring-event_metric_script-generation)
- `metrics`: из `default.bs_6606_metric_distributed` (алиас md), строки с `metric_id = 20363` и `md.insert_timestamp > toDateTime(now(), 'Europe/Moscow') - toIntervalMinute(19)`. severity: `when metric_value >0 then 'WARNING' else 'NORMAL'`. Также: metric_name as metricName, metric_value as metricValue, insert_timestamp as timeAlertCreated, cast(metric_uuid, 'String') as object, object as originalData, metric_object_count as additionalAttributes, toDateTime(now(), 'Europe/Moscow') as insert_timestamp, metric_object. (2-POST _api_monitoring-event_metric_script-generation)
- `monitoring_events`: externalId из `default.bs_6606_monitoring_event_distributed` (алиас me), где `externalId != ''` и `insert_timestamp > now() - interval '7 DAY'`. (2-POST _api_monitoring-event_metric_script-generation)
- Итоговый select: 'TRmonBS' as application, 'Бизнес-сервис' as category, severity, '6606' as ciName, 'Волков(базовый)' as serviceName, '2099 Транзакционный мониторинг - Волков(базовый). Новая метрика1' as title и as alertText, metricName, metricValue, timeAlertCreated, metric_object as object, metric_object as originalData, insert_timestamp, metrics.object as externalId. (2-POST _api_monitoring-event_metric_script-generation)
- Источник: from metrics left join monitoring_events on metrics.object = monitoring_events.externalId; условие: `metrics.object != monitoring_events.externalId and severity != 'NORMAL'`, `limit 1`. (2-POST _api_monitoring-event_metric_script-generation)

### API и интеграции
- URL: /api/monitoring-event/metric/script-generation; метод HTTP: POST; авторизация: JWT (token) пользователя. (2-POST _api_monitoring-event_metric_script-generation)
- Swagger: https://trmonbs-admin-service.ppmon.test.sfera-t1.ru/swagger-ui/index.html#/MonitoringEventController (2-POST _api_monitoring-event_metric_script-generation)

### Сообщения и ошибки
- Обработка ошибок: коды 400, 403, 409, 423, 500 (описания кодов не приведены). Успешный ответ: http-статус 200. (2-POST _api_monitoring-event_metric_script-generation)

### Роли и права
- Роли: Администратор. Авторизация: JWT (token) пользователя. (2-POST _api_monitoring-event_metric_script-generation)
