# GET /api/template/{templateId}/linked-computed-attributes — получение списка вычисляемых атрибутов, созданных из шаблона

> Метод GET /api/template/{templateId}/linked-computed-attributes возвращает администратору список вычисляемых атрибутов (с данными карточки мониторинга и бизнес-сервиса), созданных из указанного шаблона, кроме атрибутов в статусе TEMPLATE.

### Описание
- Наименование метода: «Получение списка вычисляемых атрибутов, созданных из шаблона». URL: /api/template/{templateId}/linked-computed-attributes. Метод HTTP: GET. Способ авторизации: JWT (token) пользователя. (GET _api_template_{templateId}_linked-computed-attributes-10)
- Ссылка на swagger: TBD. (GET _api_template_{templateId}_linked-computed-attributes-10)
- История изменений: версия 1.0, автор @Kalinina D.А., дата 02 июл. 2026, описание «Создание страницы», задача PPBP-2309 [SA] Аналитика по функционалу "Массовые операции над сущностями созданными из шаблона". (GET _api_template_{templateId}_linked-computed-attributes-10)

### Роли и права
- Роли: Администратор. (GET _api_template_{templateId}_linked-computed-attributes-10)

### API и интеграции
- Обработка ошибок: 400, 403, 404, 500. http-статус коды в ответе: 200. (GET _api_template_{templateId}_linked-computed-attributes-10)
- Входной параметр: № 1, templateId, int64, «Идентификатор шаблона», расположение: path, обязательный: «+», значение по умолчанию: «-», пример: 1851. (GET _api_template_{templateId}_linked-computed-attributes-10)
- Пример запроса: в документе не приведён (раздел пуст). (GET _api_template_{templateId}_linked-computed-attributes-10)
- Выходные параметры (все обязательные «+», по умолчанию «-»): 1) businessServiceId, int — Идентификатор бизнес-сервиса; 2) businessServiceCode, string — Код БС; 3) monitoringCardId, int — Идентификатор КМ; 4) monitoringCardRowId, int — Идентификатор версии КМ; 5) monitoringCardName, string — Название КМ; 6) monitoringCardStatus, string — Статус КМ; 7) entityRowId, int — Идентификатор вычисляемого атрибута; 8) entityName, string — Название вычисляемого атрибута; 9) entityStatus, string — Статус выч. атрибута; 10) manualIntervalOverride, boolean — Признак ручного изменения порогов критичности. (GET _api_template_{templateId}_linked-computed-attributes-10)
- Пример ответа (массив): {"businessServiceId":1234,"businessServiceCode":"BS001","monitoringCardId":1234,"monitoringCardRowId":424242,"monitoringCardName":"Карточка авторизации","monitoringCardStatus":"MONITORING","entityRowId":101,"entityName":"Время ответа","entityStatus":"MONITORING","manualIntervalOverride":true}; {"businessServiceId":2345,"businessServiceCode":"BS002","monitoringCardId":2345,"monitoringCardRowId":505050,"monitoringCardName":"Карточка мониторинга","monitoringCardStatus":"DRAFT","entityRowId":201,"entityName":"Время ответа","entityStatus":"DRAFT","manualIntervalOverride":false}. (GET _api_template_{templateId}_linked-computed-attributes-10)

### Сообщения и ошибки
- 400 — «Ошибка в запросе». (GET _api_template_{templateId}_linked-computed-attributes-10)
- 403 — «Недостаточно прав». (GET _api_template_{templateId}_linked-computed-attributes-10)
- 404 — «Файл не найден» (возвращается, если запись с таким templateId не найдена). (GET _api_template_{templateId}_linked-computed-attributes-10)
- 500 указан в перечне обработки ошибок, описание не приведено. Успешный ответ: 200 OK. (GET _api_template_{templateId}_linked-computed-attributes-10)

### Бизнес-правила и ограничения
- Выбираются записи таблицы computed_attribute, у которых template_id = templateId и status != TEMPLATE. (GET _api_template_{templateId}_linked-computed-attributes-10)
- Если карточка мониторинга имеет несколько версий (например, одна на мониторинге, другая в черновике), в ответе формируются две отдельные записи с одинаковым businessServiceCode, но разными monitoringCardRowId и статусами карточек. (GET _api_template_{templateId}_linked-computed-attributes-10)
- Сортировка по умолчанию: по businessServiceCode (по возрастанию), затем по monitoringCardRowId. (GET _api_template_{templateId}_linked-computed-attributes-10)

### Сценарии
- 1. Система отправляет запрос GET /api/template/{templateId}/linked-computed-attributes. 2. Система обращается к таблице template для проверки существования шаблона с templateId; [alt: запись не найдена] сервис возвращает ошибку 404. 3. Сервис обращается к таблице computed_attribute за записями с template_id = templateId и status != TEMPLATE. 4. Для каждого уникального monitoring_card_row_id сервис обращается к таблице monitoring_card за информацией о карточке. 5. Для каждой карточки сервис обращается к таблице business_service за кодом бизнес-сервиса. 6. Система формирует ответ, объединяя данные шагов 3, 4 и 5; [opt: несколько версий карточки] формируются две отдельные записи с одинаковым businessServiceCode, но разными monitoringCardRowId и статусами карточек. 7. Сортировка по businessServiceCode (по возрастанию), затем по monitoringCardRowId. 8. Сервис синхронно возвращает 200 OK. (GET _api_template_{templateId}_linked-computed-attributes-10)

### Открытые вопросы
- Ссылка на swagger: TBD. (GET _api_template_{templateId}_linked-computed-attributes-10)
- Пример запроса в документе отсутствует. (GET _api_template_{templateId}_linked-computed-attributes-10)
- Для кода 500 описание не приведено. (GET _api_template_{templateId}_linked-computed-attributes-10)
