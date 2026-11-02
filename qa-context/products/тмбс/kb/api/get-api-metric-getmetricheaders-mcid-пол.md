# GET /api/metric/getMetricHeaders/{mcId} — получение списка основных параметров метрик карточки мониторинга

> GET-метод ТМБС для получения списка основных параметров метрик карточки мониторинга по идентификатору карточки (mcId).

### Описание
- URL*: /api/metric/getMetricHeaders/{mcId}; метод HTTP*: GET; наименование метода*: Получение списка основных параметров метрик карточки мониторинга (3-GET _api_metric_getMetricHeaders_{mcId})
- Ссылка на swagger: https://trmonbs-admin-service.ppmon.dev.sfera-t1.ru/swagger-ui/index.html#/MetricController/getMetricHeaders (3-GET _api_metric_getMetricHeaders_{mcId})
- Оглавление документа: Описание метода, История изменений, Входные параметры, Пример запроса, Выходные параметры, Пример ответа, Логика работы. Раздел «Логика работы» в предоставленном фрагменте текста не содержит. (3-GET _api_metric_getMetricHeaders_{mcId})

### Поля и элементы
**Входные параметры**
- authorization: string, JWT (token) пользователя, header, обязательный (+), значение по умолчанию -, пример -. (3-GET _api_metric_getMetricHeaders_{mcId})
- mcId: int32, идентификатор карточки мониторинга, обязательный (+), по умолчанию -, пример 1833. (3-GET _api_metric_getMetricHeaders_{mcId})

**Выходные параметры**
- content: object. (3-GET _api_metric_getMetricHeaders_{mcId})
- id: int32, идентификатор метрики, обязательный (+), пример 1569. (3-GET _api_metric_getMetricHeaders_{mcId})
- metricId: int32, сквозной идентификатор метрики, пример 257. (3-GET _api_metric_getMetricHeaders_{mcId})
- name: string, имя метрики, пример Invalid metric. (3-GET _api_metric_getMetricHeaders_{mcId})
- description: string, описание метрики, пример s. (3-GET _api_metric_getMetricHeaders_{mcId})
- status: string, статус метрики, по умолчанию DRAFT. (3-GET _api_metric_getMetricHeaders_{mcId})
- exportToKafka: boolean, признак отправки метрики в ЗСМ, по умолчанию false, пример false. (3-GET _api_metric_getMetricHeaders_{mcId})
- service: object; service.id: int4, идентификатор сервиса, пример 8488; service.name: string, наименование сервиса, пример «Сервис платежей»; service.code: string, код сервиса, пример CI3000162. (3-GET _api_metric_getMetricHeaders_{mcId})

### Бизнес-правила и ограничения
- Авторизация: JWT (token) пользователя, передаётся в параметре authorization (header), обязателен. (3-GET _api_metric_getMetricHeaders_{mcId})
- Обязательные параметры запроса: authorization, mcId. Обязательное поле ответа: id. (3-GET _api_metric_getMetricHeaders_{mcId})
- Значения по умолчанию: status — DRAFT, exportToKafka — false. (3-GET _api_metric_getMetricHeaders_{mcId})

### API и интеграции
- Пример запроса: GET https://sfera.ppcps-stable.dev.sfera-t1.ru/app/trmonbs/api/admin/api/metric/getMetricHeaders/1833 (3-GET _api_metric_getMetricHeaders_{mcId})
- Пример ответа: массив объектов, например [{"id":1569,"metricId":257,"name":"Invalid metric","description":"s","status":"DISCONNECTED_MANUAL","exportToKafka":false,"service":{"id":8488,"name":"Сервис платежей","code":"CI3000162"}}] (3-GET _api_metric_getMetricHeaders_{mcId})

### Сообщения и ошибки
- Обрабатываемые ошибки: 400, 401, 403, 500. Успешный ответ: http-статус 200. (3-GET _api_metric_getMetricHeaders_{mcId})

### Роли и права
- Роли*: в документе значение не указано. (3-GET _api_metric_getMetricHeaders_{mcId})

### Сценарии
- История изменений: версия 1.0, @Perekin D.С., 04 мар. 2026 — создание страницы, задача PPBP-1721 [Аналитика] Передача метрик ЦС из Сфера. Транзакционный мониторинг в Сфера.Зонтичный мониторинг. (3-GET _api_metric_getMetricHeaders_{mcId})
- Версия 1.1, @Perekin D.С., 26 авг. 2026 — доработка контракта в рамках принадлежности выч. атрибута к сервису (изменения подсвечены зелёным), задача PPBP-2528 [Аналитика] ТМБС. Подготовка артефактов для 4 варианта реализации. (3-GET _api_metric_getMetricHeaders_{mcId})

### Открытые вопросы
- Роли, которым доступен метод, не указаны.
- Раздел «Логика работы» пуст.
- Список допустимых статусов метрики не приведён.
- Тип service.id указан как int4, остальные идентификаторы — int32.
- В документе указаны два разных хоста: sfera.ppcps-stable.dev.sfera-t1.ru (пример запроса) и trmonbs-admin-service.ppmon.dev.sfera-t1.ru (swagger). (3-GET _api_metric_getMetricHeaders_{mcId})

### Расхождения между документами
- Расположение mcId: в таблице входных параметров — header, в примере запроса — в пути URL (/1833).
- Структура ответа: в таблице выходных параметров есть поле content (object), в примере ответа — массив без обёртки content.
- Пример status: в таблице — DRAFT, в примере ответа — DISCONNECTED_MANUAL.
