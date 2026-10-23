# GET /api/metricService/getMetricHeaders/{serviceId} — получение списка основных параметров метрик Сервиса

> Метод GET /api/metricService/getMetricHeaders/{serviceId} возвращает список основных параметров метрик указанного Сервиса в ТМБС.

### Описание
- URL: /api/metricService/getMetricHeaders/{serviceId}; метод HTTP: GET; наименование метода: Получение списка основных параметров метрик Сервиса; ссылка на swagger: -. (6-GET _api_metricService_getMetricHeaders_{serviceId})
- Оглавление документа: Описание метода, История изменений, Входные параметры, Пример запроса, Выходные параметры, Пример ответа, Логика работы, Разрешения. (6-GET _api_metricService_getMetricHeaders_{serviceId})
- История изменений: Версия 1.0, @Perekin D.С., 10 мар. 2026, «Создание страницы», задача PPBP-1742 [Аналитика] ТМБС. Сервисы. Передача метрик из ТМБС в ЗСМ в привязке к сервисам с агрегирующим расчетом на строне ТМБС; Версия 1/1, @Perekin D.С., 23 мар. 2026, «изменен атрибут "metricServiceId" на "metricId"»; Версия 1.2, @Perekin D.С., 10 апр. 2026, «Добавлен раздел "Разрешения"», задача PPBP-1905 [SA] ТМБС. Конфигурирование метрики сервиса. (6-GET _api_metricService_getMetricHeaders_{serviceId})

### Поля и элементы
- Входные параметры:
  - authorization: string, JWT (token) пользователя, расположение header, обязательный (+), по умолчанию -, пример -.
  - serviceId: int64, Идентификатор Сервиса, расположение header, обязательный (+), по умолчанию -, пример 1851. (6-GET _api_metricService_getMetricHeaders_{serviceId})
- Выходные параметры:
  - id: int32, Идентификатор метрики Сервиса, обязательный (+), по умолчанию -, пример 1701.
  - metricId: int32, Сквозной идентификатор метрики Сервиса, обязательный (+), по умолчанию -, пример 1777.
  - name: string, Наименование метрики Сервиса, обязательный (+), по умолчанию -, пример «Наименование метрики».
  - description: string, Описание метрики сервиса, необязательный (-), по умолчанию -, пример «Здесь что то написать».
  - exportToKafka: boolean, Признак отправки метрики Сервиса в ЗСМ, обязательный (+), по умолчанию false, пример false.
  - labelMetric: string, Метки метрики Сервиса, необязательный (-), по умолчанию -, пример «Метка 1, метка 2, метка 3».
  - status: string, Статус метрики Срвиса, обязательный (+), по умолчанию DRAFT, пример DRAFT. (6-GET _api_metricService_getMetricHeaders_{serviceId})

### API и интеграции
- Способ авторизации: JWT (token) пользователя. (6-GET _api_metricService_getMetricHeaders_{serviceId})
- http-статус коды в ответе: 200. Обработка ошибок: 400, 403, 409, 423, 500. (6-GET _api_metricService_getMetricHeaders_{serviceId})
- Пример запроса: 'https://trmonbs-admin-service.ppmon.dev.sfera-t1.ru/api/metricService/getMetricHeaders/1851'. (6-GET _api_metricService_getMetricHeaders_{serviceId})
- Пример ответа: [{"id":1570,"metricId":262,"name":"Тестовая метрика cthdbcf для отладки","description":"qwerty123","exportToKafka":false,"labelMetric":"Метка 1, метка 2, метка 3","status":"DRAFT"}] — ответ представляет собой массив объектов. (6-GET _api_metricService_getMetricHeaders_{serviceId})

### Роли и права
- Роли: Администратор. (6-GET _api_metricService_getMetricHeaders_{serviceId})
- Разрешение № 1: PPBP_METRIC_SERVICE_HEADERS (ссылка: «Метрика Сервиса»). (6-GET _api_metricService_getMetricHeaders_{serviceId})

### Открытые вопросы
- Раздел «Логика работы» указан в оглавлении и заголовках, но не заполнен. (6-GET _api_metricService_getMetricHeaders_{serviceId})
- В примере описания метрики указан плейсхолдер «Здесь что то написать». (6-GET _api_metricService_getMetricHeaders_{serviceId})
- serviceId в таблице входных параметров указан с расположением header, хотя в URL передаётся как path-параметр {serviceId}. (6-GET _api_metricService_getMetricHeaders_{serviceId})
- Ссылка на swagger отсутствует. (6-GET _api_metricService_getMetricHeaders_{serviceId})
