# API настроек по умолчанию коллекций метрик: подсказки (tooltip) и применение (apply)

> Административное API портала для загрузки и применения настроек по умолчанию коллекций метрик: обновление подсказок (tooltip) по выбранной таблице и применение настроек (apply) с необязательной проверкой обязательных атрибутов.

### Описание
- Раздел описывает методы POST/PUT /admin/metric-collection-default-settings/tooltip и POST/PUT /admin/metric-collection-default-settings/apply. Назначение методов в документе не описано, указаны только параметры и ответы. (portalbackend)
- Смежные методы: GET /admin/metric-collection-template/metric-collection-tool-tip (получение списка подсказок) и GET /admin/metric-collection-default-settings/download. (portalbackend)

### Поля и элементы
- tooltip, параметр table (в запросе, string, обязательный): METRIC_COLLECTION_TEMPLATE_ATTRIBUTE | METRIC_COLLECTION_ATTRIBUTE | DEFAULT_METRIC_COLLECTION_TEMPLATE_ATTRIBUTE. Описание: «Выберите таблицу для обновления.» (portalbackend)
- apply, параметр validateMissingRequiredAttributes (в запросе, boolean, необязательный). (portalbackend)
- Тело запроса POST tooltip и POST apply (multipart/form-data): file (string, обязательное, формат binary). (portalbackend)
- Элементы ответа GET metric-collection-tool-tip (массив): id (integer, необязательное, int64) — «Идентификатор подсказки создания коллекции метрик»; technicalName (string, необязательное) — «Техническое наименование подсказки»; text (string, необязательное) — «Текст подсказки». (portalbackend)

### API и интеграции
- POST /admin/metric-collection-default-settings/tooltip: параметр table (обязательный); тело multipart/form-data с file (обязательное); ответ 200 — OK. (portalbackend)
- PUT /admin/metric-collection-default-settings/tooltip: параметр table (обязательный); тело запроса не описано; ответ 200 — OK. (portalbackend)
- POST /admin/metric-collection-default-settings/apply: параметр validateMissingRequiredAttributes (необязательный); тело multipart/form-data с file (обязательное); ответ 200 — OK. (portalbackend)
- PUT /admin/metric-collection-default-settings/apply: параметр validateMissingRequiredAttributes (необязательный); тело запроса не описано; ответ 200 — OK. (portalbackend)
- GET /admin/metric-collection-template/metric-collection-tool-tip — «Получение списка подсказок»; ответ 200 — OK, массив элементов (id, technicalName, text). (portalbackend)
- GET /admin/metric-collection-default-settings/download: описания и параметров в документе нет; ответ 200 — OK (тело ответа не описано). (portalbackend)

### Открытые вопросы
- Не описано назначение методов tooltip и apply, формат содержимого загружаемого file, тело запросов PUT, поведение флага validateMissingRequiredAttributes, тело ответа download, коды ошибок и роли/права доступа. (portalbackend)

<!-- qa-pro:kb
{"kind":"kbblock","id":"kbmvr2ca1oxdcm0","parts":[{"docId":"dmvr2a59jh6h21","docName":"portalbackend.json","chunk":2,"sections":["POST/PUT /admin/metric-collection-default-settings/tooltip","POST/PUT /admin/metric-collection-default-settings/apply"],"md":"### API и интеграции\n- POST /admin/metric-collection-default-settings/tooltip\n  - Параметры: table (в запросе, string: METRIC_COLLECTION_TEMPLATE_ATTRIBUTE | METRIC_COLLECTION_ATTRIBUTE | DEFAULT_METRIC_COLLECTION_TEMPLATE_ATTRIBUTE, обязательный) — Выберите таблицу для обновления.\n  - Тело запроса (multipart/form-data): file (string, обязательное, формат binary).\n  - Ответы: 200 — OK.\n- PUT /admin/metric-collection-default-settings/tooltip\n  - Параметры: table (в запросе, string: METRIC_COLLECTION_TEMPLATE_ATTRIBUTE | METRIC_COLLECTION_ATTRIBUTE | DEFAULT_METRIC_COLLECTION_TEMPLATE_ATTRIBUTE, обязательный) — Выберите таблицу для обновления.\n  - Тело запроса не описано.\n  - Ответы: 200 — OK.\n- POST /admin/metric-collection-default-settings/apply\n  - Параметры: validateMissingRequiredAttributes (в запросе, boolean, необязательный).\n  - Тело запроса (multipart/form-data): file (string, обязательное, формат binary).\n  - Ответы: 200 — OK.\n- PUT /admin/metric-collection-default-settings/apply\n  - Параметры: validateMissingRequiredAttributes (в запросе, boolean, необязательный).\n  - Тело запроса не описано.\n  - Ответы: 200 — OK.\n- Назначение методов в документе не описано, указаны только параметры и ответы.","h":"14vowfwjon3","at":1793128381404},{"docId":"dmvr2kwae2c1xg","docName":"portalbackend.json","chunk":3,"sections":["GET /admin/metric-collection-template/metric-collection-tool-tip","GET /admin/metric-collection-default-settings/download"],"md":"### API и интеграции\n- **GET /admin/metric-collection-template/metric-collection-tool-tip** — Получение списка подсказок.\n  - Ответ 200 — OK, массив элементов:\n    - id (integer, необязательное, int64) — Идентификатор подсказки создания коллекции метрик\n    - technicalName (string, необязательное) — Техническое наименование подсказки\n    - text (string, необязательное) — Текст подсказки\n- **GET /admin/metric-collection-default-settings/download**\n  - Описания и параметров в документе нет.\n  - Ответ 200 — OK (тело ответа не описано).","h":"hdqohiivlu","at":1793129052252}],"by":"u_W5YRm3xP7Wk86vd57MKusA","updatedAt":1793129598623,"ph":"jpxikv0u9","conflicts":[],"links":["kbmvr2ca27957dy","kbmvr2bg96wzq9n","kbmvr2q0crp2k73","kbmvr2bg90pvmn7"],"synthAt":1793129581035,"synthHash":"jpxikv0u9","synthV":2,"big":0,"redo":[],"bodyIsSynth":true}
-->
