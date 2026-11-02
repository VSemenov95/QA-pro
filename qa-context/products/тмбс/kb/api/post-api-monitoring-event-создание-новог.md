# POST /api/monitoring-event — создание нового события мониторинга

> POST /api/monitoring-event — метод создания нового события мониторинга (в том числе ручного, с привязкой к сервису, коду отклонения, метрике и вычисляемому атрибуту), доступный роли Администратор.

### Описание
- Наименование метода: «Создание нового события мониторинга». URL: /api/monitoring-event. Метод HTTP: POST. (9-POST _api_monitoring-event)
- Способ авторизации: JWT (token) пользователя. (9-POST _api_monitoring-event)
- Ссылка на swagger: https://trmonbs-admin-service.ppmon.test.sfera-t1.ru/swagger-ui/index.html#/MonitoringEventController (9-POST _api_monitoring-event)

### Роли и права
- Роли: Администратор. (9-POST _api_monitoring-event)

### Поля и элементы
**Входные параметры** (столбцы таблицы: Параметр, Тип, Описание, Обязательный, Значение по умолчанию, Пример, Задача; признаки обязательности из-за повреждённого форматирования достоверно не восстановлены):
- status (string) — статус события мониторинга.
- monitoringEvent (object) — основная информация о событии:
  - id (int32) — идентификатор события мониторинга.
  - monitoringCardRowId (int64) — ID карточки мониторинга.
  - name (string) — название события.
  - description (string) — описание события.
  - type (string) — тип события (MANUAL или AUTO).
  - status (string) — статус события.
  - tags (array<object>) — список тегов события: code (string) — код тега; name (string) — название тега; description (string) — описание тега; type (string) — тип тега (например, MONITORING_EVENT).
  - uploadToZSM (boolean) — признак выгрузки события в ЗСМ.
  - eventScript (string) — SQL-код события мониторинга.
  - alertedObjectUrlTemplate (string) — шаблон ссылки на дашборд.
  - calculationIntervalInMinutes (int32) — частота выполнения запроса в минутах.
  - codeDeviation (object) — идентификатор кода отклонения: id (uuid), пример af9bd94b-c9e7-4b12-a2af-7e3123836f70; code (string), пример ШВ-1234.
- service (object): id (int4) — идентификатор сервиса, пример 8488; name (string) — наименование сервиса, пример «Сервис платежей»; code (string) — код сервиса, пример CI3000162.
- linkedMetric (object) — связанная метрика (если есть): id (int32); metricId (int32) — сквозной идентификатор метрики; name (string); description (string); status (string); exportToKafka (boolean) — признак экспорта во внешнюю систему.
- linkedComputedAttribute (object) — связанный вычисляемый атрибут (если есть): id (int32); metricId (int32) — сквозной идентификатор вычисляемого атрибута; name (string); description (string).
- notificationGroup (string) — название группы оповещений.
(9-POST _api_monitoring-event)

### API и интеграции
- Пример запроса: {"status":"DRAFT","monitoringEvent":{"id":1073741824,"monitoringCardRowId":9007199254740991,"name":"string","description":"string","type":"MANUAL","status":"DRAFT","tags":[{"code":"string","name":"string","description":"string","type":"COMPUTED_ATTRIBUTE"}],"uploadToZSM":true,"eventScript":"string","alertedObjectUrlTemplate":"string","calculationIntervalInMinutes":1073741824,"codeDeviation":{"id":"af9bd94b-c9e7-4b12-a2af-7e3123836f70","code":"ШВ-1231"}},"service":{"id":8488,"name":"Сервис платежей","code":"CI3000162"},"linkedMetric":{"id":1073741824,"metricId":1073741824,"name":"string","description":"string","status":"DRAFT","exportToKafka":true},"linkedComputedAttribute":{"id":1073741824,"metricId":1073741824,"name":"string","description":"string"},"notificationGroup":"string"} (9-POST _api_monitoring-event)
- Выходные параметры: состав и типы полей совпадают с входными (status, monitoringEvent с tags и codeDeviation, service, linkedMetric, linkedComputedAttribute, notificationGroup). Пример ответа совпадает с примером запроса. (9-POST _api_monitoring-event)
- История изменений: 1.0, @Kalinina D.А., 19 июн. 2026 — создание страницы. 1.1, @Perekin D.С., 22 июн. 2026 — дополнение атрибутов: для 1-ой поставки "codeDeviation" (фича PPMON-1651 ТМБС. Отправка отклонений в сторонние системы ч1); для 2-ой поставки "codeDeviationId" (фича PPMON-1784 ТМБС. Отправка отклонений в сторонние системы ч2); задача PPBP-2225 [SA] ТМБС. Отправка отклонений в сторонние системы ч4. 1.2, @Perekin D.С., 25 авг. 2026 — доработка контракта в рамках принадлежности ручного события мониторинга к сервису, задача PPBP-2528 [Аналитика] ТМБС. Подготовка артефактов для 4 варианта реализации. 1.3, @Perekin D.С., 16 сент. 2026 — изменен уровень объекта service (изменения подсвечены зеленым), задача PPBP-2528. (9-POST _api_monitoring-event)

### Сообщения и ошибки
- Обрабатываемые ошибки: 400, 403, 409, 423, 500; тексты сообщений не приведены. Успешный ответ: http-статус 200. (9-POST _api_monitoring-event)

### Открытые вопросы
- Раздел «Логика работы» (страница 10) содержит только заголовок, содержимого нет. (9-POST _api_monitoring-event)
- Не восстановлены однозначно столбцы «Обязательный», «Значение по умолчанию» и «Задача» для параметров. (9-POST _api_monitoring-event)
