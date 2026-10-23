# GET /api/checkpoint/{checkPointId} — получение информации контрольной точки

> Метод GET /api/checkpoint/{checkPointId} возвращает администратору полную информацию о контрольной точке (КТ): общие данные, сервис, атрибуты, константы обогащения, группы правил и версию источника данных.

### Описание
- Наименование метода: Получение информации контрольной точки. (GET _api_checkpoint_{checkpointId}-8)
- Разделы документа: Описание метода, История изменений, Входные параметры, Пример запроса, Выходные параметры, Пример ответа, Логика работы. Содержимое разделов «Пример запроса», «Пример ответа» и «Логика работы» во фрагменте отсутствует (только заголовки). (GET _api_checkpoint_{checkpointId}-8)
- История изменений: v1.0, @Perekin D.С., 17 мар. 2026 — создание страницы, задача PPBP-1863 [Аналитика] ТМБС. Сервисы. Передача метрик из ТМБС в ЗСМ в привязке к сервисам с агрегирующим расчетом на строне ТМБС ч2; v1.1, 25 мая 2026 — дополнен атрибут "searchAttributes" (изменения подсвечены зеленым), задача PPBP-1955 [Аналитика] ТМБС. АПИ для поиска БС и id транзакции по заданным полям; v1.2, 26 авг. 2026 — доработка контракта в рамках принадлежности КТ к сервису (изменения подсвечены зеленым), задача PPBP-2528 [Аналитика] ТМБС. Подготовка артефактов для 4 варианта реализации. (GET _api_checkpoint_{checkpointId}-8)

### Поля и элементы
Входные параметры:
- authorization — string, JWT (token) пользователя, header, обязательный (+), по умолчанию «-». (GET _api_checkpoint_{checkpointId}-8)
- checkPointId — int32, внутренний идентификатор контрольной точки, расположение: header (в URL указан как {checkPointId}), обязательный (+), по умолчанию «-», пример 7777. (GET _api_checkpoint_{checkpointId}-8)

Выходные параметры (все в response body):
- id — int32, идентификатор контрольной точки. (GET _api_checkpoint_{checkpointId}-8)
- mcId — int64, ID карточки мониторинга (первичный ключ), обязательный. (GET _api_checkpoint_{checkpointId}-8)
- infSystemId — int32, идентификатор информационной системы (пример: infSystemId). (GET _api_checkpoint_{checkpointId}-8)
- dataSourceRowId — int32, идентификатор конкретной версии источника данных (пример: dataSourceRowId). (GET _api_checkpoint_{checkpointId}-8)
- dataSourceId — int32, идентификатор источника данных (пример: dataSourceId). (GET _api_checkpoint_{checkpointId}-8)
- name — string, имя контрольной точки. (GET _api_checkpoint_{checkpointId}-8)
- status — string, статус контрольной точки, обязательный, пример DRAFT. (GET _api_checkpoint_{checkpointId}-8)
- mandatory — boolean, флаг обязательности контрольной точки, обязательный, пример false. (GET _api_checkpoint_{checkpointId}-8)
- monitoringObject — string, общая информация КТ: Объект мониторинга. (GET _api_checkpoint_{checkpointId}-8)
- processStep — string, общая информация КТ: Шаг процесса. (GET _api_checkpoint_{checkpointId}-8)
- monitoringDesc — string, общая информация КТ: Что мониторим. (GET _api_checkpoint_{checkpointId}-8)
- description — string, общая информация КТ: Описание контрольной точки. (GET _api_checkpoint_{checkpointId}-8)
- service — object, Сервис: service.id (int32, идентификатор сервиса, пример 8488); service.name (string, наименование сервиса, пример «Сервис платежей»); service.code (string, код сервиса, пример CI3000162). (GET _api_checkpoint_{checkpointId}-8)
- attributes — array<object>, атрибуты КТ; элемент: id (int32, идентификатор атрибута КТ), name (string, наименование атрибута), description (string, описание атрибута), keyIdentifier (boolean, флаг ключевого атрибута), technicalAttributeId (int32, идентификатор технического аттрибута), identifierType (string, тип атрибута). (GET _api_checkpoint_{checkpointId}-8)
- searchAttributeCode — string, код атрибута поиска. (GET _api_checkpoint_{checkpointId}-8)
- enrichmentConstants — array<object>, константы обогащения; элемент: id (int32), name (string, название константы обогащения), value (string, значение константы обогащения). (GET _api_checkpoint_{checkpointId}-8)
- isOffUt — boolean, «Выключить ли user_transaction_time». (GET _api_checkpoint_{checkpointId}-8)
- group — object, группа правил: id (int32), order (int32, порядковый номер группы), logicalOperator (string, логический оператор И/ИЛИ), rules (array<object>, правила группы; элемент: id, order — порядковый номер правила, technicalAttributeId, operatorCode — код оператора, parameters — object, параметры правила, items: string), nestedGroups (array<any>, вложенные группы правил, $ref на GroupDTO). (GET _api_checkpoint_{checkpointId}-8)
- type — string, тип КТ, пример TRANSACTIONAL. (GET _api_checkpoint_{checkpointId}-8)
- dataSourceVersion — int32, версия источника, которая связана с КТ. (GET _api_checkpoint_{checkpointId}-8)
- Значения в колонках «Обязательный» и «Пример» для части строк в исходнике сдвинуты из-за разбора PDF; принадлежность полей к service, attributes, group восстановлена по структуре вложенности. (GET _api_checkpoint_{checkpointId}-8)

### Бизнес-правила и ограничения
- Статус КТ в примере: DRAFT. (GET _api_checkpoint_{checkpointId}-8)
- Тип КТ в примере: TRANSACTIONAL. (GET _api_checkpoint_{checkpointId}-8)
- isOffUt: «Выключить ли user_transaction_time». (GET _api_checkpoint_{checkpointId}-8)
- Логический оператор группы правил: И/ИЛИ. (GET _api_checkpoint_{checkpointId}-8)

### API и интеграции
- URL*: /api/checkpoint/{checkPointId}; Метод HTTP*: GET. (GET _api_checkpoint_{checkpointId}-8)
- Способ авторизации*: JWT (token) пользователя. (GET _api_checkpoint_{checkpointId}-8)
- Swagger: https://trmonbs-admin-service.ppmon.dev.sfera-t1.ru/swagger-ui/index.html#/CheckpointController/getCheckpoint (GET _api_checkpoint_{checkpointId}-8)
- Схема вложенных групп: $ref https://trmonbs-admin-service.ppmon.dev.sfera-t1.ru/v3/api-docs#/components/schemas/GroupDTO (GET _api_checkpoint_{checkpointId}-8)
- http-статус кода в ответе: 200. (GET _api_checkpoint_{checkpointId}-8)

### Сообщения и ошибки
- Обработка ошибок*: 400, 403, 409, 423, 500 (тексты сообщений не приведены). (GET _api_checkpoint_{checkpointId}-8)
- Успешный ответ: http-статус 200. (GET _api_checkpoint_{checkpointId}-8)

### Роли и права
- Роли*: Администратор. (GET _api_checkpoint_{checkpointId}-8)

### Открытые вопросы
- Разделы «Пример запроса», «Пример ответа» и «Логика работы» пусты.  (GET _api_checkpoint_{checkpointId}-8)
- checkPointId указан как header, хотя в URL это path-параметр {checkPointId}. (GET _api_checkpoint_{checkpointId}-8)
