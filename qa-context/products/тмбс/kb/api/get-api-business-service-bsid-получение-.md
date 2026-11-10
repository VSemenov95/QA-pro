# GET /api/business-service/{bsId} — получение информации о бизнес сервисе

> Получение информации о бизнес сервисе с проверкой сообщений начала и успешного завершения операции в Сфера.Аудит.

## Сфера.Аудит — история прохождений и тест-план.md

### Описание
- Проверяется получение информации о бизнес сервисе.
### Поля и элементы
- Параметр пути bsId — id бизнес сервиса; пример: 55555.
### Бизнес-правила и ограничения
- Предусловие: существует бизнес-сервис, известен его id.
### API и интеграции
- Запрос: GET {{baseURL}}/api/business-service/{bsId}.
- Ожидаемый ответ: «Статус Код 200 OK».
- В Kafka-топике audit-topic проверяются сообщения BUSINESS_SERVICE_GET_BUSINESS_SERVICE с code=PPBP_BUSINESS_SERVICE_GET_BUSINESS_SERVICE, status=START и status=SUCCESS.
- Атрибуты: infoSystemCode=PPBP, infoSystemId=2099; userIdentity.requestMetadata.method=GET, url=/api/business-service/55555; additionalAttributes.bsId=55555; businessOperation=Получение информации о бизнес сервисе; businessObject=Бизнес сервис.
- Для START: messageTemplate=Начало операции; для SUCCESS: messageTemplate=Успешно завершено.
### Сценарии
- Отправить запрос, проверить START, затем SUCCESS. Все три шага отмечены «Успешен».

<!-- qa-pro:kb
{"kind":"kbblock","id":"kbmwb4q8v2a8l7k","area":"api","parts":[{"docId":"import_audit_execution_history","docName":"Сфера.Аудит — история прохождений и тест-план.md","chunk":2,"sections":["PPBP-3594 — [BE] Проверка события BUSINESS_SERVICE_GET_BUSINESS_SERVICE"],"md":"### Описание\n- Проверяется получение информации о бизнес сервисе.\n### Поля и элементы\n- Параметр пути bsId — id бизнес сервиса; пример: 55555.\n### Бизнес-правила и ограничения\n- Предусловие: существует бизнес-сервис, известен его id.\n### API и интеграции\n- Запрос: GET {{baseURL}}/api/business-service/{bsId}.\n- Ожидаемый ответ: «Статус Код 200 OK».\n- В Kafka-топике audit-topic проверяются сообщения BUSINESS_SERVICE_GET_BUSINESS_SERVICE с code=PPBP_BUSINESS_SERVICE_GET_BUSINESS_SERVICE, status=START и status=SUCCESS.\n- Атрибуты: infoSystemCode=PPBP, infoSystemId=2099; userIdentity.requestMetadata.method=GET, url=/api/business-service/55555; additionalAttributes.bsId=55555; businessOperation=Получение информации о бизнес сервисе; businessObject=Бизнес сервис.\n- Для START: messageTemplate=Начало операции; для SUCCESS: messageTemplate=Успешно завершено.\n### Сценарии\n- Отправить запрос, проверить START, затем SUCCESS. Все три шага отмечены «Успешен».","h":"1gd960zks40","at":1794341715806}],"by":"local","updatedAt":1794341715816,"ph":"1q79kr671va","bodyIsSynth":false}
-->
