# GET /api/monitoring-event/{eventId} — получение события мониторинга по идентификатору

> Метод GET /api/monitoring-event/{eventId} возвращает администратору событие мониторинга по идентификатору вместе с тегами, сервисом, связанной метрикой, вычисляемым атрибутом и группой оповещений.

### Описание
- URL: /api/monitoring-event/{eventId}; метод HTTP: GET; наименование: Получение события мониторинга по идентификатору. (12-GET _api_monitoring-event_{eventId})
- Ссылка на swagger: https://trmonbs-admin-service.ppmon.test.sfera-t1.ru/swagger-ui/index.html#/MonitoringEventController (12-GET _api_monitoring-event_{eventId})

### Поля и элементы
**Входные параметры**
- authorization: string, JWT (token) пользователя, header, обязательный (+), значение по умолчанию и пример не указаны. (12-GET _api_monitoring-event_{eventId})
- eventId: int32, идентификатор события мониторинга, path, обязательный (+), по умолчанию нет, пример 123. (12-GET _api_monitoring-event_{eventId})

**Выходные параметры** (+ обязательный, - необязательный; признаки восстановлены по порядку строк и могут быть неточными)
- status: string, статус события мониторинга (+)
- monitoringEvent: object, основная информация о событии (+):
  - id: int32, идентификатор события (+)
  - monitoringCardRowId: int64, ID карточки мониторинга (+)
  - name: string, название события (+)
  - description: string, описание события (-)
  - type: string, тип события (MANUAL или AUTO) (+)
  - status: string, статус события (+)
  - tags: array<object>, список тегов (+): code: string, код тега (+); name: string, название тега (+); description: string, описание тега (-); type: string, тип тега (например, MONITORING_EVENT) (+)
  - uploadToZSM: boolean, признак выгрузки события в ЗСМ (+)
  - eventScript: string, SQL-код события мониторинга (-)
  - alertedObjectUrlTemplate: string, шаблон ссылки на дашборд (-)
  - calculationIntervalInMinutes: int32, частота выполнения запроса в минутах (+)
  - codeDeviation: object: id: uuid, идентификатор кода отклонения (-); code: string, код отклонения (-)
- service: object: id: int4, идентификатор сервиса (+); name: string, наименование сервиса (+); code: string, код сервиса (+)
- linkedMetric: object, связанная метрика (если есть) (-): id: int32 (+); metricId: int32, сквозной идентификатор метрики (+); name: string (+); description: string (-); status: string (+); exportToKafka: boolean, признак экспорта во внешнюю систему (+)
- linkedComputedAttribute: object, связанный вычисляемый атрибут (если есть) (-): id: int32 (+); metricId: int32, сквозной идентификатор вычисляемого атрибута (+); name: string (+); description: string (-)
- notificationGroup: string, название группы оповещений (-)
(12-GET _api_monitoring-event_{eventId})

### Бизнес-правила и ограничения
- История изменений: 1.0, @Kalinina D.А., 19 июн. 2026: создание страницы. 1.1, @Perekin D.С., 22 июн. 2026: дополнение атрибутов: для 1-ой поставки "codeDeviation" (фича PPMON-1651 ТМБС. Отправка отклонений в сторонние системы ч1); для 2-ой поставки "codeDeviationId" (фича PPMON-1784 ТМБС. Отправка отклонений в сторонние системы ч2); задача PPBP-2225 [SA] ТМБС. Отправка отклонений в сторонние системы ч4. 1.2, @Perekin D.С., 24 июн. 2026: изменение атрибута в рамках 2-ой поставки PPMON-1784; задача PPBP-2225. 1.3, @Perekin D.С., 25 авг. 2026: доработка контракта в рамках принадлежности ручного события мониторинга к сервису; задача PPBP-2528 [Аналитика] ТМБС. Подготовка артефактов для 4 варианта реализации. 1.4, @Perekin D.С., 16 сент. 2026: изменен уровень объекта service (изменения подсвечены зелёным); задача PPBP-2528. (12-GET _api_monitoring-event_{eventId})
- В таблице выходных параметров у объекта codeDeviation указана задача PPBP-2530 [US] Доработка 4-го варианта реализации. (12-GET _api_monitoring-event_{eventId})

### API и интеграции
- Способ авторизации: JWT (token) пользователя. (12-GET _api_monitoring-event_{eventId})
- Обработка ошибок: 400, 403, 409, 423, 500; http-статус в ответе: 200. (12-GET _api_monitoring-event_{eventId})
- Пример запроса: GET https://trmonbs-admin-service.ppmon.dev.sfera-t1.ru/api/monitoring-event/123 (12-GET _api_monitoring-event_{eventId})
- Пример ответа: {"status":"DRAFT","monitoringEvent":{"id":1073741824,"monitoringCardRowId":9007199254740991,"name":"string","description":"string","type":"MANUAL","status":"DRAFT","tags":[{"code":"string","name":"string","description":"string","type":"COMPUTED_ATTRIBUTE"}],"uploadToZSM":true,"eventScript":"string","alertedObjectUrlTemplate":"string","calculationIntervalInMinutes":1073741824,"codeDeviation":{"id":"af9bd94b-c9e7-4b12-a2af-7e3123836f70","code":"ШВ-1231"}},"service":{"id":8488,"name":"Сервис платежей","code":"CI3000162"},"linkedMetric":{"id":1073741824,"metricId":1073741824,"name":"string","description":"string","status":"DRAFT","exportToKafka":true},"linkedComputedAttribute":{"id":1073741824,"metricId":1073741824,"name":"string","description":"string"},"notificationGroup":"string"} (12-GET _api_monitoring-event_{eventId})
- В примере ответа в linkedComputedAttribute нет поля status. (12-GET _api_monitoring-event_{eventId})

### Роли и права
- Роли: Администратор. (12-GET _api_monitoring-event_{eventId})

### Открытые вопросы
- Раздел «Логика работы» есть в оглавлении, но его содержимое пустое. (12-GET _api_monitoring-event_{eventId})
- Таблица выходных параметров в PDF разбита по страницам; колонки «Значение по умолчанию» и «Пример» для выходных параметров не читаются; признаки обязательности могут быть неточными. (12-GET _api_monitoring-event_{eventId})

### Расхождения между документами
- Тип тега: в описании параметра «например, MONITORING_EVENT», в примере ответа COMPUTED_ATTRIBUTE. (12-GET _api_monitoring-event_{eventId})
- В истории изменений упомянут атрибут "codeDeviationId", в выходных параметрах и примере ответа используется codeDeviation с полями id и code. (12-GET _api_monitoring-event_{eventId})
