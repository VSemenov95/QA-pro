# GET /api/template/{templateId}/linked-metrics — получение списка метрик, созданных из шаблона

> Метод GET /api/template/{templateId}/linked-metrics возвращает администратору список метрик (с данными карточки мониторинга и бизнес-сервиса), созданных из указанного шаблона.

### Описание
- Метод возвращает список метрик, созданных из указанного шаблона. Наименование: «Получение списка метрик, созданных из шаблона». (GET _api_template_{templateId}_linked-metrics-10)
- URL: /api/template/{templateId}/linked-metrics; метод HTTP: GET; авторизация: JWT (token) пользователя; ссылка на swagger: TBD. (GET _api_template_{templateId}_linked-metrics-10)
- История изменений: версия 1.0, автор @Kalinina D.А., дата 02 июл. 2026, описание «Создание страницы», задача PPBP-2309 [SA] Аналитика по функционалу "Массовые операции над сущностями созданными из шаблона". (GET _api_template_{templateId}_linked-metrics-10)
- Оглавление: Описание метода, История изменений, Входные параметры, Пример запроса, Выходные параметры, Пример ответа, 400, 403, 404, Логика работы. Раздел «Пример запроса» пуст. (GET _api_template_{templateId}_linked-metrics-10)

### Роли и права
- Роль: Администратор. (GET _api_template_{templateId}_linked-metrics-10)

### API и интеграции
- Обработка ошибок: 400, 403, 404, 500; http-статус коды в ответе: 200. Ответ возвращается синхронно. (GET _api_template_{templateId}_linked-metrics-10)
- Входной параметр: templateId, int64, «Идентификатор шаблона», расположение path, обязательный «+», значение по умолчанию «-», пример 1851. (GET _api_template_{templateId}_linked-metrics-10)
- Выходные параметры (все обязательные «+», по умолчанию «-»): 1) businessServiceId, int, Идентификатор БС; 2) businessServiceCode, string, Код БС; 3) monitoringCardId, int, Идентификатор КМ; 4) monitoringCardRowId, int, Идентификатор версии КМ; 5) monitoringCardName, string, Название КМ; 6) monitoringCardStatus, string, Статус КМ; 7) entityRowId, int, Идентификатор метрики; 8) entityName, string, Название метрики; 9) entityStatus, string, Статус метрики; 10) manualIntervalOverride, boolean, Признак ручного изменения порогов критичности. (GET _api_template_{templateId}_linked-metrics-10)
- Пример ответа: массив объектов, напр. {"businessServiceId":1234,"businessServiceCode":"BS001","monitoringCardId":1234,"monitoringCardRowId":42,"monitoringCardName":"Карточка авторизации","monitoringCardStatus":"MONITORING","entityRowId":101,"entityName":"Время ответа","entityStatus":"MONITORING","manualIntervalOverride":true} и {"businessServiceId":2345,"businessServiceCode":"BS002","monitoringCardId":2345,"monitoringCardRowId":50,"monitoringCardName":"Карточка мониторинга","monitoringCardStatus":"DRAFT","entityRowId":201,"entityName":"Время ответа","entityStatus":"DRAFT","manualIntervalOverride":false}. (GET _api_template_{templateId}_linked-metrics-10)
- Используемые таблицы: template, metric, monitoring_card, business_service. (GET _api_template_{templateId}_linked-metrics-10)

### Сообщения и ошибки
- 400 — «Ошибка в запросе». (GET _api_template_{templateId}_linked-metrics-10)
- 403 — «Недостаточно прав». (GET _api_template_{templateId}_linked-metrics-10)
- 404 — «Файл не найден»; возвращается, если запись с переданным templateId не найдена в таблице template. (GET _api_template_{templateId}_linked-metrics-10)
- 500 указан в списке обработки ошибок, текст сообщения не приведён. (GET _api_template_{templateId}_linked-metrics-10)

### Бизнес-правила и ограничения
- Из таблицы metric выбираются все записи, у которых template_id = templateId и status != TEMPLATE. (GET _api_template_{templateId}_linked-metrics-10)
- Если у карточки мониторинга несколько версий (например, одна на мониторинге, другая в черновике), формируются две отдельные записи с одинаковым businessServiceCode, но разными monitoringCardRowId и статусами карточек. (GET _api_template_{templateId}_linked-metrics-10)
- Сортировка по умолчанию: по businessServiceCode (по возрастанию), затем по monitoringCardRowId. (GET _api_template_{templateId}_linked-metrics-10)

### Сценарии
- 1. Система отправляет запрос GET /api/template/{templateId}/linked-metrics для получения списка метрик, созданных из шаблона (в тексте документа указано «вычислительных атрибутов»). 2. Проверка существования шаблона с templateId в таблице template; если не найден — ошибка 404. 3. Из таблицы metric выбираются записи с template_id = templateId и status != TEMPLATE. 4. Для каждого уникального monitoring_card_row_id запрашивается информация из таблицы monitoring_card. 5. Для каждой карточки из таблицы business_service запрашивается код бизнес-сервиса. 6. Ответ формируется объединением данных шагов 3, 4 и 5; при нескольких версиях карточки — отдельные записи. 7. Сортировка по businessServiceCode (по возрастанию), затем по monitoringCardRowId. 8. Синхронный возврат ответа 200 OK. (GET _api_template_{templateId}_linked-metrics-10)

### Открытые вопросы
- Ссылка на swagger: TBD. (GET _api_template_{templateId}_linked-metrics-10)
- Пример запроса в документе пуст. (GET _api_template_{templateId}_linked-metrics-10)
- В шаге 1 логики упомянуты «вычислительные атрибуты», тогда как метод возвращает метрики. (GET _api_template_{templateId}_linked-metrics-10)
- Для кода 500 текст сообщения не указан; для 404 указан текст «Файл не найден». (GET _api_template_{templateId}_linked-metrics-10)
