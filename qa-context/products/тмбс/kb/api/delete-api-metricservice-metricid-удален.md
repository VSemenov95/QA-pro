# DELETE /api/metricService/{metricId} — удаление метрики Сервиса

> DELETE-метод REST API ТМБС для удаления метрики Сервиса по её идентификатору; доступен пользователю с разрешением PPBP_METRIC_SERVICE_DELETE (роль Администратор).

### Описание
- URL: /api/metricService/{metricId}; метод HTTP: DELETE; наименование метода: Удаление метрики Сервиса. (DELETE _api_metricService_{metricId}-5)
- Ссылка на swagger: отсутствует («-»). (DELETE _api_metricService_{metricId}-5)
- История изменений: 1.0, @Perekin D.С., 10 мар. 2026 — Создание страницы. Задача PPBP-1742 [Аналитика] ТМБС. Сервисы. Передача метрик из ТМБС в ЗСМ в привязке к сервисам с агрегирующим расчетом на строне ТМБС ч1; 1.1, @Perekin D.С., 23 мар. 2026 — Переименован атрибут "metricServiceId" в "metricService"; 1.2, @Perekin D.С., 10 апр. 2026 — Добавлен раздел "Разрешения". Задача PPBP-1905 [SA] ТМБС. Конфигурирование метрики сервиса. (DELETE _api_metricService_{metricId}-5)

### Поля и элементы
- Входные параметры:
  - authorization: тип string; описание «JWT (token) пользователя»; расположение header; обязательный (+); значение по умолчанию отсутствует («-»); пример отсутствует («-»).
  - metricId: тип int64; описание «Идентификатор метрики Сервиса»; расположение header; обязательный (+); значение по умолчанию отсутствует («-»); пример 1851.
  (DELETE _api_metricService_{metricId}-5)
- Выходные параметры: Статус код от Сервиса. (DELETE _api_metricService_{metricId}-5)

### Бизнес-правила и ограничения
- Способ авторизации: JWT (token) пользователя. (DELETE _api_metricService_{metricId}-5)
- Раздел «Логика работы» в документе указан, но содержимого в имеющемся фрагменте не содержит. (DELETE _api_metricService_{metricId}-5)
- Раздел «Пример запроса» в имеющемся фрагменте содержимого не содержит. (DELETE _api_metricService_{metricId}-5)

### API и интеграции
- DELETE /api/metricService/{metricId}. (DELETE _api_metricService_{metricId}-5)
- http-статус коды в ответе: 200; пример ответа: 200 ок. (DELETE _api_metricService_{metricId}-5)
- Разрешение (раздел «Разрешение»): № 1 — PPBP_METRIC_SERVICE_DELETE, ссылка «Метрика Сервиса» 'https://trmonbs-admin-service.ppmon.dev.sfera-t1.ru/api/metricService/1851'. (DELETE _api_metricService_{metricId}-5)

### Сообщения и ошибки
- Обработка ошибок: 400, 403, 409, 423, 500. (DELETE _api_metricService_{metricId}-5)

### Роли и права
- Роли: Администратор. (DELETE _api_metricService_{metricId}-5)
- Необходимое разрешение: PPBP_METRIC_SERVICE_DELETE. (DELETE _api_metricService_{metricId}-5)
