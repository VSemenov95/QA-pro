# PUT /api/metricService/ — изменение метрики Сервиса

> PUT /api/metricService/ — метод API для изменения метрики Сервиса (с передачей id, metricId, привязки к Сервису, расписания расчёта, единицы измерения и интервалов) от пользователя с JWT-авторизацией и ролью «Администратор».

### Описание
- URL*: /api/metricService/; метод HTTP*: PUT; наименование метода*: Изменение метрики Сервиса; способ авторизации*: JWT (token) пользователя; ссылка на swagger: - (PUT _api_metricService_-6)
- Звёздочкой (*) в таблице описания метода помечены обязательные характеристики описания метода. (PUT _api_metricService_-6)
- Оглавление документа: Описание метода, История изменений, Входные параметры, Пример запроса, Выходные параметры, Пример ответа, Логика работы, Разрешения. (PUT _api_metricService_-6)
- История изменений: 1.0, @Perekin D.С., 10 мар. 2026 — создание страницы, задача PPBP-1742 [Аналитика] ТМБС. Сервисы. Передача метрик из ТМБС в ЗСМ в привязке к сервисам с агрегирующим расчетом на строне ТМБС ч1; 1/1, @Perekin D.С., 23 мар. 2026 — переименован атрибут "metricServiceId" в "metricId", изменен атрибут "ServiceId" на объект "Service" в теле запроса, изменения подсвечены зелёным цветом; 1.3, @Perekin D.С., 10 апр. 2026 — добавлен раздел "Разрешения", задача PPBP-1905 [SA] ТМБС. Конфигурирование метрики сервиса. (PUT _api_metricService_-6)

### Поля и элементы
Входные параметры (параметр, тип, описание, расположение, обязательность, по умолчанию, пример):
- authorization, string, JWT (token) пользователя, header, обязательный +
- id, int32, Идентификатор метрики Сервиса, body, +, пример 1701
- metricId, int32, Сквозной идентификатор метрики Сервиса, body, +, 1777
- name, string, Наименование метрики Сервиса, body, +, «Наименование метрики»
- description, string, Описание метрики сервиса, body, -, «Здесь что то написать»
- exportToKafka, boolean, Признак отправки метрики Сервиса в ЗСМ, body, +, по умолчанию false, пример false
- labelMetric, string, Метки метрики Сервиса, body, -, «Метка 1, метка 2, метка 3»
- service, object, Сервис, body, +; service.id, int32, Идентификатор Сервиса, +, 1888
- status, string, Статус метрики Срвиса, body, +, по умолчанию DRAFT, пример DRAFT
- calculationMethod, string, Методика расчета, body, -
- script, string, Код метрики Сервиса, body, -, «select\n sipHash64(metric_id, metric_time) as metric_uuid»
- eventScript, string, Код события мониторинга, body, -, тот же пример
- calculationPeriod, string, Период расчёта метрики, body, +, 5
- calculationIntervalInMinutes, string, Частота расчёта метрики, body, +, 4
- alertedObjectUrlTemplate, string, Шаблон ссылки, body, +, 123
- sendingEnabled, string, Признак включённой отправки событий мониторинга, body, +, true
- metricSchedule, object, Периодичность расчета метрики Сервиса, body, +: type string «Тип периода расчета» + (WEEK); timeHour int32 «час» - (0); timeMinute int32 «минута» - (30); weekDay int32 «День недели» - (1); monthDay int32 «День месяца» - (1)
- unit, object, Единица измерения метрики Сервиса, body, +: id int32 + (1); value string + («шт»)
- intervals, object, Интервалы расчета метрики, body, +: items (object); id int32 «Идентификатор интервала» + (3947); active boolean «Признак состояния интервала» + (false); minValue int64 - (1); maxValue int64 - (2); type string «тип критичности интервала» + (NORMAL)
(PUT _api_metricService_-6)
Выходные параметры: id (1701), metricId (1777), name, description (-), exportToKafka (+, по умолчанию false), labelMetric (-), service {id 1888, name «Сервис»}, calculationMethod (-), script (-), eventScript (-), calculationPeriod (5), calculationIntervalInMinutes (4), alertedObjectUrlTemplate (123), sendingEnabled (true), metricSchedule {type WEEK, timeHour 0, timeMinute 30, weekDay 1, monthDay}, unit {id 1, value «шт»}, intervals {items; id 3947; active false; minValue 1; maxValue 2; type NORMAL} — типы и описания те же, что во входных. (PUT _api_metricService_-6)
- В выходных параметрах поле status в таблице не приведено, но присутствует в примере ответа ("status": "DRAFT"). (PUT _api_metricService_-6)

### Бизнес-правила и ограничения
- Раздел «Логика работы» содержит только заголовок; описания логики нет. (PUT _api_metricService_-6)
- Типы критичности интервалов: NORMAL, WARNING, CRITICAL; в примерах id интервалов 3947, 3948, 3949. (PUT _api_metricService_-6)

### API и интеграции
- PUT /api/metricService/, авторизация JWT (token) в заголовке authorization. (PUT _api_metricService_-6)
- Пример запроса: {"id":1570,"metricId":262,"name":"Тестовая метрика Сервиса","description":"qwerty123","exportToKafka":false,"labelMetric":"Метка 1, метка 2, метка 3","status":"DRAFT","service":{"id":"1888"},"calculationMethod":"121111112","script":"select\n sipHash64(metric_id, metric_time) as metric_uuid","calculationPeriod":5,"calculationIntervalInMinutes":3,"alertedObjectUrlTemplate":"123","sendingEnabled":true,"metricSchedule":{"type":"WEEK","timeHour":0,"timeMinute":30,"weekDay":1,"monthDay":null},"unit":{"id":1,"value":"Шт"},"intervals":[{"id":3947,"active":false,"minValue":null,"maxValue":null,"type":"NORMAL"},{"id":3948,...,"type":"WARNING"},{"id":3949,...,"type":"CRITICAL"}]} (PUT _api_metricService_-6)
- Пример ответа: тот же JSON, но "id":1700 и "service":{"id":"1888","name":"Сервис"}. (PUT _api_metricService_-6)

### Сообщения и ошибки
- Обработка ошибок*: 400, 403, 409, 423, 500; http-статус в ответе: 200. (PUT _api_metricService_-6)

### Роли и права
- Роли*: Администратор. (PUT _api_metricService_-6)
- Разрешения (все со ссылкой «Метрика Сервиса»): PPBP_METRIC_SERVICE_UPDATE_IN_STATUS_DRAFT; PPBP_METRIC_SERVICE_STATUS_CHANGE_FROM_DRAFT_TO_CONNECTED; ..._FROM_DRAFT_TO_DISCONNECTED_MANUAL; ..._FROM_CONNECTED_TO_DRAFT; ..._FROM_CONNECTED_TO_DISCONNECTED_MANUAL; ..._FROM_CONNECTED_TO_MONITORING; ..._FROM_MONITORING_TO_DISCONNECTED_MANUAL; PPBP_METRIC _STATUS_CHANGE_FROM_MONITORING_TO_DRAFT_SERVICE; PPBP_METRIC_SERVICE_STATUS_CHANGE_FROM_DISCONNECTED_MANUAL_TO_DRAFT; ..._FROM_DISCONNECTED_MANUAL_TO_CONNECTED. (PUT _api_metricService_-6)

### Открытые вопросы
- Раздел «Логика работы» не заполнен. (PUT _api_metricService_-6)
- Пример запроса: id 1570 и «Шт», таблица: 1701 и «шт»; в ответе id 1700 при запросе с id 1570. (PUT _api_metricService_-6)
- calculationPeriod, calculationIntervalInMinutes, sendingEnabled — string в таблицах, в JSON числа и boolean. (PUT _api_metricService_-6)
- service.id в запросе строкой "1888", в таблице int32. (PUT _api_metricService_-6)
