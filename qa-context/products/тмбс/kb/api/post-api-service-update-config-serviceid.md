# POST /api/service/update-config/{serviceId} — обновление карточки Сервиса (обновление конфигураций метрик сервисов)

> Метод POST /api/service/update-config/{serviceId} обновляет карточку Сервиса: переводит связанные метрики сервиса из статуса «Подключено» в «На мониторинге», обновляет их конфигурации и возвращает данные Сервиса со связанными Бизнес-сервисами.

### Описание
- URL: /api/service/update-config/{serviceId}; метод HTTP: POST; наименование: Обновление карточки Сервиса (обновление конфигураций метрик сервисов). Ссылка на swagger: - (2-POST _api_service_update-config_{serviceId})
- История изменений: версия 1.0, автор @Perekin D.С., 10 апр. 2026, «Создание страницы», задача PPBP-1905 [SA] ТМБС. Конфигурирование метрики сервиса (2-POST _api_service_update-config_{serviceId})
- Оглавление страницы: Описание метода, История изменений, Входные параметры, Пример запроса, Выходные параметры, Пример ответа, Логика работы, Разрешение (2-POST _api_service_update-config_{serviceId})

### Поля и элементы
- Входные параметры:
  - authorization: string, JWT (token) пользователя, расположение header, обязательный (+), значение по умолчанию -, пример - (2-POST _api_service_update-config_{serviceId})
  - serviceId: int32, Идентификатор Сервиса, расположение header, обязательный (+), значение по умолчанию -, пример 1851 (2-POST _api_service_update-config_{serviceId})
- Выходные параметры (все, кроме content, обязательные (+), значение по умолчанию -):
  - content: object (обязательность и описание не указаны) (2-POST _api_service_update-config_{serviceId})
  - id: int32, Идентификатор Сервиса, пример 4206 (2-POST _api_service_update-config_{serviceId})
  - extServiceId: string, Внешний идентификатор Сервиса, пример CI3008588 (2-POST _api_service_update-config_{serviceId})
  - code: string, Код Сервиса, пример SRV-88 (2-POST _api_service_update-config_{serviceId})
  - name: string, Наименование сервиса, пример «Сервис» (2-POST _api_service_update-config_{serviceId})
  - businessService: object, Массив связанных Бизнес-сервисов (2-POST _api_service_update-config_{serviceId})
  - BSId: int32, Внутренний идентификатор БС, пример 3950 (2-POST _api_service_update-config_{serviceId})
  - name: string, Наименование БС, пример «Бизнес-сервис» (2-POST _api_service_update-config_{serviceId})
  - extBSId: string, Внешний идентификатор БС, пример CI0652123 (2-POST _api_service_update-config_{serviceId})

### Бизнес-правила и ограничения
- Логика работы: 1) получить в запросе "serviceId"; 2) по "serviceId" найти все связанные метрики сервиса (по "serviceId" в таблице metric_service); 3) поменять статусы для метрик сервиса, если статус "Подключено" -> "На мониторинге"; 4) обновить конфигурацию метрик Сервисов (2-POST _api_service_update-config_{serviceId})

### API и интеграции
- Способ авторизации: JWT (token) пользователя (2-POST _api_service_update-config_{serviceId})
- http-статус коды в ответе: 200 (2-POST _api_service_update-config_{serviceId})
- Пример запроса: обращение к 'https://trmonbs-admin-service.ppmon.dev.sfera-t1.ru/api/service/update-config/{serviceId}' (2-POST _api_service_update-config_{serviceId})
- Пример ответа: массив с объектом {"id": 4206, "extServiceId": "CI3008588", "сode": "SRV-88", "name": "Наименование Сервиса", "businessService": [{"BSId": 3950, "name": "Наименование Бизнес-сервиса 1", "extBSId": "CI0652123"}, {"BSId": 3951, "name": "Наименование Бизнес-сервиса 2", "extBSId": "CI0652123"}]} (2-POST _api_service_update-config_{serviceId})

### Сообщения и ошибки
- Обработка ошибок: 400, 403, 409, 423, 500 (тексты сообщений не указаны) (2-POST _api_service_update-config_{serviceId})

### Роли и права
- Роли: Администратор (2-POST _api_service_update-config_{serviceId})
- Разрешение № 1: PPBP_SERVICE_UPDATE (ссылка: «Сервис») (2-POST _api_service_update-config_{serviceId})

### Открытые вопросы
- В примере ответа ключ написан как "сode" (возможно, кириллическая «с»), в описании параметров — code; в примере ответа корневой элемент — массив, а в параметрах указан объект content (2-POST _api_service_update-config_{serviceId})
- Параметр serviceId указан как header, хотя присутствует в URL как path-параметр (2-POST _api_service_update-config_{serviceId})
