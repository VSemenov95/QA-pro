# DELETE /api/monitoring-event/{eventId} — удаление события мониторинга

> Метод DELETE /api/monitoring-event/{eventId} удаляет событие мониторинга по его идентификатору и доступен роли «Администратор» по JWT пользователя.

### Описание
- Наименование метода: «Удаление события мониторинга». Метод удаляет событие мониторинга по идентификатору события (eventId). (2-DELETE _api_monitoring-event_{eventId})
- Оглавление страницы: Описание метода, История изменений, Входные параметры, Пример запроса, Выходные параметры, Пример ответа, Логика работы. (2-DELETE _api_monitoring-event_{eventId})
- История изменений: версия 1.0, автор @Kalinina D.А., дата 19 июн. 2026, описание «Создание страницы». Номер задачи не указан. (2-DELETE _api_monitoring-event_{eventId})

### Поля и элементы
- Входной параметр authorization: тип string, описание «JWT (token) пользователя», расположение header, обязательный (+). Значение по умолчанию и пример не указаны. (2-DELETE _api_monitoring-event_{eventId})
- Входной параметр eventId: тип int32, описание «Идентификатор события мониторинга», расположение path, обязательный (+), пример 123. Значение по умолчанию не указано. (2-DELETE _api_monitoring-event_{eventId})
- Выходные параметры: метод не возвращает данные в теле ответа; успешное выполнение подтверждается HTTP-статусом 200. (2-DELETE _api_monitoring-event_{eventId})

### API и интеграции
- URL: /api/monitoring-event/{eventId}; метод HTTP: DELETE. (2-DELETE _api_monitoring-event_{eventId})
- Способ авторизации: JWT (token) пользователя. (2-DELETE _api_monitoring-event_{eventId})
- Ссылка на swagger: https://trmonbs-admin-service.ppmon.test.sfera-t1.ru/swagger-ui/index.html#/MonitoringEventController (2-DELETE _api_monitoring-event_{eventId})
- Пример запроса: DELETE https://trmonbs-admin-service.ppmon.dev.sfera-t1.ru/api/monitoring-event/123 (2-DELETE _api_monitoring-event_{eventId})
- Пример ответа: 200 ОК. (2-DELETE _api_monitoring-event_{eventId})
- http-статус коды в ответе: 200. (2-DELETE _api_monitoring-event_{eventId})

### Сообщения и ошибки
- Обработка ошибок: 400, 403, 409, 423, 500. Описания и тексты ошибок не приведены. (2-DELETE _api_monitoring-event_{eventId})
- Успешный ответ: 200 ОК, тело ответа отсутствует. (2-DELETE _api_monitoring-event_{eventId})

### Роли и права
- Роли: Администратор. Способ авторизации: JWT (token) пользователя. (2-DELETE _api_monitoring-event_{eventId})

### Сценарии
- Клиент отправляет DELETE на /api/monitoring-event/{eventId} с заголовком authorization (JWT пользователя) и идентификатором события в path (например, 123); при успехе возвращается 200 ОК без тела ответа. (2-DELETE _api_monitoring-event_{eventId})

### Открытые вопросы
- Раздел «Логика работы» содержит только пример запроса, описание логики обработки не приведено. (2-DELETE _api_monitoring-event_{eventId})
- Расшифровка кодов ошибок 400, 403, 409, 423, 500 не приведена. (2-DELETE _api_monitoring-event_{eventId})
- В ссылке на swagger указан тестовый стенд (ppmon.test), а в примере запроса — dev-стенд (ppmon.dev). (2-DELETE _api_monitoring-event_{eventId})
