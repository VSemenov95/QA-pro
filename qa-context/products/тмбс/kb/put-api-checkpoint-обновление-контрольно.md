# PUT /api/checkpoint — обновление контрольной точки

> Метод PUT /api/checkpoint обновляет контрольную точку (КТ) карточки мониторинга: принимает её общие данные, сервис, атрибуты, константы обогащения и группы правил фильтрации и возвращает обновлённую КТ.

### Описание
- URL: /api/checkpoint; метод HTTP: PUT; наименование метода: Обновление контрольной точки; способ авторизации: JWT (token) пользователя. (PUT _api_checkpoint-10)
- Swagger: https://trmonbs-admin-service.ppmon.dev.sfera-t1.ru/swagger-ui/index.html#/CheckpointController/updateCheckpoint (контроллер CheckpointController, операция updateCheckpoint, сервис trmonbs-admin-service). (PUT _api_checkpoint-10)
- Оглавление страницы: Описание метода, История изменений, Входные параметры, Пример запроса, Выходные параметры, Пример ответа, Логика работы. В предоставленном фрагменте разделы «Пример запроса», «Пример ответа» и «Логика работы» содержат только заголовки, без содержимого. (PUT _api_checkpoint-10)
- История изменений: 1.0, @Perekin D.С., 17 мар. 2026 — создание страницы, задача PPBP-1863 [Аналитика] ТМБС. Сервисы. Передача метрик из ТМБС в ЗСМ в привязке к сервисам с агрегирующим расчетом на строне ТМБС ч2. 1/1, 23 мар. 2026 — изменен атрибут "ServiceId" на объект "Service" в теле запроса. 1.2, 25 мая 2026 — дополнен атрибут "searchAttributeCode", задача PPBP-1955 [Аналитика] ТМБС. АПИ для поиска БС и id транзакции по заданным полям. 1.3, 26 авг. 2026 — доработка контракта в рамках принадлежности выч. атрибута к сервису (изменения подсвечены зеленым), задача PPBP-2528 [Аналитика] ТМБС. Подготовка артефактов для 4 варианта реализации. (PUT _api_checkpoint-10)

### Поля и элементы
Входные параметры (колонки: Параметр, Тип, Описание, Расположение, Обязательный, По умолчанию, Пример):
- authorization (string) — JWT (token) пользователя; header; обязательный. (PUT _api_checkpoint-10)
- id (int32) — идентификатор контрольной точки; body; необязательный. (PUT _api_checkpoint-10)
- mcId (int64) — ID карточки мониторинга (первичный ключ); body; обязательный. (PUT _api_checkpoint-10)
- infSystemId (int32) — идентификатор информационной системы; body; необязательный; в колонке значения указано infSystemId. (PUT _api_checkpoint-10)
- dataSourceRowId (int32) — идентификатор конкретной версии источника данных; body; необязательный; в колонке значения указано dataSourceRowId. (PUT _api_checkpoint-10)
- dataSourceId (int32) — идентификатор источника данных; body; необязательный; в колонке значения указано dataSourceId. (PUT _api_checkpoint-10)
- name (string) — имя контрольной точки; необязательный. (PUT _api_checkpoint-10)
- status (string) — статус контрольной точки; обязательный; по умолчанию DRAFT; пример DRAFT. (PUT _api_checkpoint-10)
- mandatory (boolean) — флаг обязательности контрольной точки; обязательный; по умолчанию false. (PUT _api_checkpoint-10)
- monitoringObject (string) — Общая информация КТ: Объект мониторинга; необязательный. (PUT _api_checkpoint-10)
- processStep (string) — Общая информация КТ: Шаг процесса; необязательный. (PUT _api_checkpoint-10)
- monitoringDesc (string) — Общая информация КТ: Что мониторим; необязательный. (PUT _api_checkpoint-10)
- description (string) — Общая информация КТ: Описание контрольной точки; необязательный. (PUT _api_checkpoint-10)
- service (object) — Сервис; необязательный: id (int4, идентификатор сервиса, пример 8488), name (string, наименование сервиса, пример «Сервис платежей»), code (string, код сервиса, пример CI3000162). (PUT _api_checkpoint-10)
- attributes (array<object>) — атрибуты КТ; необязательный. Элемент: id (int32); name (string); description (string); keyIdentifier (boolean, флаг ключевого атрибута); technicalAttributeId (int32, идентификатор технического аттрибута); identifierType (string, тип атрибута; обязательный; по умолчанию TRANSACTIONAL; пример TRANSACTIONAL); searchAttributeCode (string, код атрибута поиска; необязательный). (PUT _api_checkpoint-10)
- enrichmentConstants (array<object>) — константы обогащения; необязательный. Элемент: id (int32); name (string, название, обязательный); value (string, значение, необязательный). (PUT _api_checkpoint-10)
- isOffUt (boolean) — выключить ли user_transaction_time; необязательный; по умолчанию false. (PUT _api_checkpoint-10)
- group (object) — необязательный: id (int32, идентификатор группы); order (int32, порядковый номер группы); logicalOperator (string, логический оператор (И/ИЛИ)); rules (array<object>, правила группы): id (int32), order (int32, обязательный), technicalAttributeId (int32, обязательный), operatorCode (string, код оператора, обязательный), parameters (object, параметры правила, items string); nestedGroups (array<any>, вложенные группы правил, $ref на схему GroupDTO: https://trmonbs-admin-service.ppmon.dev.sfera-t1.ru/v3/api-docs#/components/schemas/GroupDTO). (PUT _api_checkpoint-10)
- type (string) — тип КТ; необязательный. (PUT _api_checkpoint-10)
- dataSourceVersion (int32) — версия источника, связанная с КТ; необязательный; в колонке значения указано TRANSACTIONAL. (PUT _api_checkpoint-10)

Выходные параметры (расположение: response body, в документе «responce body»):
- Структура повторяет входную: id, mcId (обязательный), infSystemId, dataSourceRowId, dataSourceId, name, status (обязательный; по умолчанию DRAFT; пример DRAFT), mandatory (обязательный; по умолчанию false), monitoringObject, processStep, monitoringDesc, description, service (id, name, code с теми же примерами), attributes (id, name, description, keyIdentifier, technicalAttributeId, identifierType, searchAttributeCode), enrichmentConstants (id, name, value), isOffUt, group (id, order, logicalOperator, rules[id, order, technicalAttributeId, operatorCode, parameters], nestedGroups по GroupDTO), type, dataSourceVersion (в колонке значения указано TRANSACTIONAL). Описания и типы полей — как во входных параметрах. (PUT _api_checkpoint-10)

### API и интеграции
- PUT /api/checkpoint, CheckpointController, операция updateCheckpoint (swagger сервиса trmonbs-admin-service); схема вложенных групп — GroupDTO в v3/api-docs. (PUT _api_checkpoint-10)

### Сообщения и ошибки
- Обработка ошибок: 400, 403, 409, 423, 500. (PUT _api_checkpoint-10)
- HTTP-статус в ответе: 200. (PUT _api_checkpoint-10)

### Роли и права
- Роли: Администратор. (PUT _api_checkpoint-10)
- Способ авторизации: JWT (token) пользователя (параметр authorization, header). (PUT _api_checkpoint-10)
