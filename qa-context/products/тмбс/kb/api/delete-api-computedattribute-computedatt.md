# DELETE /api/computedAttribute/{computedAttributeId} — удаление вычисляемого атрибута

> Удаление вычисляемого атрибута проверяется на ответ 200 ОК и наличие записи в audit_outbox.

## Сфера.Аудит — история прохождений и тест-план.md

### Бизнес-правила и ограничения
- В PPBP-3607 предусловия: SFERA_AUDIT_ENABLED = true, SFERA_AUDIT_TRANSPORT_MODE=KAFKA, SFERA_AUDIT_KAFKA_TOPIC=ppbp.audit-topic.
- Указано: существует шаблон вычисляемого атрибута, известен computedAttributeId, например, 2600.
### Сценарии
- Отправить DELETE {{baseURL}}/api/computedAttribute/{computedAttributeId}, где computedAttributeId=2600 — «id шаблона вычисляемого атрибута». Ожидается «Статус Код 200 ОК».
- Проверить запись в таблице audit_outbox; ожидается «Запись присутствует в таблице audit_outbox».
- Тест PPBP-3607 имеет статус «Успешен», дата 24.09.2026 13:24:01; у шагов указано «Нет результата».
- В PPBP-3606 этот метод используется в постусловии для удаления созданного вычисляемого атрибута.

<!-- qa-pro:kb
{"kind":"kbblock","id":"kbmwb4vhwrkb078","area":"api","parts":[{"docId":"import_audit_execution_history","docName":"Сфера.Аудит — история прохождений и тест-план.md","chunk":5,"sections":["PPBP-3606 — постусловие 1","PPBP-3607 — [BE] Проверка события COMPUTED_ATTRIBUTE_DELETE_COMPUTED_ATTRIBUTE"],"md":"### Бизнес-правила и ограничения\n- В PPBP-3607 предусловия: SFERA_AUDIT_ENABLED = true, SFERA_AUDIT_TRANSPORT_MODE=KAFKA, SFERA_AUDIT_KAFKA_TOPIC=ppbp.audit-topic.\n- Указано: существует шаблон вычисляемого атрибута, известен computedAttributeId, например, 2600.\n### Сценарии\n- Отправить DELETE {{baseURL}}/api/computedAttribute/{computedAttributeId}, где computedAttributeId=2600 — «id шаблона вычисляемого атрибута». Ожидается «Статус Код 200 ОК».\n- Проверить запись в таблице audit_outbox; ожидается «Запись присутствует в таблице audit_outbox».\n- Тест PPBP-3607 имеет статус «Успешен», дата 24.09.2026 13:24:01; у шагов указано «Нет результата».\n- В PPBP-3606 этот метод используется в постусловии для удаления созданного вычисляемого атрибута.","h":"24vykr2zcqo","at":1794341960812}],"by":"local","updatedAt":1794341960816,"ph":"2bz9efnnu2j","bodyIsSynth":false}
-->
