# GET /api/monitoring-event/dict-code-deviation — получение списка справочных значений кодов отклонений для ручных событий

> GET-метод /api/monitoring-event/dict-code-deviation возвращает справочный список кодов отклонений (id и codeDeviation) для ручных событий мониторинга в продукте ТМБС.

### Описание
- URL: /api/monitoring-event/dict-code-deviation; метод HTTP: GET. (2-GET _api_monitoring-event_dict-code-deviation)
- Наименование метода: Получение списка справочных значений кодов отклонений для ручных событий мониторинга. (2-GET _api_monitoring-event_dict-code-deviation)
- Ссылка на swagger: https://trmonbs-admin-service.ppmon.test.sfera-t1.ru/swagger-ui/index.html#/MonitoringEventController (2-GET _api_monitoring-event_dict-code-deviation)
- История изменений: версия 1.0, автор @Perekin D.С., дата 19 июн. 2026, описание «Создание страницы», номер задачи PPBP-2225 [SA] ТМБС. Отправка отклонений в сторонние системы ч4. (2-GET _api_monitoring-event_dict-code-deviation)
- Оглавление документа: Описание метода, История изменений, Входные параметры, Пример запроса, Выходные параметры, Пример ответа, Логика работы. (2-GET _api_monitoring-event_dict-code-deviation)
- Раздел «Логика работы» присутствует в документе (страница 3), но содержимого во фрагменте нет. (2-GET _api_monitoring-event_dict-code-deviation)

### Поля и элементы
- Входной параметр authorization: тип string; описание «JWT (token) пользователя»; расположение header; обязательный «+»; значение по умолчанию «-»; пример «-». (2-GET _api_monitoring-event_dict-code-deviation)
- Выходные параметры (для всех: обязательный «-», значение по умолчанию «-»): (2-GET _api_monitoring-event_dict-code-deviation)
  - id: тип int4; «Идентификатор кода отклонения»; пример 1. (2-GET _api_monitoring-event_dict-code-deviation)
  - codeDeviation: тип string; «Код отклонения события мониторинга»; пример «ШВ-1234». (2-GET _api_monitoring-event_dict-code-deviation)

### API и интеграции
- Способ авторизации: JWT (token) пользователя. (2-GET _api_monitoring-event_dict-code-deviation)
- http-статус коды в ответе: 200. (2-GET _api_monitoring-event_dict-code-deviation)
- Обработка ошибок: 400, 403, 409, 423, 500. (2-GET _api_monitoring-event_dict-code-deviation)
- Раздел «Пример запроса» в документе пуст, указан только заголовок. (2-GET _api_monitoring-event_dict-code-deviation)
- Пример запроса/ответа: GET https://trmonbs-admin-service.ppmon.dev.sfera-t1.ru/api/monitoring-event/dict-code-deviation (2-GET _api_monitoring-event_dict-code-deviation)
- Пример ответа: [{"id": 1, "codeDeviation": "ШВ-1234"}, {"id": 2, "codeDeviation": "ГП-1234"}] (2-GET _api_monitoring-event_dict-code-deviation)

### Роли и права
- Роли: Администратор. (2-GET _api_monitoring-event_dict-code-deviation)
