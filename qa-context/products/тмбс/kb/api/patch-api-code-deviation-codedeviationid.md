# PATCH /api/code-deviation/{codeDeviationId} — изменение справочных значений кодов отклонений для ручных событий монитори

> Метод PATCH /api/code-deviation/{codeDeviationId} позволяет администратору изменить справочное значение кода отклонения для ручных событий мониторинга.

### Описание
- Наименование метода: «Изменение справочных значений кодов отклонений для ручных событий мониторинга». URL: /api/code-deviation/{codeDeviationId}, метод HTTP: PATCH. (7-PATCH _api_code-deviation_{codeDeviationId})
- Ссылка на swagger: https://trmonbs-admin-service.ppmon.test.sfera-t1.ru/swagger-ui/index.html#/MonitoringEventController (7-PATCH _api_code-deviation_{codeDeviationId})
- Оглавление документа: Описание метода, История изменений, Входные параметры, Пример запроса, Выходные параметры, Пример ответа, Логика работы. (7-PATCH _api_code-deviation_{codeDeviationId})

### Бизнес-правила и ограничения
- Способ авторизации: JWT (token) пользователя. (7-PATCH _api_code-deviation_{codeDeviationId})
- Версия 1.1 изменила тип данных для ИД кода отклонения и изменила нейминг атрибута 'codeDeviation' на 'code'. (7-PATCH _api_code-deviation_{codeDeviationId})
- История изменений: 1.0, автор @Perekin D.С., 08 июл. 2026 — создание страницы, задача PPBP-2280 [Аналитика] ТМБС. Отправка отклонений в сторонние системы по требованиям второй поставки; 1.1, автор @Perekin D.S., 27 июл. 2026 — изменён тип данных для ИД кода отклонения, изменён нейминг атрибута 'codeDeviation' на 'code'. (7-PATCH _api_code-deviation_{codeDeviationId})

### API и интеграции
- URL: /api/code-deviation/{codeDeviationId}, метод HTTP: PATCH. (7-PATCH _api_code-deviation_{codeDeviationId})
- http-статус коды в ответе: 200. Обработка ошибок: 400, 403, 409, 423, 500. (7-PATCH _api_code-deviation_{codeDeviationId})
- Входные параметры (значения по умолчанию для всех не заданы (-)):
  - authorization: string, JWT (token) пользователя, расположение header, обязательный (+).
  - codeDeviationId: string, «Идентификатор кода отклонения события мониторинга», расположение query, обязательный (+), пример c86cb707-b4cc-4d54-8d1d-e984648828ee (в документе пример разбит по строкам: c86cb707 / b4cc-4d5 / 8d1d- / e984648).
  - code: string, «Код отклонения события мониторинга», расположение body, обязательный (+), пример ГП-1234. (7-PATCH _api_code-deviation_{codeDeviationId})
- Пример запроса (body): {"code": "NEW_CODE"} (7-PATCH _api_code-deviation_{codeDeviationId})
- Выходные параметры (обязательность и значение по умолчанию не заданы):
  - id: string, «Идентификатор кода отклонения», пример c86cb707-b4cc-4d54-8d1d-e984648828ee.
  - code: string, «Код отклонения события мониторинга», пример ШВ-1234. (7-PATCH _api_code-deviation_{codeDeviationId})
- Пример ответа: {"id": "c86cb707-b4cc-4d54-8d1d-e984648828ee", "code": "NEW_CODE"} (7-PATCH _api_code-deviation_{codeDeviationId})

### Роли и права
- Роли: Администратор. Способ авторизации: JWT (token) пользователя. (7-PATCH _api_code-deviation_{codeDeviationId})

### Открытые вопросы
- Раздел «Логика работы» указан в оглавлении и на странице 3 как заголовок, но содержимого не имеет. (7-PATCH _api_code-deviation_{codeDeviationId})
- В описании параметра codeDeviationId указано расположение query, хотя идентификатор является частью URL-пути {codeDeviationId}. (7-PATCH _api_code-deviation_{codeDeviationId})
- Примеры значений кода отклонения в документе различаются (ГП-1234, ШВ-1234, NEW_CODE). (7-PATCH _api_code-deviation_{codeDeviationId})
