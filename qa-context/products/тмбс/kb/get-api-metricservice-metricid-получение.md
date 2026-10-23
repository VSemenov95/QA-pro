# GET /api/metricService/{metricId} — получение информации о метрике Сервиса

> Метод GET /api/metricService/{metricId} возвращает по JWT-авторизации полную информацию о метрике Сервиса: параметры, расчёт, расписание, единицу измерения и интервалы.

### Описание
- URL: /api/metricService/{metricId}; метод HTTP: GET; наименование: «Получение информации о метрике Сервиса»; авторизация: JWT (token) пользователя; ссылка на swagger: не указана («-»); http-статус в ответе: 200. (GET _api_metricService_{metricId}-9)
- Оглавление: Описание метода, История изменений, Входные параметры, Пример запроса, Выходные параметры, Пример ответа, Логика работы, Разрешения. (GET _api_metricService_{metricId}-9)
- История изменений: 1.0, @Perekin D.С., 10 мар. 2026, «Создание страницы», PPBP-1742 [Аналитика] ТМБС. Сервисы. Передача метрик из ТМБС в ЗСМ в привязке к сервисам с агрегирующим расчетом на строне ТМБС; 1.1, @Perekin D.С., дата не указана, «Измене атрибут service. изменения подсвечены зеленым цветом», PPBP-1863 [Аналитика] ТМБС. Сервисы. Передача метрик из ТМБС в ЗСМ в привязке к сервисам с агрегирующим расчетом на строне ТМБС ч2; 1.2, @Perekin D.С., 23 мар. 2026, «изменен атрибут "metricServiceId" на "metricId"»; 1.3, @Perekin D.С., 10 апр. 2026, «Добавлен раздел "Разрешения"», PPBP-1905 [SA] ТМБС. Конфигурирование метрики сервиса. (GET _api_metricService_{metricId}-9)

### Бизнес-правила и ограничения
- Раздел «Логика работы» присутствует как заголовок, содержимого нет. (GET _api_metricService_{metricId}-9)

### API и интеграции
**Входные параметры**
- authorization: string, «JWT (token) пользователя», header, обязательный (+).
- metricId: int64, «Идентификатор метрики Сервиса», header, обязательный (+), пример 1851.

**Пример запроса**: 'https://trmonbs-admin-service.ppmon.dev.sfera-t1.ru/api/metricService/1851'

**Выходные параметры** (+ обязательный, - необязательный)
- id: int32, «Идентификатор метрики Сервиса», +; пример 1701
- metricId: int32, «Сквозной идентификатор метрики Сервиса», +; пример 1777
- name: string, «Наименование метрики Сервиса», +; пример «Наименование метрики»
- description: string, «Описание метрики сервиса», -; пример «Здесь что то написать»
- exportToKafka: boolean, «Признак отправки метрики Сервиса в ЗСМ», +; пример false
- labelMetric: string, «Метки метрики Сервиса», -; пример «Метка 1, метка 2, метка 3»
- service: object, +
  - id: int32, «Идентификатор Сервиса», +; пример 1888
  - name: string, «Идентификатор Сервиса», +; пример «сервис 1»
- status: string, «Статус метрики Срвиса», +; пример DRAFT
- calculationMethod: string, «Методика расчета», -
- script: string, «Код метрики Сервиса», -; пример «select\n sipHash64(metric_id, metric_time) as metric_uuid»
- eventScript: string, «Код события мониторинга», -; пример «select\n sipHash64(metric_id, metric_time) as metric_uuid»
- calculationPeriod: string, «Период расчёта метрики», +; пример 5
- calculationIntervalInMinutes: string, «Частота расчёта метрики», +; пример 4
- alertedObjectUrlTemplate: string, «Шаблон ссылки», +; пример 123
- sendingEnabled: string, «Признак включённой отправки событий мониторинга», +; пример true
- metricSchedule: object, «Периодичность расчета метрики Сервиса»
  - type: string, «Тип периода расчета», +; пример WEEK
  - timeHour: int32, «час», -; пример 0
  - timeMinute: int32, «минута», -; пример 30
  - weekDay: int32, «День недели», -; пример 1
  - monthDay: int32, «День месяца», -; пример 1 (в примере ответа null)
- unit: object, «Единица измерения метрики Сервиса», +
  - id: int32, «Идентификатор единицы измерения метрики», +; пример 1
  - value: string, «Значение единицы измерения метрики», +; пример «шт»
- intervals: object, «Интервалы расчета метрики», +
  - items: object
    - id: int32, «Идентификатор интервала», +; пример 3947
    - active: boolean, «Признак состояния интервала», +; пример false
    - minValue: int64, «Минимальное значение интервала», -; пример 1
    - maxValue: int64, «Максимальное значение интервала», -; пример 2
    - type: string, «тип критичности интервала», +; пример NORMAL
(GET _api_metricService_{metricId}-9)

**Пример ответа**: id 1570; name «Тестовая метрика Сервиса»; description «qwerty123»; exportToKafka false; labelMetric «Метка 1, метка 2, метка 3»; status DRAFT; service {id "1888", name "Сервис"}; calculationMethod "121111112"; script «select\n sipHash64(metric_id, metric_time) as metric_uuid»; calculationPeriod 5; calculationIntervalInMinutes 3; alertedObjectUrlTemplate "123"; sendingEnabled true; metricSchedule {WEEK, 0, 30, weekDay 1, monthDay null}; unit {1, «Шт»}; intervals — массив из трёх: 3947 NORMAL, 3948 WARNING, 3949 CRITICAL (active false, minValue null, maxValue null). (GET _api_metricService_{metricId}-9)

### Сообщения и ошибки
- Обрабатываемые ошибки: 400, 403, 409, 423, 500; успешный ответ: 200. Тексты сообщений об ошибках не приведены. (GET _api_metricService_{metricId}-9)

### Роли и права
- Роль: Администратор; разрешение № 1 — PPBP_METRIC_SERVICE_READ (ссылка «Метрика Сервиса»). (GET _api_metricService_{metricId}-9)

### Открытые вопросы
- Раздел «Логика работы» пуст; ссылка на swagger не указана. (GET _api_metricService_{metricId}-9)

### Расхождения между документами
- Внутри документа: таблица выходных параметров указывает metricId, а пример ответа содержит metricServiceId (262), хотя в v1.2 атрибут переименован на metricId.
- Внутри документа: calculationPeriod, calculationIntervalInMinutes и sendingEnabled в таблице string, в примере ответа — числа и boolean.
- Внутри документа: service.name описан как «Идентификатор Сервиса», в примере содержит наименование («Сервис»).
