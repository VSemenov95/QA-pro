# GET /api/monitoring-card/getInformationSystemsAndCheckpoints/{monitoringCardRowId} — получение списка информационных сис

> GET-метод API ТМБС, возвращающий по Id версии карточки мониторинга список информационных систем и их контрольных точек (с атрибутами, константами обогащения, сервисом и группами правил).

### Описание
- Наименование метода: «Получениесписка информационных систем и контрольных точек карточки мониторинга». (2-GET _api_monitoring-card_getInformationSystemsAndCheckpoints_{monitoringCardRowId})
- URL: /api/monitoring-card/getInformationSystemsAndCheckpoints/{monitoringCardRowId}; метод HTTP: GET. (2-GET _api_monitoring-card_getInformationSystemsAndCheckpoints_{monitoringCardRowId})
- Swagger: https://trmonbs-admin-service.ppmon.dev.sfera-t1.ru/swagger-ui/index.html#/MonitoringCardController/getInformationSystemsAndCheckpoints (2-GET _api_monitoring-card_getInformationSystemsAndCheckpoints_{monitoringCardRowId})
- История изменений: версия 1.0, автор @Perekin D.С., 17 мар. 2026, «Создание страницы», задача PPBP-1863 [Аналитика] ТМБС. Сервисы. Передача метрик из ТМБС в ЗСМ в привязке к сервисам с агрегирующим расчетом на строне ТМБС ч2. (2-GET _api_monitoring-card_getInformationSystemsAndCheckpoints_{monitoringCardRowId})
- Оглавление документа: Описание метода, История изменений, Входные параметры, Пример запроса, Выходные параметры, Пример ответа, Логика работы. Разделы «Пример запроса» и «Логика работы» в предоставленном фрагменте не содержат текста. (2-GET _api_monitoring-card_getInformationSystemsAndCheckpoints_{monitoringCardRowId})

### API и интеграции
- Способ авторизации: JWT (token) пользователя. (2-GET _api_monitoring-card_getInformationSystemsAndCheckpoints_{monitoringCardRowId})
- Входные параметры:
  - authorization: string, JWT (token) пользователя, header, обязательный (+).
  - monitoringCardRowId: int64, Id конкретной версии карточки мониторинга, header, обязательный (+), пример 7777. (2-GET _api_monitoring-card_getInformationSystemsAndCheckpoints_{monitoringCardRowId})
- Выходные параметры (все в response body; «+» обязательный, «-» необязательный):
  - id: int32, Идентификатор информационной системы (+).
  - externalId: string, Внешний идентификатор информационной системы (+).
  - name: string, Имя информационной системы (+).
  - description: string, Описание информационной системы (-).
  - checkpoints: array<object> (-); checkpoints.items: object, Контрольная точка (-):
    - id: int32, Идентификатор контрольной точки (-).
    - mcId: int64, ID карточки мониторинга (первичный ключ) (+).
    - infSystemId: int32, Идентификатор информационной системы (-); пример: infSystemId.
    - dataSourceRowId: int32, Идентификатор конкретной версии источника данных (-); пример: dataSourceRowId.
    - dataSourceId: int32, Идентификатор источника данных (-); пример: dataSourceId.
    - name: string, Имя контрольной точки (-).
    - status: string, Статус контрольной точки (+), пример DRAFT.
    - mandatory: boolean, Флаг обязательности контрольной точки (+), пример false.
    - monitoringObject: string, Общая информация КТ: Объект мониторинга (-).
    - processStep: string, Общая информация КТ: Шаг процесса (-).
    - monitoringDesc: string, Общая информация КТ: Что мониторим.
    - description: string, Общая информация КТ: Описание контрольной точки.
    - service: object: id (int32, Идентификатор сервиса), name (string, Наименование сервиса).
    - attributes: array<object>; items: object, Атрибут контрольной точки: id (int32, Идентификатор атрибута контрольной точки), name (string, Наименование атрибута), description (string, Описание атрибута), keyIdentifier (boolean, Флаг ключевого атрибута), technicalAttributeId (int32, Идентификатор технического аттрибута), identifierType (string, Тип атрибута).
    - enrichmentConstants: array<object>; items: object, Константа обогащения: id (int32, Идентификатор константы обогащения), name (string, Название константы обогащения), value (string, Значение константы обогащения).
    - isOffUt: boolean, Выключить ли user_transaction_time.
    - group: object: id (int32, Идентификатор группы), order (int32, Порядковый номер группы), logicalOperator (string, Логический оператор (И/ИЛИ)), rules (array<object>, Правила, входящие в группу; items: object: id (int32, Идентификатор правила), order (int32, Порядковый номер правила), technicalAttributeId (в документе «technicalAttribute» + «ttributeId») (int32, Идентификатор технического аттрибута), operatorCode (string, Код оператора), parameters (object, Параметры правила; items: string)), nestedGroups (array<any>, Вложенные группы правил (-); items: any, $ref на схему GroupDTO https://trmonbs-admin-service.ppmon.dev.sfera-t1.ru/v3/api-docs#/components/schemas/GroupDTO (-)).
    - type: string, Тип КТ (-); пример: TRANSACTIONAL.
    - dataSourceVersion: int32, Версия источника, которая связана с КТ (-). (2-GET _api_monitoring-card_getInformationSystemsAndCheckpoints_{monitoringCardRowId})

### Бизнес-правила и ограничения
- Значения по умолчанию в примере: status — DRAFT; mandatory — false; type — TRANSACTIONAL. (2-GET _api_monitoring-card_getInformationSystemsAndCheckpoints_{monitoringCardRowId})

### Сообщения и ошибки
- http-статус коды в ответе: 200. Обработка ошибок: 400, 403, 409, 423, 500. (2-GET _api_monitoring-card_getInformationSystemsAndCheckpoints_{monitoringCardRowId})

### Роли и права
- Роль: Администратор; авторизация: JWT (token) пользователя. (2-GET _api_monitoring-card_getInformationSystemsAndCheckpoints_{monitoringCardRowId})
