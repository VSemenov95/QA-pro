# GET /api/technical-attribute/name-replacement-rules — получение правил замены имён технических атрибутов

> Метод GET /api/technical-attribute/name-replacement-rules сервиса PPBP возвращает правила замены имён технических атрибутов (top-level-only и after-top-level), загружаемые из переменной окружения ATTR_NAME_REPLACEMENT_RULES, для автоматической генерации технических атрибутов.

### Описание
- Метод возвращает список правил замены имен технических атрибутов для автоматической генерации технических атрибутов. (GET _api_technical-attribute_name-replacement-rules-7)
- Правила загружаются из переменной окружения ATTR_NAME_REPLACEMENT_RULES. (GET _api_technical-attribute_name-replacement-rules-7)
- Правила разделены на две категории: top-level-only — применяются только к атрибутам верхнего уровня JSON; after-top-level — применяются к атрибутам вложенных уровней. (GET _api_technical-attribute_name-replacement-rules-7)
- История изменений: версия 1.0, автор @Kalinina D.А., дата 04 февр. 2026, описание «Создание страницы», номер задачи PPBP-1628 [Analytics][SA] Автоматическая генерация правил парсинга технических атрибутов в источнике данных. (GET _api_technical-attribute_name-replacement-rules-7)

### Поля и элементы
- Объект ответа NameReplacementRules (тип object), обязательные поля: top-level-only, after-top-level. (GET _api_technical-attribute_name-replacement-rules-7)
- top-level-only (array of ReplacementRule): правила замены, применяемые только к атрибутам верхнего уровня JSON. (GET _api_technical-attribute_name-replacement-rules-7)
- after-top-level (array of ReplacementRule): правила замены, применяемые к атрибутам вложенных уровней. (GET _api_technical-attribute_name-replacement-rules-7)
- ReplacementRule (object), обязательные поля: from, to. (GET _api_technical-attribute_name-replacement-rules-7)
- from (string): исходное имя атрибута для поиска (точное совпадение); пример: payload. (GET _api_technical-attribute_name-replacement-rules-7)
- to (string): целевое имя атрибута для замены; пример: object. (GET _api_technical-attribute_name-replacement-rules-7)

### Бизнес-правила и ограничения
- Если переменная окружения не задана, сервис возвращает объект с пустыми массивами after-top-level и top-level-only. (GET _api_technical-attribute_name-replacement-rules-7)
- Если переменная задана, сервис пытается выполнить парсинг JSON-строки. (GET _api_technical-attribute_name-replacement-rules-7)
- Если парсинг успешен, сервис валидирует структуру каждого правила, в том числе проверяет наличие обязательных полей. (GET _api_technical-attribute_name-replacement-rules-7)
- Поиск по from выполняется по точному совпадению. (GET _api_technical-attribute_name-replacement-rules-7)

### API и интеграции
- Метод: GET /api/technical-attribute/name-replacement-rules сервиса PPBP. (GET _api_technical-attribute_name-replacement-rules-7)
- OpenAPI 3.0.0, title: Technical Attribute Name Replacement Rules API, description: API для получения правил замены имён технических атрибутов при автоматической генерации, version 1.0.0; server url: /api (API сервер). (GET _api_technical-attribute_name-replacement-rules-7)
- tags: Technical Attribute; summary: Получить правила замены имён технических атрибутов; operationId: getTechnicalAttributeNameReplacementRules. (GET _api_technical-attribute_name-replacement-rules-7)
- Ответ HTTP 200: description «Список правил замены имён атрибутов» (в OpenAPI: «Успешный ответ с правилами замены»), объект NameReplacementRules, content application/json. ОР: (значение не приведено в документе). (GET _api_technical-attribute_name-replacement-rules-7)
- Ответ HTTP 500: description «Внутренняя ошибка сервера при обработке конфигурации» (в OpenAPI: «Внутренняя ошибка сервера»), объект ServerErrorDto. (GET _api_technical-attribute_name-replacement-rules-7)
- Пример ответа (контракт): {"after-top-level":[{"from":"transactionUid","to":"id"}],"top-level-only":[{"from":"payload","to":"object"}]} (GET _api_technical-attribute_name-replacement-rules-7)

### Сообщения и ошибки
- Ошибка 1: код 500, «Внутренняя ошибка сервера при обработке конфигурации правил замены», пример текста ошибки: «//Некорректный JSON». (GET _api_technical-attribute_name-replacement-rules-7)
- Ошибка 2: код 500, «Ошибка валидации правил замены», пример текста ошибки: «//Ошибка валидации». (GET _api_technical-attribute_name-replacement-rules-7)

### Сценарии
1. Система отправляет запрос к методу GET /api/technical-attribute/name-replacement-rules сервиса PPBP.
2. Сервис PPBP читает значение переменной окружения ATTR_NAME_REPLACEMENT_RULES.
3. Если переменная окружения не задана, сервис возвращает объект с пустыми массивами after-top-level и top-level-only.
4. Если переменная задана, сервис пытается выполнить парсинг JSON-строки.
5. Если парсинг успешен, сервис валидирует структуру каждого правила: (a) проверяет наличие обязательных полей.
6. Сервис формирует ответ запроса.
7. Сервис синхронно возвращает ответ на запрос системе с ответом 200 OK. (GET _api_technical-attribute_name-replacement-rules-7)
