# POST /api/metricService/ — создание метрики Сервиса

> POST /api/metricService/ — метод создания метрики Сервиса в ТМБС (по JWT-токену пользователя с ролью Администратор) с расчётом, интервалами критичности и опциональной выгрузкой в ЗСМ.

### Описание
- URL: /api/metricService/; метод HTTP: POST; наименование метода: Создание метрики Сервиса; способ авторизации: JWT (token) пользователя; ссылка на swagger: - (POST _api_metricService_-7)
- История изменений: 1.0, @Perekin D.С., 10 мар. 2026 — создание страницы, задача PPBP-1742 [Аналитика] ТМБС. Сервисы. Передача метрик из ТМБС в ЗСМ в привязке к сервисам с агрегирующим расчетом на строне ТМБС ч1; 1.1, 23 мар. 2026 — переименован атрибут "metricServiceId" в "metricService", атрибут "ServiceId" заменён объектом "Service" в теле запроса; 1.2, 10 апр. 2026 — добавлен раздел "Разрешения", задача PPBP-1905 [SA] ТМБС. Конфигурирование метрики сервиса (POST _api_metricService_-7)

### Поля и элементы
- Входные параметры (авторизация — header, остальные — body). Обязательные (+): authorization (string, JWT); name (string, наименование метрики Сервиса); exportToKafka (boolean, признак отправки в ЗСМ, по умолчанию false); service (object) с id (int32, обязательный, пример 1888); status (string, по умолчанию DRAFT); calculationPeriod (string, период расчёта, пример 5); calculationIntervalInMinutes (string, частота расчёта); alertedObjectUrlTemplate (string, шаблон ссылки, пример 123); sendingEnabled (string, признак включённой отправки событий мониторинга, пример true); metricSchedule (object); unit (object); intervals (object) (POST _api_metricService_-7)
- Необязательные (-): description (string); labelMetric (string, метки, пример «Метка 1, метка 2, метка 3»); calculationMethod (string, методика расчета); script (string, код метрики Сервиса, пример «select\n sipHash64 (metric_id, metric_time) as metric_uuid»); eventScript (string, код события мониторинга) (POST _api_metricService_-7)
- metricSchedule (периодичность расчета): type (string, обязательный, пример WEEK); timeHour (int32, час, пример 0); timeMinute (int32, минута, пример 30); weekDay (int32, день недели, пример 1); monthDay (int32, день месяца, пример 1) — все кроме type необязательные (POST _api_metricService_-7)
- unit: id (int32, обязательный, пример 1); value (string, обязательный, пример «шт») (POST _api_metricService_-7)
- intervals: items (object, необязательный); id (int32, обязательный, пример 3947); active (boolean, обязательный, пример false); minValue (int64, необязательный, пример 1); maxValue (int64, необязательный, пример 2); type (string, тип критичности, обязательный, пример NORMAL) (POST _api_metricService_-7)

### API и интеграции
- Http-статус в ответе: 200. Обработка ошибок: 400, 403, 409, 423, 500 (POST _api_metricService_-7)
- Пример запроса (body): {"name":"Тестовая метрика Сервиса","description":"qwerty123","exportToKafka":false,"labelMetric":"Метка 1, метка 2, метка 3","status":"DRAFT","service":{"id":"1888"},"calculationMethod":"121111112","script":"select\n sipHash64(metric_id, metric_time) as metric_uuid","calculationPeriod":5,"calculationIntervalInMinutes":3,"alertedObjectUrlTemplate":"123","sendingEnabled":true,"metricSchedule":{"type":"WEEK","timeHour":0,"timeMinute":30,"weekDay":1,"monthDay":null},"unit":{"id":1,"value":"Шт"},"intervals":[{"id":3947,"active":false,"minValue":null,"maxValue":null,"type":"NORMAL"},{"id":3948,...,"type":"WARNING"},{"id":3949,...,"type":"CRITICAL"}]} (POST _api_metricService_-7)
- Выходные параметры: те же поля, что во входных, плюс id (int32, идентификатор метрики Сервиса) и metricId (int32, сквозной идентификатор), оба обязательные; service дополнительно содержит name (string, наименование сервиса, обязательный, пример «Сервис»); в выходных metricSchedule не помечен обязательным (POST _api_metricService_-7)
- Пример ответа: {"id":1570,"metricId":262,"name":"Тестовая метрика Сервиса","status":"DRAFT","service":{"id":"1888","name":"Сервис"},...} — остальные поля повторяют запрос; интервалы с id 3947, 3948, 3949 (NORMAL, WARNING, CRITICAL), active=false, minValue/maxValue=null (POST _api_metricService_-7)

### Роли и права
- Роли: Администратор (POST _api_metricService_-7)
- Разрешения: PPBP_METRIC_SERVICE_CREATE (ссылка: Метрика Сервиса); PPBP_METRIC_SERVICE_UPDATE_IN_STATUS_DRAFT (POST _api_metricService_-7)

### Открытые вопросы
- Раздел «Логика работы» не заполнен: нет описания поведения метода и условий для кодов ошибок 400, 403, 409, 423, 500 (POST _api_metricService_-7)
- Описание description в примере — заглушка «Здесь что то написать» (POST _api_metricService_-7)
- Типы calculationPeriod, calculationIntervalInMinutes и sendingEnabled указаны как string, но в примерах переданы числа (5, 3) и булево (true) (POST _api_metricService_-7)

### Расхождения между документами
- Примеры в таблицах и в JSON расходятся: calculationIntervalInMinutes 4 в таблице и 3 в JSON; unit.value «шт» и «Шт»; id/metricId в ответе 1701/1777 в таблице и 1570/262 в JSON (POST _api_metricService_-7)
