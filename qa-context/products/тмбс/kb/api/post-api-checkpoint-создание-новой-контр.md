# POST /api/checkpoint — создание новой контрольной точки

> POST /api/checkpoint — метод административного сервиса ТМБС для создания новой контрольной точки (КТ) карточки мониторинга с атрибутами, правилами фильтрации, привязкой к Сервису и источнику данных.

### Описание
- URL: /api/checkpoint; метод HTTP: POST; наименование метода: Создание новой контрольной точки; способ авторизации: JWT (token) пользователя (13-POST _api_checkpoint)
- Swagger: https://trmonbs-admin-service.ppmon.dev.sfera-t1.ru/swagger-ui/index.html#/CheckpointController/createCheckpoint (13-POST _api_checkpoint)
- Оглавление документа: Описание метода, История изменений, Входные параметры, Пример запроса, Выходные параметры, Пример ответа, Логика работы (13-POST _api_checkpoint)
- История изменений: 1.0, @Perekin D.С., 17 мар. 2026 — создание страницы, задача PPBP-1863 [Аналитика] ТМБС. Сервисы. Передача метрик из ТМБС в ЗСМ в привязке к сервисам с агрегирующим расчетом на строне ТМБС ч2; 1.1, 23 мар. 2026 — атрибут "ServiceId" изменён на объект "Service" в теле запроса; 1.2, 25 мая 2026 — дополнен атрибут "searchAttributes", задача PPBP-1955 [Аналитика] ТМБС. АПИ для поиска БС и id транзакции по заданным полям; 1.3, 26 авг. 2026 — доработка контракта в рамках принадлежности выч. атрибута к сервису (изменения подсвечены зелёным), задача PPBP-2528 [Аналитика] ТМБС. Подготовка артефактов для 4 варианта реализации (13-POST _api_checkpoint)

### Поля и элементы
Входные параметры (параметр, тип, описание, расположение, обязательность):
- authorization (string) — JWT (token) пользователя; header; обязательный (13-POST _api_checkpoint)
- id (int32) — Идентификатор контрольной точки; request body; необязательный (13-POST _api_checkpoint)
- mcId (int64) — ID карточки мониторинга (первичный ключ); request body; обязательный (13-POST _api_checkpoint)
- infSystemId (int32) — Идентификатор информационной системы; необязательный; в колонке значения/примера указано infSystemId (13-POST _api_checkpoint)
- dataSourceRowId (int32) — Идентификатор конкретной версии источника данных; необязательный; указано dataSourceRowId (13-POST _api_checkpoint)
- dataSourceId (int32) — Идентификатор источника данных; необязательный; указано dataSourceId (13-POST _api_checkpoint)
- name (string) — Имя контрольной точки; необязательный (13-POST _api_checkpoint)
- status (string) — Статус контрольной точки; обязательный; по умолчанию DRAFT; пример DRAFT (13-POST _api_checkpoint)
- mandatory (boolean) — Флаг обязательности контрольной точки; обязательный; по умолчанию false (13-POST _api_checkpoint)
- monitoringObject (string) — Общая информация КТ: Объект мониторинга; необязательный (13-POST _api_checkpoint)
- processStep (string) — Общая информация КТ: Шаг процесса; необязательный (13-POST _api_checkpoint)
- monitoringDesc (string) — Общая информация КТ: Что мониторим; необязательный (13-POST _api_checkpoint)
- description (string) — Общая информация КТ: Описание контрольной точки; необязательный (13-POST _api_checkpoint)
- service (object) — Сервис; необязательный: id (int32, Идентификатор сервиса, пример 8488), name (string, Наименование сервиса, пример «Сервис платежей»), code (string, Код сервиса, пример CI3000162) (13-POST _api_checkpoint)
- attributes (array<object>) — необязательный; элемент — Атрибут контрольной точки: id (int32); name (string); description (string); keyIdentifier (boolean, флаг ключевого атрибута); technicalAttributeId (int32, идентификатор технического аттрибута); identifierType (string, тип атрибута; обязательный; по умолчанию/пример TRANSACTIONAL); searchAttributeCode (string, код атрибута поиска); enrichmentConstants (array<object>, константы обогащения: id (int32), name (string, обязательный), value (string)) (13-POST _api_checkpoint)
- isOffUt (boolean) — Выключить ли user_transaction_time; по умолчанию false (13-POST _api_checkpoint)
- group (object) — необязательный: id (int32, идентификатор группы); order (int32, порядковый номер группы); logicalOperator (string, Логический оператор (И/ИЛИ)); rules (array<object>, правила группы: id (int32); order (int32, обязательный); technicalAttributeId (int32, обязательный); operatorCode (string, код оператора, обязательный); parameters (object, параметры правила; items string)); nestedGroups (array<any>, вложенные группы правил, ссылка $ref https://trmonbs-admin-service.ppmon.dev.sfera-t1.ru/v3/api-docs#/components/schemas/GroupDTO) (13-POST _api_checkpoint)
- type (string) — Тип КТ; необязательный (13-POST _api_checkpoint)
- dataSourceVersion (int32) — Версия источника, связанная с КТ; необязательный; в колонке по умолчанию/примера указано TRANSACTIONAL (13-POST _api_checkpoint)

Выходные параметры (response body, в документе «responce body»): состав и описания полей совпадают с входными, кроме authorization; обязательными отмечены mcId, status (по умолчанию/пример DRAFT), mandatory (по умолчанию false) (13-POST _api_checkpoint)

### API и интеграции
- POST /api/checkpoint; http-статус код в ответе: 200 (13-POST _api_checkpoint)
- Схема GroupDTO: https://trmonbs-admin-service.ppmon.dev.sfera-t1.ru/v3/api-docs#/components/schemas/GroupDTO (13-POST _api_checkpoint)

### Сообщения и ошибки
- Обработка ошибок: 400, 403, 409, 423, 500 (13-POST _api_checkpoint)

### Роли и права
- Роли: Администратор; авторизация: JWT (token) пользователя (13-POST _api_checkpoint)

### Открытые вопросы
- Разделы «Пример запроса», «Пример ответа» и «Логика работы» не содержат текста в извлечённом фрагменте (вероятно, изображения или блоки кода) (13-POST _api_checkpoint)
- Не приведён текст описаний ошибок (значение каждого кода) (13-POST _api_checkpoint)

<!-- qa-pro:kb
{"id":"f1f69yg1h20o","area":"api","parts":[{"docId":"import_audit_execution_history","docName":"Сфера.Аудит — история прохождений и тест-план.md","chunk":2,"sections":["PPBP-3596 — [BE] Проверка события CHECKPOINT_CREATE_CHECKPOINT"],"md":"### Бизнес-правила и ограничения\n- Предусловия: SFERA_AUDIT_ENABLED = true, SFERA_AUDIT_TRANSPORT_MODE=KAFKA, SFERA_AUDIT_KAFKA_TOPIC=audit-event.\n- Существует карточка мониторинга, известен mcId; пример: 209203.\n### API и интеграции\n- Запрос: POST {{baseURL}}/api/checkpoint.\n- Тело запроса из примера:\n```json\n{\"id\":null,\"mcId\":209203,\"name\":\"SelectiveEventsPart2 autotest firstCheckpointCard1 eknufuakbs\",\"tags\":[],\"type\":\"TRANSACTIONAL\",\"group\":null,\"status\":\"DRAFT\",\"isOffUtt\":false,\"mandatory\":false,\"attributes\":[{\"id\":null,\"name\":\"event_time\",\"description\":null,\"keyIdentifier\":false,\"identifierType\":\"TRANSACTIONAL\",\"searchAttributeCode\":null,\"technicalAttributeId\":1964338},{\"id\":null,\"name\":\"status\",\"description\":null,\"keyIdentifier\":false,\"identifierType\":\"TRANSACTIONAL\",\"searchAttributeCode\":null,\"technicalAttributeId\":1964339},{\"id\":null,\"name\":\"documentid\",\"description\":null,\"keyIdentifier\":true,\"identifierType\":\"TRANSACTIONAL\",\"searchAttributeCode\":null,\"technicalAttributeId\":1964341}],\"description\":null,\"infSystemId\":197259,\"processStep\":null,\"dataSourceId\":215382,\"monitoringDesc\":null,\"dataSourceRowId\":233748,\"monitoringObject\":null,\"dataSourceVersion\":1,\"enrichmentConstants\":[]}\n```\n- Ожидаемый ответ: «Статус Код 200ОК».\n- Проверяется наличие PPBP_CHECKPOINT_CREATE_CHECKPOINT в топике audit-event со status=START и status=SUCCESS.\n- Атрибуты обоих сообщений: infoSystemCode=PPBP, infoSystemId=2099; userIdentity.requestMetadata.method=POST, url=/api/checkpoint; additionalAttributes.checkpointDto содержит полное приведённое тело запроса, включая mcId=209203 и id=null.\n- businessOperation=Создание новой контрольной точки; businessObject=Контрольная точка; START: messageTemplate=Начало операции; SUCCESS: messageTemplate=Успешно завершено.\n### Сценарии\n- Отправить запрос, проверить START, затем SUCCESS. У всех трёх шагов результат «Нет результата», хотя весь тест обозначен «Успешен».\n- Постусловие: удалить созданную контрольную точку через DELETE {{baseURL}}/api/checkpoint/{checkpointId}.","h":"n2nvkfa2qu","at":1794341715867}],"conflicts":[],"links":[],"human":true,"updatedAt":1794341715873,"kind":"kbblock","by":"local","ph":"1i6v1o5gkvk","bodyIsSynth":true}
-->
