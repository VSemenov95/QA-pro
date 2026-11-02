# GET /api/dictionary/metricServiceStatuses/ — получение списка возможных статусов для метрик Сервиса

> GET-метод REST API «ТМБС», возвращающий справочник возможных статусов метрик Сервиса (пары status/value) для авторизованного по JWT пользователя.

### Описание
- Наименование метода: «Получение списка возможных статусов для метрик Сервиса». URL: /api/dictionary/metricServiceStatuses/; метод HTTP: GET. (2-GET _api_dictionary_metricServiceStatuses_)
- Ссылка на swagger: -. (2-GET _api_dictionary_metricServiceStatuses_)
- Оглавление документа: Описание метода, История изменений, Входные параметры, Пример запроса, Выходные параметры, Пример ответа, Логика работы. (2-GET _api_dictionary_metricServiceStatuses_)
- История изменений: версия 1.0, автор @Perekin D.С., дата 08 апр. 2026, описание «Создание страницы», номер задачи PPBP-1905 [SA] ТМБС. Конфигурирование метрики сервиса. (2-GET _api_dictionary_metricServiceStatuses_)

### Поля и элементы
- Входной параметр: authorization — тип string, описание «JWT (token) пользователя», расположение header, обязательный (+), значение по умолчанию -, пример не указан. (2-GET _api_dictionary_metricServiceStatuses_)
- Выходные параметры (элементы массива в ответе): status — string, «Статус метрики Сервиса», обязательный (+), по умолчанию -; value — string, «Текстовое значение статуса метрики Сервиса», обязательный (+), по умолчанию -. (2-GET _api_dictionary_metricServiceStatuses_)

### Бизнес-правила и ограничения
- Способ авторизации: JWT (token) пользователя. (2-GET _api_dictionary_metricServiceStatuses_)

### API и интеграции
- URL: /api/dictionary/metricServiceStatuses/; метод HTTP: GET. (2-GET _api_dictionary_metricServiceStatuses_)
- Пример запроса: 'https://trmonbs-admin-service.ppmon.dev.sfera-t1.ru/api/dictionary/metricServiceStatuses/ (2-GET _api_dictionary_metricServiceStatuses_)
- http-статус коды в ответе: 200. (2-GET _api_dictionary_metricServiceStatuses_)
- Пример ответа: [{"status":"MONITORING","value":"На мониторинге"}] (2-GET _api_dictionary_metricServiceStatuses_)

### Сообщения и ошибки
- Обработка ошибок: 400, 403, 404, 409, 423, 500. (2-GET _api_dictionary_metricServiceStatuses_)

### Роли и права
- Роли: Администратор. (2-GET _api_dictionary_metricServiceStatuses_)

### Открытые вопросы
- Раздел «Логика работы» присутствует в оглавлении и на странице, но содержимого не содержит. (2-GET _api_dictionary_metricServiceStatuses_)
- Ссылка на swagger не указана (-). (2-GET _api_dictionary_metricServiceStatuses_)
- Полный перечень возможных статусов в документе не приведён. (2-GET _api_dictionary_metricServiceStatuses_)

### Расхождения между документами
- Пример в таблице выходных параметров (status = DRAFT, value = «Черновик») отличается от примера ответа (status = MONITORING, value = «На мониторинге»). (2-GET _api_dictionary_metricServiceStatuses_)
