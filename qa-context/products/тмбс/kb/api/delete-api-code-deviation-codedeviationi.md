# DELETE /api/code-deviation/{codeDeviationId} — удаление кода отклонения для ручного события мониторинга

> Метод DELETE /api/code-deviation/{codeDeviationId} удаляет справочный код отклонения для ручного события мониторинга; доступен роли Администратор, авторизация по JWT.

### Описание
- Наименование метода: «Удаление кода отклонения для ручного события мониторинга». URL: /api/code-deviation/{codeDeviationId}. Метод HTTP: DELETE. (6-DELETE _api_code-deviation_{codeDeviationId})
- Ссылка на swagger: https://trmonbs-admin-service.ppmon.test.sfera-t1.ru/swagger-ui/index.html#/MonitoringEventController (6-DELETE _api_code-deviation_{codeDeviationId})
- Оглавление документа: Описание метода, История изменений, Входные параметры, Пример запроса, Выходные параметры, Пример ответа, Логика работы. (6-DELETE _api_code-deviation_{codeDeviationId})
- История изменений: версия 1.0, автор @Perekin D.С., 08 июл. 2026, «Создание страницы», задача PPBP-2280 [Аналитика] ТМБС. Отправка отклонений в сторонние системы по требованиям второй поставки. Версия 1.1, автор @Perekin D.S., 27 июл. 2026, «Изменен тип данных для ИД кода отклонения», «изменен нейминг атрибута 'codeDeviation' на 'code'». (6-DELETE _api_code-deviation_{codeDeviationId})

### Поля и элементы
- Входной параметр authorization: тип string; описание «JWT (token) пользователя»; расположение header; обязательный: +; значение по умолчанию: -; пример: -. (6-DELETE _api_code-deviation_{codeDeviationId})
- Входной параметр codeDeviationId: тип string; описание «Идентификатор кода отклонения события мониторинга»; расположение query; обязательный: +; значение по умолчанию: -; пример: c86cb707-b4cc-4d54-8d1d-e984648828ee (в документе значение разбито переносами строк, на странице 3 приведено как 86cb707-b4cc-4d54-8d1d-e984648828ee). (6-DELETE _api_code-deviation_{codeDeviationId})
- Выходные параметры: статус код. (6-DELETE _api_code-deviation_{codeDeviationId})

### Бизнес-правила и ограничения
- Способ авторизации: JWT (token) пользователя. (6-DELETE _api_code-deviation_{codeDeviationId})
- Раздел «Логика работы» содержит только пример запроса, описание логики в явном виде отсутствует. (6-DELETE _api_code-deviation_{codeDeviationId})

### API и интеграции
- Пример запроса: DELETE https://trmonbs-admin-service.ppmon.dev.sfera-t1.ru/api/code-deviation/{codeDeviationId} (6-DELETE _api_code-deviation_{codeDeviationId})
- http-статус код в ответе: 200; пример ответа: 200 ок. (6-DELETE _api_code-deviation_{codeDeviationId})

### Сообщения и ошибки
- Обработка ошибок: 400, 403, 409, 423, 500. (6-DELETE _api_code-deviation_{codeDeviationId})

### Роли и права
- Роли: Администратор. (6-DELETE _api_code-deviation_{codeDeviationId})

### Открытые вопросы
- Идентификатор в примере приведён в двух вариантах (c86cb707-… и 86cb707-…), единый корректный пример не определён. (6-DELETE _api_code-deviation_{codeDeviationId})
- Расположение codeDeviationId указано как query, хотя в URL он path-параметр; тексты ошибок и условия кодов 409 и 423 не описаны. (6-DELETE _api_code-deviation_{codeDeviationId})
- Хосты swagger (test) и примера запроса (dev) различаются. (6-DELETE _api_code-deviation_{codeDeviationId})
