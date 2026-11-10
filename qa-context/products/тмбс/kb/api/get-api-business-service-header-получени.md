# GET /api/business-service/header — получение списка бизнес сервисов

> Вызов списка бизнес сервисов проверяется на ответ 200 OK и сообщения аудита BUSINESS_SERVICE_GET_BUSINESS_SERVICES_HEADERS.

## Сфера.Аудит — история прохождений и тест-план.md

### Бизнес-правила и ограничения
- Предусловия: SFERA_AUDIT_ENABLED = true, SFERA_AUDIT_TRANSPORT_MODE=KAFKA, SFERA_AUDIT_KAFKA_TOPIC=audit-topic.
### API и интеграции
- Запрос: GET {{baseURL}}/api/business-service/header.
- Ожидаемый ответ: «Статус Код 200 OK».
- В топике audit-topic проверяются сообщения BUSINESS_SERVICE_GET_BUSINESS_SERVICES_HEADERS с code=PPBP_BUSINESS_SERVICE_GET_BUSINESS_SERVICES_HEADERS и status=START/SUCCESS.
- Атрибуты: infoSystemCode=PPBP, infoSystemId=2099; userIdentity.requestMetadata.method=GET, url=/api/business-service/header; additionalAttributes={}; businessOperation=Уравление бизнес сервисами; businessObject=Бизнес сервис.
- START: messageTemplate=Начало операции; SUCCESS: messageTemplate=Успешно завершено.
### Сценарии
- Отправить запрос, проверить START, затем SUCCESS. Все три шага отмечены «Успешен».

<!-- qa-pro:kb
{"kind":"kbblock","id":"kbmwb4q8w2b81jk","area":"api","parts":[{"docId":"import_audit_execution_history","docName":"Сфера.Аудит — история прохождений и тест-план.md","chunk":2,"sections":["PPBP-3595 — [BE] Проверка события BUSINESS_SERVICE_GET_BUSINESS_SERVICES_HEADERS"],"md":"### Бизнес-правила и ограничения\n- Предусловия: SFERA_AUDIT_ENABLED = true, SFERA_AUDIT_TRANSPORT_MODE=KAFKA, SFERA_AUDIT_KAFKA_TOPIC=audit-topic.\n### API и интеграции\n- Запрос: GET {{baseURL}}/api/business-service/header.\n- Ожидаемый ответ: «Статус Код 200 OK».\n- В топике audit-topic проверяются сообщения BUSINESS_SERVICE_GET_BUSINESS_SERVICES_HEADERS с code=PPBP_BUSINESS_SERVICE_GET_BUSINESS_SERVICES_HEADERS и status=START/SUCCESS.\n- Атрибуты: infoSystemCode=PPBP, infoSystemId=2099; userIdentity.requestMetadata.method=GET, url=/api/business-service/header; additionalAttributes={}; businessOperation=Уравление бизнес сервисами; businessObject=Бизнес сервис.\n- START: messageTemplate=Начало операции; SUCCESS: messageTemplate=Успешно завершено.\n### Сценарии\n- Отправить запрос, проверить START, затем SUCCESS. Все три шага отмечены «Успешен».","h":"hupqdpbd28","at":1794341715842}],"by":"local","updatedAt":1794341715850,"ph":"2d40cp4an8n","bodyIsSynth":false}
-->
