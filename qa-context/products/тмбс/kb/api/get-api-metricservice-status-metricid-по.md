# GET /api/metricService/status/{metricId} — получение информации о статусах для метрики Сервиса

> GET-метод REST API ТМБС для получения статуса (код и текстовое значение) метрики Сервиса по её идентификатору, доступный пользователю с JWT и разрешением PPBP_METRIC_SERVICE_READ.

### Описание
- URL*: /api/metricService/status/{metricId}; метод HTTP*: GET; наименование метода*: Получение информации о статусах для метрики Сервиса; способ авторизации*: JWT (token) пользователя; ссылка на swagger: - (не указана). (6-GET _api_metricService_status_{metricId})
- История изменений: Версия 1.0, @Perekin D.С., 10 мар. 2026 — создание страницы, задача PPBP-1742 [Аналитика] ТМБС. Сервисы. Передача метрик из ТМБС в ЗСМ в привязке к сервисам с агрегирующим расчетом на строне ТМБС ч1. Версия 1/1, @perekin, 23 мар. 2026 — переименован атрибут "metricServiceId" в "metricService". Версия 1.2, @Perekin D.С., 10 апр. 2026 — добавлен раздел "Разрешения", задача PPBP-1905 [SA] ТМБС. Конфигурирование метрики сервиса. (6-GET _api_metricService_status_{metricId})

### Поля и элементы
- Входной параметр authorization: тип string; описание: JWT (token) пользователя; расположение: header; обязательный: +; значение по умолчанию: -; пример: -. (6-GET _api_metricService_status_{metricId})
- Входной параметр metricId: тип int64; описание: Идентификатор метрики Сервиса; расположение: header; обязательный: +; значение по умолчанию: -; пример: 1851. (6-GET _api_metricService_status_{metricId})
- Выходной параметр status: тип string; описание: Статус метрики; обязательный: +; значение по умолчанию: -. (6-GET _api_metricService_status_{metricId})
- Выходной параметр value: тип string; описание: Текстовое значение статуса метрики; обязательный: +; значение по умолчанию: -. (6-GET _api_metricService_status_{metricId})

### Бизнес-правила и ограничения
- Обработка ошибок*: 400, 403, 409, 423, 500. (6-GET _api_metricService_status_{metricId})
- http-статус коды в ответе: 200. (6-GET _api_metricService_status_{metricId})

### API и интеграции
- Пример запроса: раздел в документе не содержит текста (на странице 3 виден только обрывок «имер»). (6-GET _api_metricService_status_{metricId})
- Пример ответа для 'https://trmonbs-admin-service.ppmon.dev.sfera-t1.ru/api/metricService/status/1851': [{"status":"DISCONNECTED","value":"Отключено"}]. Ответ представлен массивом объектов со статусом и текстовым значением. (6-GET _api_metricService_status_{metricId})

### Роли и права
- Роли*: Администратор. (6-GET _api_metricService_status_{metricId})
- Раздел «Разрешение»: № 1 — разрешение PPBP_METRIC_SERVICE_READ, ссылка: «Метрика Сервиса». Раздел «Логика работы» содержит только подраздел «Разрешение» с этой таблицей. (6-GET _api_metricService_status_{metricId})

### Открытые вопросы
- Параметр metricId указан с расположением «header», хотя в URL он задан как path-параметр {metricId}. (6-GET _api_metricService_status_{metricId})
- Ссылка на swagger не указана. (6-GET _api_metricService_status_{metricId})
- Пример запроса в документе отсутствует. (6-GET _api_metricService_status_{metricId})

### Расхождения между документами
- Пример статуса: в описании выходных параметров — DRAFT («Черновик»), в примере ответа — DISCONNECTED («Отключено») (оба в 6-GET _api_metricService_status_{metricId}).
