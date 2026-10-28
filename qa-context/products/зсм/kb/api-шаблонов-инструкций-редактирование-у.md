# API шаблонов инструкций (редактирование, удаление)

> REST API Portal backend для редактирования и удаления шаблона инструкции по идентификатору.

## portalbackend.json

### API и интеграции
- PUT /admin/instruction-template/{id} — Редактирование шаблона инструкции.
  - Параметры: id (в пути, string, обязательный).
  - Тело запроса (application/json), все поля необязательные:
    - name (string)
    - hint (string)
    - steps (object) со служебными полями JSON-узла: null, array, empty, missingNode, object, valueNode, container, embeddedValue, pojo, number, integralNumber, floatingPointNumber, short, int, long, float, double, bigDecimal, bigInteger, textual, boolean, binary, string (все boolean); nodeType (string: ARRAY | BINARY | BOOLEAN | MISSING | NULL | NUMBER | OBJECT | POJO | STRING)
  - Ответы: 200 — OK.
- DELETE /admin/instruction-template/{id} — Удаление шаблона инструкции.
  - Параметры: id (в пути, string, обязательный).
  - Ответы: 200 — OK.

<!-- qa-pro:kb
{"kind":"kbblock","id":"kbmvr2ca231lxyf","parts":[{"docId":"dmvr2a59jh6h21","docName":"portalbackend.json","chunk":2,"sections":["PUT /admin/instruction-template/{id}","DELETE /admin/instruction-template/{id}"],"md":"### API и интеграции\n- PUT /admin/instruction-template/{id} — Редактирование шаблона инструкции.\n  - Параметры: id (в пути, string, обязательный).\n  - Тело запроса (application/json), все поля необязательные:\n    - name (string)\n    - hint (string)\n    - steps (object) со служебными полями JSON-узла: null, array, empty, missingNode, object, valueNode, container, embeddedValue, pojo, number, integralNumber, floatingPointNumber, short, int, long, float, double, bigDecimal, bigInteger, textual, boolean, binary, string (все boolean); nodeType (string: ARRAY | BINARY | BOOLEAN | MISSING | NULL | NUMBER | OBJECT | POJO | STRING)\n  - Ответы: 200 — OK.\n- DELETE /admin/instruction-template/{id} — Удаление шаблона инструкции.\n  - Параметры: id (в пути, string, обязательный).\n  - Ответы: 200 — OK.","h":"2ai7vi0kluw","at":1793128381419}],"by":"u_W5YRm3xP7Wk86vd57MKusA","updatedAt":1793128381420,"ph":"kkwyareeci","bodyIsSynth":false}
-->
