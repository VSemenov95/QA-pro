# GET /api/checkpoint/{checkPointId} — получение информации контрольной точки

> Метод GET /api/checkpoint/{checkPointId} возвращает администратору полную информацию о контрольной точке (КТ): общие данные, сервис, атрибуты, константы обогащения, группы правил и версию источника данных.

### Описание
- Наименование метода: Получение информации контрольной точки. (GET _api_checkpoint_{checkpointId}-8)
- Разделы документа: Описание метода, История изменений, Входные параметры, Пример запроса, Выходные параметры, Пример ответа, Логика работы. Содержимое разделов «Пример запроса», «Пример ответа» и «Логика работы» во фрагменте отсутствует (только заголовки). (GET _api_checkpoint_{checkpointId}-8)
- История изменений: v1.0, @Perekin D.С., 17 мар. 2026 — создание страницы, задача PPBP-1863 [Аналитика] ТМБС. Сервисы. Передача метрик из ТМБС в ЗСМ в привязке к сервисам с агрегирующим расчетом на строне ТМБС ч2; v1.1, 25 мая 2026 — дополнен атрибут "searchAttributes" (изменения подсвечены зеленым), задача PPBP-1955 [Аналитика] ТМБС. АПИ для поиска БС и id транзакции по заданным полям; v1.2, 26 авг. 2026 — доработка контракта в рамках принадлежности КТ к сервису (изменения подсвечены зеленым), задача PPBP-2528 [Аналитика] ТМБС. Подготовка артефактов для 4 варианта реализации. (GET _api_checkpoint_{checkpointId}-8)

### Поля и элементы
Входные параметры:
- authorization — string, JWT (token) пользователя, header, обязательный (+), по умолчанию «-». (GET _api_checkpoint_{checkpointId}-8)
- checkPointId — int32, внутренний идентификатор контрольной точки, расположение: header (в URL указан как {checkPointId}), обязательный (+), по умолчанию «-», пример 7777. (GET _api_checkpoint_{checkpointId}-8)

Выходные параметры (все в response body):
- id — int32, идентификатор контрольной точки. (GET _api_checkpoint_{checkpointId}-8)
- mcId — int64, ID карточки мониторинга (первичный ключ), обязательный. (GET _api_checkpoint_{checkpointId}-8)
- infSystemId — int32, идентификатор информационной системы (пример: infSystemId). (GET _api_checkpoint_{checkpointId}-8)
- dataSourceRowId — int32, идентификатор конкретной версии источника данных (пример: dataSourceRowId). (GET _api_checkpoint_{checkpointId}-8)
- dataSourceId — int32, идентификатор источника данных (пример: dataSourceId). (GET _api_checkpoint_{checkpointId}-8)
- name — string, имя контрольной точки. (GET _api_checkpoint_{checkpointId}-8)
- status — string, статус контрольной точки, обязательный, пример DRAFT. (GET _api_checkpoint_{checkpointId}-8)
- mandatory — boolean, флаг обязательности контрольной точки, обязательный, пример false. (GET _api_checkpoint_{checkpointId}-8)
- monitoringObject — string, общая информация КТ: Объект мониторинга. (GET _api_checkpoint_{checkpointId}-8)
- processStep — string, общая информация КТ: Шаг процесса. (GET _api_checkpoint_{checkpointId}-8)
- monitoringDesc — string, общая информация КТ: Что мониторим. (GET _api_checkpoint_{checkpointId}-8)
- description — string, общая информация КТ: Описание контрольной точки. (GET _api_checkpoint_{checkpointId}-8)
- service — object, Сервис: service.id (int32, идентификатор сервиса, пример 8488); service.name (string, наименование сервиса, пример «Сервис платежей»); service.code (string, код сервиса, пример CI3000162). (GET _api_checkpoint_{checkpointId}-8)
- attributes — array<object>, атрибуты КТ; элемент: id (int32, идентификатор атрибута КТ), name (string, наименование атрибута), description (string, описание атрибута), keyIdentifier (boolean, флаг ключевого атрибута), technicalAttributeId (int32, идентификатор технического аттрибута), identifierType (string, тип атрибута). (GET _api_checkpoint_{checkpointId}-8)
- searchAttributeCode — string, код атрибута поиска. (GET _api_checkpoint_{checkpointId}-8)
- enrichmentConstants — array<object>, константы обогащения; элемент: id (int32), name (string, название константы обогащения), value (string, значение константы обогащения). (GET _api_checkpoint_{checkpointId}-8)
- isOffUt — boolean, «Выключить ли user_transaction_time». (GET _api_checkpoint_{checkpointId}-8)
- group — object, группа правил: id (int32), order (int32, порядковый номер группы), logicalOperator (string, логический оператор И/ИЛИ), rules (array<object>, правила группы; элемент: id, order — порядковый номер правила, technicalAttributeId, operatorCode — код оператора, parameters — object, параметры правила, items: string), nestedGroups (array<any>, вложенные группы правил, $ref на GroupDTO). (GET _api_checkpoint_{checkpointId}-8)
- type — string, тип КТ, пример TRANSACTIONAL. (GET _api_checkpoint_{checkpointId}-8)
- dataSourceVersion — int32, версия источника, которая связана с КТ. (GET _api_checkpoint_{checkpointId}-8)
- Значения в колонках «Обязательный» и «Пример» для части строк в исходнике сдвинуты из-за разбора PDF; принадлежность полей к service, attributes, group восстановлена по структуре вложенности. (GET _api_checkpoint_{checkpointId}-8)

### Бизнес-правила и ограничения
- Статус КТ в примере: DRAFT. (GET _api_checkpoint_{checkpointId}-8)
- Тип КТ в примере: TRANSACTIONAL. (GET _api_checkpoint_{checkpointId}-8)
- isOffUt: «Выключить ли user_transaction_time». (GET _api_checkpoint_{checkpointId}-8)
- Логический оператор группы правил: И/ИЛИ. (GET _api_checkpoint_{checkpointId}-8)

### API и интеграции
- URL*: /api/checkpoint/{checkPointId}; Метод HTTP*: GET. (GET _api_checkpoint_{checkpointId}-8)
- Способ авторизации*: JWT (token) пользователя. (GET _api_checkpoint_{checkpointId}-8)
- Swagger: https://trmonbs-admin-service.ppmon.dev.sfera-t1.ru/swagger-ui/index.html#/CheckpointController/getCheckpoint (GET _api_checkpoint_{checkpointId}-8)
- Схема вложенных групп: $ref https://trmonbs-admin-service.ppmon.dev.sfera-t1.ru/v3/api-docs#/components/schemas/GroupDTO (GET _api_checkpoint_{checkpointId}-8)
- http-статус кода в ответе: 200. (GET _api_checkpoint_{checkpointId}-8)

### Сообщения и ошибки
- Обработка ошибок*: 400, 403, 409, 423, 500 (тексты сообщений не приведены). (GET _api_checkpoint_{checkpointId}-8)
- Успешный ответ: http-статус 200. (GET _api_checkpoint_{checkpointId}-8)

### Роли и права
- Роли*: Администратор. (GET _api_checkpoint_{checkpointId}-8)

### Открытые вопросы
- Разделы «Пример запроса», «Пример ответа» и «Логика работы» пусты.  (GET _api_checkpoint_{checkpointId}-8)
- checkPointId указан как header, хотя в URL это path-параметр {checkPointId}. (GET _api_checkpoint_{checkpointId}-8)

<!-- qa-pro:kb
{"id":"f18ew8hfuvbi","area":"api","parts":[{"docId":"import_audit_execution_history","docName":"Сфера.Аудит — история прохождений и тест-план.md","chunk":3,"sections":["PPBP-3598 · [BE] Проверка события CHECKPOINT_GET_CHECKPOINT"],"md":"### Бизнес-правила и ограничения\n- Предусловия: `SFERA_AUDIT_ENABLED = true`, `SFERA_AUDIT_TRANSPORT_MODE=KAFKA`, `SFERA_AUDIT_KAFKA_TOPIC=audit-topic`.\n- Существует контрольная точка, известен идентификатор `checkpointId`, например `341566`.\n### API и интеграции\n- Шаг 1: отправить `GET {{baseURL}}/api/checkpoint/{checkpointId}`. Ожидается `Статус Код 200 OK`.\n- Шаги 2 и 3: проверить в Kafka сообщения события `CHECKPOINT_GET_CHECKPOINT` со статусами `START` и `SUCCESS`; оба присутствуют в топике `audit-topic`.\n### Сообщения и ошибки\n- Общие поля примеров: `version=\"1.0\"`, `correlationId=\"85922d02-b68b-47d4-b058-bbabc69d16a1\"`, `code=\"PPBP_CHECKPOINT_GET_CHECKPOINT\"`, `infoSystemCode=\"PPBP\"`, `infoSystemId=\"2099\"`, `additionalAttributes.checkpointId=341566`.\n- `userIdentity.login=\"sa-ppbp\"`, `userIdentity.sourceIPAddress=\"10.228.64.26\"`; в `userIdentity.requestMetadata`: `ipNearbyNode=\"10.228.64.26\"`, `ipRecipient=\"10.233.70.181\"`, `sessionId=\"\"`, `url=\"/api/checkpoint/341566\"`, `method=\"GET\"`.\n- `podName=\"trmonbs-admin-service-7ccd75fc66-gl4xl\"`, `namespace=\"ppbp\"`, `eventCodeAlias=null`, `eventType=\"Просмотр\"`, `businessOperation=\"Получение информации о контрольной точке\"`, `businessObject=\"Контрольная точка\"`, `businessObjectExpression=null`, `title=\"'Получение информации о контрольной точке'\"`, `crossSystemEvent=false`, `userType=\"ANY\"`, `eventLevel=\"MEDIUM\"`, `vendor=\"Sfera\"`, `techSectionCode=\"hi\"`, `starterVersion=\"4.2.3-java-17\"`.\n- Начало: `status=\"START\"`, `messageTemplate=\"Начало операции\"`, `time=\"2026-09-18T08:58:22.686Z\"`, `id=\"3061fa90-3646-434f-a919-cfe7c92ebafb\"`.\n- Завершение: `status=\"SUCCESS\"`, `messageTemplate=\"Успешно завершено\"`, `time=\"2026-09-18T08:58:22.972Z\"`, `id=\"dea7f429-7e43-4dd8-b829-30f4b47c13b7\"`.\n### Сценарии\n- Тест PPBP-3598: тип `СТ`, приоритет `Средний`, состояние `Готов к автоматизации`, результат теста и шагов `Успешен`; исполнитель `Nudiplodov Stepan Петрович`, дата `18.09.2026 14:16:19`. Постусловие 1 не заполнено.","h":"1luxlebr3b2","at":1794341797385}],"conflicts":[],"links":[],"human":true,"updatedAt":1794341797395,"kind":"kbblock","by":"local","ph":"1g9osucp848","bodyIsSynth":true}
-->
