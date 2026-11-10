# DELETE /api/checkpoint/{checkpointId} — удаление контрольной точки

> Удаление контрольной точки проверяется на ответ 200 ОК и сообщение аудита начала операции.

## Сфера.Аудит — история прохождений и тест-план.md

### Поля и элементы
- Параметр пути checkpointId — «Идентификатор контрольной точки»; пример: 364732.
### Бизнес-правила и ограничения
- Предусловия: SFERA_AUDIT_ENABLED = true, SFERA_AUDIT_TRANSPORT_MODE=KAFKA, SFERA_AUDIT_KAFKA_TOPIC=audit-topic.
- Существует контрольная точка, известен идентификатор checkpointId.
### API и интеграции
- Запрос: DELETE {{baseURL}}/api/checkpoint/{checkpointId}.
- Ожидаемый ответ: «Статус Код 200 ОК»; шаг отмечен «Успешен».
- Проверяется сообщение Kafka события CHECKPOINT_DELETE_CHECKPOINT с status=START, infoSystemCode=PPBP, infoSystemId=2099, userIdentity.requestMetadata.method=DELETE, userIdentity.requestMetadata.url=/api/checkpoint/364732, additionalAttributes.checkpointId=364732, businessOperation=Удаление контрольной точки, businessObject=Контрольная точка, messageTemplate=Начало операции.
- Фрагмент обрывается внутри шага проверки START; его ожидаемый результат и дальнейшие шаги не приведены.
### Сценарии
- Этот же эндпоинт используется для удаления созданной контрольной точки в постусловии PPBP-3596.

## Сфера.Аудит — история прохождений и тест-план.md

### API и интеграции
- Для DELETE `/api/checkpoint/364732` в топике `audit-topic` присутствуют сообщения события `CHECKPOINT_DELETE_CHECKPOINT`, поле `code` — `PPBP_CHECKPOINT_DELETE_CHECKPOINT`.
### Сообщения и ошибки
- Общие поля двух примеров: `version="1.0"`, `correlationId="da336db0-c24e-4cfc-a261-9f3cca15f4d3"`, `infoSystemCode="PPBP"`, `infoSystemId="2099"`, `additionalAttributes.checkpointId=364732`.
- `userIdentity.login="sa-ppbp"`, `userIdentity.sourceIPAddress="10.228.64.26"`; в `userIdentity.requestMetadata`: `ipNearbyNode="10.228.64.26"`, `ipRecipient="10.233.70.191"`, `sessionId=""`, `url="/api/checkpoint/364732"`, `method="DELETE"`.
- `podName="trmonbs-admin-service-8976b8659-xn92z"`, `namespace="ppbp"`, `eventCodeAlias=null`, `eventType="Удаление"`, `businessOperation="Удаление контрольной точки"`, `businessObject="Контрольная точка"`, `businessObjectExpression=null`, `title="'Удаление контрольной точки'"`, `crossSystemEvent=false`, `userType="ANY"`, `eventLevel="MEDIUM"`, `vendor="Sfera"`, `techSectionCode="hi"`, `starterVersion="4.2.3-java-17"`.
- Начало операции: `status="START"`, `messageTemplate="Начало операции"`, `time="2026-09-21T07:28:39.296Z"`, `id="fb8f6f40-37ee-4e5f-bcb3-c7724fcdc59f"`.
- Шаг 3 проверяет успешное завершение: `status="SUCCESS"`, `messageTemplate="Успешно завершено"`, `time="2026-09-21T07:28:39.584Z"`, `id="a427398a-d3ba-4006-b7cf-17f34e300c28"`.
### Сценарии
- Тест PPBP-3597: тип `СТ`, приоритет `Средний`, состояние `Готов к автоматизации`, результат `Успешен`; исполнитель `Nudiplodov Stepan Петрович`, дата `21.09.2026 10:37:52`. Постусловие 1 не заполнено.

<!-- qa-pro:kb
{"kind":"kbblock","id":"kbmwb4q8x813uc0","area":"api","parts":[{"docId":"import_audit_execution_history","docName":"Сфера.Аудит — история прохождений и тест-план.md","chunk":2,"sections":["PPBP-3596 — постусловие","PPBP-3597 — [BE] Проверка события CHECKPOINT_DELETE_CHECKPOINT"],"md":"### Поля и элементы\n- Параметр пути checkpointId — «Идентификатор контрольной точки»; пример: 364732.\n### Бизнес-правила и ограничения\n- Предусловия: SFERA_AUDIT_ENABLED = true, SFERA_AUDIT_TRANSPORT_MODE=KAFKA, SFERA_AUDIT_KAFKA_TOPIC=audit-topic.\n- Существует контрольная точка, известен идентификатор checkpointId.\n### API и интеграции\n- Запрос: DELETE {{baseURL}}/api/checkpoint/{checkpointId}.\n- Ожидаемый ответ: «Статус Код 200 ОК»; шаг отмечен «Успешен».\n- Проверяется сообщение Kafka события CHECKPOINT_DELETE_CHECKPOINT с status=START, infoSystemCode=PPBP, infoSystemId=2099, userIdentity.requestMetadata.method=DELETE, userIdentity.requestMetadata.url=/api/checkpoint/364732, additionalAttributes.checkpointId=364732, businessOperation=Удаление контрольной точки, businessObject=Контрольная точка, messageTemplate=Начало операции.\n- Фрагмент обрывается внутри шага проверки START; его ожидаемый результат и дальнейшие шаги не приведены.\n### Сценарии\n- Этот же эндпоинт используется для удаления созданной контрольной точки в постусловии PPBP-3596.","h":"2f1qtcuctbo","at":1794341715884},{"docId":"import_audit_execution_history","docName":"Сфера.Аудит — история прохождений и тест-план.md","chunk":3,"sections":["PPBP-3597 · [BE] Проверка события CHECKPOINT_DELETE_CHECKPOINT"],"md":"### API и интеграции\n- Для DELETE `/api/checkpoint/364732` в топике `audit-topic` присутствуют сообщения события `CHECKPOINT_DELETE_CHECKPOINT`, поле `code` — `PPBP_CHECKPOINT_DELETE_CHECKPOINT`.\n### Сообщения и ошибки\n- Общие поля двух примеров: `version=\"1.0\"`, `correlationId=\"da336db0-c24e-4cfc-a261-9f3cca15f4d3\"`, `infoSystemCode=\"PPBP\"`, `infoSystemId=\"2099\"`, `additionalAttributes.checkpointId=364732`.\n- `userIdentity.login=\"sa-ppbp\"`, `userIdentity.sourceIPAddress=\"10.228.64.26\"`; в `userIdentity.requestMetadata`: `ipNearbyNode=\"10.228.64.26\"`, `ipRecipient=\"10.233.70.191\"`, `sessionId=\"\"`, `url=\"/api/checkpoint/364732\"`, `method=\"DELETE\"`.\n- `podName=\"trmonbs-admin-service-8976b8659-xn92z\"`, `namespace=\"ppbp\"`, `eventCodeAlias=null`, `eventType=\"Удаление\"`, `businessOperation=\"Удаление контрольной точки\"`, `businessObject=\"Контрольная точка\"`, `businessObjectExpression=null`, `title=\"'Удаление контрольной точки'\"`, `crossSystemEvent=false`, `userType=\"ANY\"`, `eventLevel=\"MEDIUM\"`, `vendor=\"Sfera\"`, `techSectionCode=\"hi\"`, `starterVersion=\"4.2.3-java-17\"`.\n- Начало операции: `status=\"START\"`, `messageTemplate=\"Начало операции\"`, `time=\"2026-09-21T07:28:39.296Z\"`, `id=\"fb8f6f40-37ee-4e5f-bcb3-c7724fcdc59f\"`.\n- Шаг 3 проверяет успешное завершение: `status=\"SUCCESS\"`, `messageTemplate=\"Успешно завершено\"`, `time=\"2026-09-21T07:28:39.584Z\"`, `id=\"a427398a-d3ba-4006-b7cf-17f34e300c28\"`.\n### Сценарии\n- Тест PPBP-3597: тип `СТ`, приоритет `Средний`, состояние `Готов к автоматизации`, результат `Успешен`; исполнитель `Nudiplodov Stepan Петрович`, дата `21.09.2026 10:37:52`. Постусловие 1 не заполнено.","h":"1lt96qhyt6s","at":1794341797370}],"by":"local","updatedAt":1794341797377,"ph":"sg6jygvfux","conflicts":[],"links":[],"bodyIsSynth":false}
-->
