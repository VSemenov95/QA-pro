# PUT /api/monitoring-event/{eventId} — обновление события мониторинга

> PUT /api/monitoring-event/{eventId} — метод обновления события мониторинга (в том числе ручного, с привязкой к сервису и коду отклонения), доступный администратору по JWT.

### Описание
- URL: /api/monitoring-event/{eventId}; метод HTTP: PUT; наименование метода: Обновление события мониторинга. (9-PUT _api_monitoring-event_{eventId})
- Способ авторизации: JWT (token) пользователя. (9-PUT _api_monitoring-event_{eventId})
- Ссылка на swagger: https://trmonbs-admin-service.ppmon.test.sfera-t1.ru/swagger-ui/index.html#/MonitoringEventController (9-PUT _api_monitoring-event_{eventId})
- Оглавление страницы: Описание метода, История изменений, Входные параметры, Пример запроса, Выходные параметры, Пример ответа, Логика работы. Раздел «Логика работы» присутствует только как заголовок, содержимого нет. (9-PUT _api_monitoring-event_{eventId})

### Роли и права
- Роли: Администратор. (9-PUT _api_monitoring-event_{eventId})

### API и интеграции
- Входные параметры (столбцы: Параметр, Тип, Описание, Обязательный, Значение по умолчанию, Пример, Задача). Обязательность указана «+»/«-», разобрана частично. (9-PUT _api_monitoring-event_{eventId})
  - eventId — int32, path — Идентификатор события мониторинга (+)
  - status — string — Статус события мониторинга (+)
  - monitoringEvent — object — Основная информация о событии (+):
    - id — int32 — Идентификатор события мониторинга (+)
    - monitoringCardRowId — int64 — ID карточки мониторинга (+)
    - name — string — Название события (+)
    - description — string — Описание события (-)
    - type — string — Тип события (MANUAL или AUTO) (+)
    - status — string — Статус события (+)
    - tags — array<object> — Список тегов события (+): code — string — Код тега (+); name — string — Название тега (+); description — string — Описание тега (-); type — string — Тип тега, например MONITORING_EVENT (+)
    - uploadToZSM — boolean — Признак выгрузки события в ЗСМ (+)
    - eventScript — string — SQL-код события мониторинга (-)
    - alertedObjectUrlTemplate — string — Шаблон ссылки на дашборд (-)
    - calculationIntervalInMinutes — int32 — Частота выполнения запроса в минутах (+)
    - codeDeviation — object (-): id — uuid — Идентификатор кода отклонения, пример af9bd94b-c9e7-4b12-a2af-7e3123836f70; code — string, пример ШВ-1231
  - service — object: id — int4 — Идентификатор сервиса, пример 8488; name — string — Наименование сервиса, пример Сервис платежей; code — string — Код сервиса, пример CI3000162
  - linkedMetric — object — Связанная метрика (если есть): id — int32 — Идентификатор метрики; metricId — int32 — Сквозной идентификатор метрики; name — string — Имя метрики; description — string — Описание метрики; status — string — Статус метрики; exportToKafka — boolean — Признак экспорта во внешнюю систему
  - linkedComputedAttribute — object — Связанный вычисляемый атрибут (если есть): id — int32 — Идентификатор вычисляемого атрибута; metricId — int32 — Сквозной идентификатор вычисляемого атрибута; name — string — Имя вычисляемого атрибута; description — string — Описание вычисляемого атрибута
  - notificationGroup — string — Название группы оповещений
- Пример запроса (тело): {"status":"DRAFT","monitoringEvent":{"id":1073741824,"monitoringCardRowId":9007199254740991,"name":"string","description":"string","type":"MANUAL","status":"DRAFT","tags":[{"code":"string","name":"string","description":"string","type":"COMPUTED_ATTRIBUTE"}],"uploadToZSM":true,"eventScript":"string","alertedObjectUrlTemplate":"string","calculationIntervalInMinutes":1073741824,"codeDeviation":{"id":"af9bd94b-c9e7-4b12-a2af-7e3123836f70","code":"ШВ-1231"}},"service":{"id":8488,"name":"Сервис платежей","code":"CI3000162"},"linkedMetric":{"id":1073741824,"metricId":1073741824,"name":"string","description":"string","status":"DRAFT","exportToKafka":true},"linkedComputedAttribute":{"id":1073741824,"metricId":1073741824,"name":"string","description":"string"},"notificationGroup":"string"} (9-PUT _api_monitoring-event_{eventId})
- Выходные параметры: структура и описания полей совпадают с входными (status, monitoringEvent с tags и codeDeviation, service, linkedMetric, linkedComputedAttribute, notificationGroup), кроме eventId (path), которого в выходных нет. (9-PUT _api_monitoring-event_{eventId})
- Пример ответа полностью совпадает с примером запроса (status DRAFT и те же значения). (9-PUT _api_monitoring-event_{eventId})

### Бизнес-правила и ограничения
- Обработка ошибок: 400, 403, 409, 423, 500; успешный ответ — 200. (9-PUT _api_monitoring-event_{eventId})
- Поле codeDeviation добавлено для 1-й поставки (PPMON-1651 ТМБС. Отправка отклонений в сторонние системы ч1); поле codeDeviationId — для 2-й поставки (PPMON-1784 ТМБС. Отправка отклонений в сторонние системы ч2). (9-PUT _api_monitoring-event_{eventId})
- Контракт доработан в рамках принадлежности ручного события мониторинга к сервису; уровень объекта service изменён (изменения подсвечены зелёным цветом в оригинале). (9-PUT _api_monitoring-event_{eventId})

### История изменений
- 1.0 — @Kalinina D.А., 19 июн. 2026 — Создание страницы. (9-PUT _api_monitoring-event_{eventId})
- 1.1 — @Perekin D.С., 22 июн. 2026 — Дополнение атрибутов: «codeDeviation» (1-я поставка, PPMON-1651) и «codeDeviationId» (2-я поставка, PPMON-1784). Задача: PPBP-2225 [SA] ТМБС. Отправка отклонений в сторонние системы ч4. (9-PUT _api_monitoring-event_{eventId})
- 1.2 — @Perekin D.С., 25 авг. 2026 — Доработка контракта в рамках принадлежности ручного события мониторинга к сервису. Задача: PPBP-2528 [Аналитика] ТМБС. Подготовка артефактов для 4 варианта реализации. (9-PUT _api_monitoring-event_{eventId})
- 1.3 — @Perekin D.С., 16 сент. 2026 — Изменен уровень объекта service (подсвечено зеленым). Задача: PPBP-2528. (9-PUT _api_monitoring-event_{eventId})

### Открытые вопросы
- Раздел «Логика работы» не содержит текста. (9-PUT _api_monitoring-event_{eventId})
- Часть значений столбцов «Обязательный», «Значение по умолчанию» и «Пример» повреждена при извлечении; обязательность восстановлена неполно. (9-PUT _api_monitoring-event_{eventId})
