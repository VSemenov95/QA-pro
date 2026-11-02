# GET /api/computedAttribute/{computedAttributeId} — получение информации о вычисляемом атрибуте

> GET-метод REST API ТМБС для получения полной информации о вычисляемом атрибуте по его идентификатору (с данными о сервисе, шаблоне, событии мониторинга, тегах и интервалах).

### Описание
- URL*: /api/computedAttribute/{computedAttributeId}; метод HTTP*: GET; наименование метода*: Получение информации о вычисляемом атрибуте (6-GET _api_computedAttribute_{computedAttributeId}).
- Ссылка на swagger: https://trmonbs-admin-service.ppmon.dev.sfera-t1.ru/swagger-ui/index.html#/ComputedAttributeController/getComputedAttribute (6-GET _api_computedAttribute_{computedAttributeId}).
- История изменений: версия 1.0, @Perekin D.С., 27 апр. 2026 — создание страницы; задача PPBP-1997 [SA] ТМБС. Отправка отклонений в сторонние системы. Версия 1.1, @Perekin D.С., 26 авг. 2026 — доработка контракта в рамках принадлежности выч. атрибута к сервису (изменения подсвечены зелёным); задача PPBP-2528 [Аналитика] ТМБС. Подготовка артефактов для 4 варианта реализации (6-GET _api_computedAttribute_{computedAttributeId}).

### Роли и права
- Роли*: Администратор; способ авторизации*: JWT (token) пользователя (6-GET _api_computedAttribute_{computedAttributeId}).

### API и интеграции
- Входные параметры:
  - authorization — string — JWT (token) пользователя; расположение: header path; обязательный: +; по умолчанию: -.
  - computedAttributeId — int32 — Идентификатор вычисляемого атрибута; расположение: header path; обязательный: +; по умолчанию: -; пример: 1812 (6-GET _api_computedAttribute_{computedAttributeId}).
- Пример запроса: 'https://trmonbs-admin-service.ppmon.dev.sfera-t1.ru/api/computedAttribute/1812 (6-GET _api_computedAttribute_{computedAttributeId}).
- Выходные параметры (отметки «обязательный» разобраны с потерями):
  - computedAttributeId (int32) — Сквозной идентификатор выч. атрибута; в примере null.
  - id (int32) — Идентификатор вычисляемого атрибута.
  - name (string) — Имя; обязательный: +.
  - mcId (int64) — ID карточки мониторинга; обязательный: +.
  - calculationMethod (string) — Методика расчёта.
  - description (string) — Описание.
  - status (string) — описание не приведено; в примере «MONITORING».
  - groups (array<object>) — обязательный: +; items: id (int32) — Идентификатор группы вычисляемого атрибута; value (string) — Значение группы.
  - type (string) — Тип выч. атрибута; в примере «GENERAL».
  - transactionType (string) — Класс выч. атрибута; в примере «TRANSACTIONAL».
  - service (object) — Сервис: id (int4) — Идентификатор сервиса, пример 8488; name (string) — Наименование сервиса, пример «Сервис платежей»; code (string) — Код сервиса, пример CI3000162.
  - automaticEvent (object) — Автоматическое событие мониторинга; в примере null.
  - monitoringEvent (object) — Общее ядро события мониторинга (поля автоматических и ручных событий), вложенное в ManualMonitoringEventDto / AutoMonitoringEventDto; обязательный: +. Поля: id (int32) — Идентификатор события мониторинга; monitoringCardRowId (int64) — ID карточки мониторинга (первичный ключ); name (string) — Наименование события; description (string) — Описание события; type (string) — Тип события мониторинга, значения: "MANUAL", "AUTO"; status (string) — Статус события мониторинга; uploadToZSM (boolean) — Признак выгрузки события в ЗСМ; eventScript (string) — SQL-код события мониторинга; alertedObjectUrlTemplate (string) — Шаблон ссылки на объект алерта; calculationIntervalInMinutes (int32) — Частота выполнения запроса в минутах; codeDeviation (object): id (uuid) — Идентификатор кода отклонения, code (string) — Значение кода отклонения; sendIntervalValue (int32) — Значение интервала отправки; sendIntervalUnit (string) — описание не приведено.
  - tags (object и array<object>; в описании monitoringEvent): code (string) — Код тега; name (string) — Название тега; description (string) — Описание тега; type (string) — Тип тега (к какой группе относится), значения: "COMPUTED_ATTRIBUTE", "METRIC", "SERVICE_METRIC", "CHECKPOINT", "MONITORING_EVENT".
  - template (object) — Базовая сущность (ссылка на шаблон): id (int32) — Идентификатор шаблона; name (string) — Наименование шаблона; status (string) — статус шаблона.
  - templateParametersApplied (array<object>) — Значения параметров шаблона, применённые к выч. атрибуту; items: code (string) — Код параметра шаблона; name (string) — Наименование параметра; type (string) — Тип; value (string) — Значение, переданное при применении или синхронизации шаблона.
  - syncedWithTemplate (boolean) — Признак синхронизации сущности с шаблоном.
  - manualIntervalOverride (boolean) — Признак того, что пользователь вручную изменил пороги критичности.
  - В примере ответа также есть поля script, unit (id, value) и intervals; их описаний в таблице нет.
- Пример ответа: id: 78047; computedAttributeId: null; name: "Шаблон номер раз"; mcId: 190548; calculationMethod: "4564"; description: "вврвввв"; status: "MONITORING"; groups: {id: 1, value: "Аномальность"}, {id: 4, value: "Своевременность"}; type: "GENERAL"; transactionType: "TRANSACTIONAL"; service: {id: "8488", name: "Сервис Платежей", code: "CI3000162"}; automaticEvent: null; tags: {code: "6", name: "metric4", description: "metric4", type: "COMPUTED_ATTRIBUTE"}, {code: "tag_1", name: "Тег 1", description: "Описание для тега 1", type: "COMPUTED_ATTRIBUTE"}, {code: "tag_12", name: "Тег 12", description: "Описание для тега 12", type: "COMPUTED_ATTRIBUTE"}; template: {id: 51, name: "Шаблон номер раз", status: "ACTIVE"}; templateParametersApplied: {code: "payment_1", name: "1", type: "NUMBER", value: "4"}; syncedWithTemplate: true; manualIntervalOverride: false; script: "select sum(amount) from data\n where event_stage in ('4')\n having count(distinct event_stage)\n filter(where event_stage in ('4')) = 2"; unit: {id: 1, value: "Шт"}; intervals: {id: 217439, active: true, minValue: null, maxValue: 2, autogeneration: null, notificationGroupName: null, type: "NORMAL"}, {id: 217440, active: true, minValue: 2, maxValue: 6, autogeneration: false, notificationGroupName: null, type: "WARNING"}, {id: 217438, active: true, minValue: 6, maxValue: null, autogeneration: false, notificationGroupName: null, type: "CRITICAL"} (6-GET _api_computedAttribute_{computedAttributeId}).

### Сообщения и ошибки
- http-статус коды в ответе: 200; обработка ошибок*: 400, 403, 409, 423, 500 (6-GET _api_computedAttribute_{computedAttributeId}).

### Открытые вопросы
- Раздел «Логика работы» есть в оглавлении и в конце документа, но текста в нём нет (6-GET _api_computedAttribute_{computedAttributeId}).
- Для script, unit и intervals нет описаний в таблице выходных параметров (6-GET _api_computedAttribute_{computedAttributeId}).
- Расположение authorization и computedAttributeId указано как «header path»; не уточнено, какое значение к какому параметру относится (6-GET _api_computedAttribute_{computedAttributeId}).
