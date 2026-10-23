# GET /api/admin-settings/monitoring-card/ — получение настроек для карточки мониторинга

> Метод GET /api/admin-settings/monitoring-card/ возвращает администратору настройки карточки мониторинга (признаки отправки отклонений, событий и метрик во внешние системы, частоту проверки отклонений).

### Описание
- Наименование метода: «Получение настроек для карточки мониторинга». URL: /api/admin-settings/monitoring-card/. Метод HTTP: GET. (GET  _api_admin-settings_monitoring-card_-7)
- Ссылка на swagger: отсутствует («-»). (GET  _api_admin-settings_monitoring-card_-7)
- Оглавление страницы: Описание метода, История изменений, Входные параметры, Пример запроса, Выходные параметры, Пример ответа, Логика работы. Раздел «Логика работы» в предоставленном фрагменте не содержит текста. (GET  _api_admin-settings_monitoring-card_-7)

### Поля и элементы
- Входной параметр: authorization — string, header, обязательный (+), описание «JWT (token) пользователя»; значение по умолчанию и пример не указаны. (GET  _api_admin-settings_monitoring-card_-7)
- Выходные параметры (все обязательные, «+»); ответ — массив объектов (в примере один элемент): (GET  _api_admin-settings_monitoring-card_-7)
  - id — int8 — ID карточки мониторинга.
  - cardId — int4 — Идентификатор связывающий все версии карточки мониторинга.
  - bsId — int4 — ИД Бизнес-сервиса.
  - name — string — Имя карточки мониторинга.
  - status — object — статус.
  - status.status — string — Статус КМ.
  - status.value — string — Текстовое значение статуса карточки мониторинга.
  - sendDeviation — boolean — Локальный признак отправки отклонений во внешние системы (в рамках КМ).
  - sendMonitoringEvents — boolean — Локальный признак отправки событий мониторинга во внешние системы (в рамках КМ).
  - sendMetric — boolean — Локальный признак отправки метрик БС во внешние системы (в рамках КМ).
  - checkIntervalMinutes — int4 — Частота проверки наличия отклонений; пример 1.

### Бизнес-правила и ограничения
- Способ авторизации: JWT (token) пользователя. (GET  _api_admin-settings_monitoring-card_-7)
- Значения по умолчанию: sendDeviation = false, sendMonitoringEvents = false, sendMetric = false, checkIntervalMinutes = 1. (GET  _api_admin-settings_monitoring-card_-7)

### API и интеграции
- Пример запроса (хост из примера): 'https://trmonbs-admin-service.ppmon.dev.sfera-t1.ru/api/admin-settings/ (в документе строка приведена не полностью). (GET  _api_admin-settings_monitoring-card_-7)
- Пример ответа: [{"id": 752, "cardId": 648, "bsId": 123 "name": "Карточка мониторинга бизнес-процессо", "status": {"status": "DRAFT", "value": "Черновик"}, "sendDeviation": false, "sendMonitoringEvents": false, "sendMetric": false, "checkIntervalMinutes": 1}] (GET  _api_admin-settings_monitoring-card_-7)

### Сообщения и ошибки
- Успешный http-статус код в ответе: 200. (GET  _api_admin-settings_monitoring-card_-7)
- Обработка ошибок: 400, 403, 409, 423, 500. (GET  _api_admin-settings_monitoring-card_-7)

### Роли и права
- Роли: Администратор. (GET  _api_admin-settings_monitoring-card_-7)

### Открытые вопросы
- В примере ответа после "bsId": 123 отсутствует запятая (в документе так). (GET  _api_admin-settings_monitoring-card_-7)
- В примере ответа имя карточки приведено как «Карточка мониторинга бизнес-процессо». (GET  _api_admin-settings_monitoring-card_-7)
- Пример запроса приведён не полностью, раздел «Логика работы» пуст. (GET  _api_admin-settings_monitoring-card_-7)
- Номер задачи в таблице истории изменений не указан. (GET  _api_admin-settings_monitoring-card_-7)

### История изменений
- 1.0, @Perekin D.С., 04 мая 2026 — Создание страницы. (GET  _api_admin-settings_monitoring-card_-7)
- 1.1, @Perekin D.С., 30 июл. 2026 — Добавлен bsId. (GET  _api_admin-settings_monitoring-card_-7)
