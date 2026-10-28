# API администрирования: текущий пользователь и справочники порогов

> Административный API портала: получение данных текущего пользователя и его ролей, а также справочников типов и операторов порогов.

### Описание
- Раздел описывает четыре GET-метода API администрирования: текущий пользователь, роли текущего пользователя, справочник типов порогов, справочник операторов порогов. (portalbackend)

### Поля и элементы
- GET /admin/users/current, ответ 200 — OK, поля (все необязательные): login (string) — Логин пользователя; name (string) — ФИО пользователя; id (integer, формат int64) — Идентификатор; email (string) — Электронная почта пользователя; phone (string) — Контактный номер телефона пользователя. (portalbackend)
- GET /admin/threshold-type, элементы массива (все необязательные): id (integer, формат int32) — Идентификатор; name (string) — Значение. (portalbackend)
- GET /admin/threshold-operator, элементы массива (все необязательные): id (integer, формат int32) — Идентификатор; symbol (string) — Значение; description (string) — Описание. (portalbackend)

### API и интеграции
- GET /admin/users/current — ответ 200 — OK. (portalbackend)
- GET /admin/users/current/roles — параметр: principal (в заголовке, string, необязательный); ответ 200 — OK (структура тела в документе не описана). (portalbackend)
- GET /admin/threshold-type — Получение списка; ответ 200 — OK. (portalbackend)
- GET /admin/threshold-operator — Получение списка; ответ 200 — OK. (portalbackend)

### Открытые вопросы
- Для GET /admin/users/current/roles не описана структура тела ответа 200. (portalbackend)
- Не описаны коды ошибок для всех четырёх методов. (portalbackend)

<!-- qa-pro:kb
{"kind":"kbblock","id":"kbmvr2q0cgp725s","parts":[{"docId":"dmvr2kwae2c1xg","docName":"portalbackend.json","chunk":2,"sections":["GET /admin/users/current","GET /admin/users/current/roles","GET /admin/threshold-type","GET /admin/threshold-operator"],"md":"### API и интеграции\n**GET /admin/users/current**\n- 200 — OK\n  - login (string, необязательное) — Логин пользователя\n  - name (string, необязательное) — ФИО пользователя\n  - id (integer, необязательное, формат int64) — Идентификатор\n  - email (string, необязательное) — Электронная почта пользователя\n  - phone (string, необязательное) — Контактный номер телефона пользователя\n\n**GET /admin/users/current/roles**\n- Параметры: principal (в заголовке, string, необязательный)\n- 200 — OK\n\n**GET /admin/threshold-type** — Получение списка\n- 200 — OK, элементы массива:\n  - id (integer, необязательное, формат int32) — Идентификатор\n  - name (string, необязательное) — Значение\n\n**GET /admin/threshold-operator** — Получение списка\n- 200 — OK, элементы массива:\n  - id (integer, необязательное, формат int32) — Идентификатор\n  - symbol (string, необязательное) — Значение\n  - description (string, необязательное) — Описание","h":"1nr8ej7fuoc","at":1793129022016}],"by":"u_W5YRm3xP7Wk86vd57MKusA","updatedAt":1793129524063,"ph":"20n9x8o7pft","conflicts":[],"links":["kbmvl1gfbl1ev84","kbmvl1hit1cx45d","kbmvl1eqfbu68a0","kbmvl1hm25zy3ej","kbmvr2op4bl0itg"],"synthAt":1793129519235,"synthHash":"20n9x8o7pft","synthV":2,"big":0,"redo":[],"bodyIsSynth":true}
-->
