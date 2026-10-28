# API системных настроек звуковых уведомлений

> API системных настроек звуковых уведомлений в Portal backend: получение списка имён файлов звуков и системных настроек (включение, пауза между сигналами, эскалация, звуки по уровням важности).

### Описание
- Раздел описывает два GET-эндпоинта административного API для системных звуковых уведомлений: список именования файлов и системные настройки. (portalbackend)

### API и интеграции
- GET /admin/notification-sound/storage/system — получение списка именования файлов для звуковых уведомлений. (portalbackend)
  - Ответ 200 — OK: names (массив из string, необязательное); count (integer, int32, необязательное). (portalbackend)
- GET /admin/notification-sound/settings/system — получение системных настроек. (portalbackend)
  - Ответ 200 — OK: enabled (boolean, обязательное); cooldownSeconds (integer, int32, обязательное); escalationOverride (boolean, обязательное); severities (object, необязательное). (portalbackend)
  - severities содержит уровни critical, warning, normal (каждый — object, необязательное). (portalbackend)
  - Поля каждого уровня: enabled (boolean, обязательное); source (string: system | custom, обязательное); systemSound (string, необязательное); customSound (string, необязательное). (portalbackend)

<!-- qa-pro:kb
{"kind":"kbblock","id":"kbmvr2op4l5hy7f","parts":[{"docId":"dmvr2kwae2c1xg","docName":"portalbackend.json","chunk":0,"sections":["GET /admin/notification-sound/storage/system","GET /admin/notification-sound/settings/system"],"md":"### API и интеграции\n#### GET /admin/notification-sound/storage/system\n- Получение списка именования файлов для звуковых уведомлений.\n- Ответ 200 — OK: names (массив из string, необязательное); count (integer, int32, необязательное).\n\n#### GET /admin/notification-sound/settings/system\n- Получение системных настроек.\n- Ответ 200 — OK:\n  - enabled (boolean, обязательное)\n  - cooldownSeconds (integer, int32, обязательное)\n  - escalationOverride (boolean, обязательное)\n  - severities (object, необязательное) с уровнями critical, warning, normal (каждый — object, необязательное), у каждого:\n    - enabled (boolean, обязательное)\n    - source (string: system | custom, обязательное)\n    - systemSound (string, необязательное)\n    - customSound (string, необязательное)","h":"axpih807kg","at":1793128960821}],"by":"u_W5YRm3xP7Wk86vd57MKusA","updatedAt":1793129071689,"ph":"f2o2w0ynaz","conflicts":[],"links":["kbmvl1hl8rsli99","kbmvr2ca1t4i43k","kbmvl1hm25zy3ej"],"synthAt":1793129067830,"synthHash":"f2o2w0ynaz","synthV":2,"big":0,"redo":[],"bodyIsSynth":true}
-->
