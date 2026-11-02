# GET /api/metric/{metricId} — получение информации о метрике

> Метод GET /api/metric/{metricId} возвращает информацию о метрике (включая сервис, расписание, единицу измерения и интервалы) по её идентификатору с авторизацией по JWT.

### Описание
- URL*: /api/metric/{metricId}; метод HTTP*: GET; наименование метода*: Получение информации о метрике. (GET _api_metric_{metricId}-4)
- Ссылка на swagger: https://trmonbs-admin-service.ppmon.dev.sfera-t1.ru/swagger-ui/index.html#/MetricController/getMetric (GET _api_metric_{metricId}-4)
- http-статус коды в ответе: 200. (GET _api_metric_{metricId}-4)
- Раздел «Логика работы» присутствует в документе (в оглавлении и на стр. 4), но текстового описания логики во фрагменте нет. (GET _api_metric_{metricId}-4)
- Версии: 1.0 — 04 мар. 2026, @Perekin D.С., создание страницы, задача PPBP-1721 [Аналитика] Передача метрик ЦС из Сфера. Транзакционный мониторинг в Сфера.Зонтичный мониторинг. 1.1 — 26 авг. 2026, @Perekin D.С., доработка контракта в рамках принадлежности выч. атрибута к сервису (изменения подсвечены зелёным цветом), задача PPBP-2528 [Аналитика] ТМБС. Подготовка артефактов для 4 варианта реализации. (GET _api_metric_{metricId}-4)

### Поля и элементы
**Входные параметры**
- authorization: string, JWT (token) пользователя, расположение: header, обязательный (+). (GET _api_metric_{metricId}-4)
- metricId: int32, идентификатор метрики, расположение: header, обязательный (+), пример: 1833. (GET _api_metric_{metricId}-4)

**Выходные параметры**
- id: int32, идентификатор метрики, обязательный (+). (GET _api_metric_{metricId}-4)
- metricId: int32, сквозной идентификатор метрики. (GET _api_metric_{metricId}-4)
- name: string, имя метрики. (GET _api_metric_{metricId}-4)
- description: string, описание метрики. (GET _api_metric_{metricId}-4)
- status: string, статус метрики; значение по умолчанию: DRAFT. (GET _api_metric_{metricId}-4)
- exportToKafka: boolean, признак отправки метрики в ЗСМ; по умолчанию: false. (GET _api_metric_{metricId}-4)
- mcId: int64, ID карточки мониторинга (первичный ключ). (GET _api_metric_{metricId}-4)
- calculationMethod: string, методика расчёта. (GET _api_metric_{metricId}-4)
- script: string, код метрики. (GET _api_metric_{metricId}-4)
- eventScript: string, код события мониторинга. (GET _api_metric_{metricId}-4)
- calculationPeriod: int32, период расчёта метрики. (GET _api_metric_{metricId}-4)
- calculationIntervalInMinutes: int32, частота расчёта метрики. (GET _api_metric_{metricId}-4)
- alertedObjectUrlTemplate: string, шаблон ссылки. (GET _api_metric_{metricId}-4)
- sendingEnabled: boolean, признак включённой отправки событий мониторинга. (GET _api_metric_{metricId}-4)
- metricSchedule: object (расписание). (GET _api_metric_{metricId}-4)
- unit: object (единица измерения). (GET _api_metric_{metricId}-4)
- service: object: id: int4, идентификатор сервиса; name: string, наименование сервиса; code: string, код сервиса. (GET _api_metric_{metricId}-4)
- intervals: array<object> (интервалы). (GET _api_metric_{metricId}-4)

### Бизнес-правила и ограничения
- Способ авторизации*: JWT (token) пользователя. (GET _api_metric_{metricId}-4)

### API и интеграции
- Пример запроса: GET https://sfera.ppcps-stable.dev.sfera-t1.ru/app/trmonbs/api/admin/api/metric/1833 (GET _api_metric_{metricId}-4)
- Пример ответа (200): id: 1571, metricId: 235, name: "stub", description: "1212121asdf", status: "MONITORING", mcId: 1851, calculationMethod: "", script: "-- п", eventScript: "-- ", calculationPeriod: 5, calculationIntervalInMinutes: 1, alertedObjectUrlTemplate: "", sendingEnabled: false. (GET _api_metric_{metricId}-4)
- metricSchedule: {type: "MINUTE", timeHour: null, timeMinute: null, weekDay: null, monthDay: null}. (GET _api_metric_{metricId}-4)
- unit: {id: 1, value: "Шт"}. (GET _api_metric_{metricId}-4)
- service: {id: 8488, name: "Сервис платежей", code: "CI3000162"}. (GET _api_metric_{metricId}-4)
- intervals: {id: 3950, active: true, minValue: null, maxValue: null, type: "NORMAL"}; {id: 3951, active: false, minValue: null, maxValue: null, type: "WARNING"}; {id: 3952, active: false, minValue: null, maxValue: null, type: "CRITICAL"}. (GET _api_metric_{metricId}-4)

### Сообщения и ошибки
- Обработка ошибок*: 400, 401, 403, 500. (GET _api_metric_{metricId}-4)
- Успешный ответ: 200. (GET _api_metric_{metricId}-4)

### Открытые вопросы
- Поле «Роли*» в описании метода указано, но значение во фрагменте отсутствует. (GET _api_metric_{metricId}-4)
- Текстовое описание раздела «Логика работы» во фрагменте отсутствует. (GET _api_metric_{metricId}-4)
