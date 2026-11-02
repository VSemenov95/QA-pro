# GET /api/functions/messageFunctions — получение списка функций для преобразования сообщений

> GET /api/functions/messageFunctions — метод админ-сервиса ТМБС, возвращающий список функций для преобразования сообщений (с категоризацией функций для конструктора технических атрибутов в источнике данных).

### Описание
- Наименование метода: «Получение списка функций для преобразования сообщений». URL: /api/functions/messageFunctions; метод HTTP: GET. (GET _api_functions_messageFunctions-5)
- Способ авторизации: JWT (token) пользователя. (GET _api_functions_messageFunctions-5)
- Ссылка на swagger: https://trmonbs-admin-service.ppmon.dev.sfera-t1.ru/swagger-ui/index.html#/FunctionsController/getMessageFunctions (GET _api_functions_messageFunctions-5)
- Доработка (версия 2.0) нужна для категоризации функций на фронте, в рамках «Конструктора создания технических атрибутов в источнике данных». (GET _api_functions_messageFunctions-5)
- История изменений: 1.0, @Perekin D.С., 03 февр. 2026: создание страницы; задача PPBP-1629 [Analytics][SA] Доработки конструктора создания технических атрибутов в источники данных. 2.0, @Perekin D.С., 03 февр. 2026: дополнены изменения в раздел 8 «Логика работы» п. 8.1 (доработка для конструктора создания технических атрибутов в источнике данных); дополнен раздел 5 «Выходные параметры» новым объектом данных "category" в рамках реализации требований по категоризации функций (изменения выделены зелёным цветом); задача PPBP-1629. (GET _api_functions_messageFunctions-5)

### Роли и права
- Роли: Администратор. Авторизация по JWT (token) пользователя. (GET _api_functions_messageFunctions-5)
- Сообщение 403: «Нет прав для доступа к данным метода»; сценарий «Доступ запрещен (согласно ролевой модели)». (GET _api_functions_messageFunctions-5)

### API и интеграции
- Обработка ошибок: 400, 403, 409, 423, 500. http-статус коды в ответе: 200. (GET _api_functions_messageFunctions-5)
- Входные параметры: authorization, тип string, описание «JWT (token) пользователя», расположение header, обязательный: +, значение по умолчанию: -, пример: -. (GET _api_functions_messageFunctions-5)
- Пример запроса: https://sfera.ppcps-stable.dev.sfera-t1.ru/app/trmonbs/api/admin/api/functions/messageFunctions (GET _api_functions_messageFunctions-5)
- Выходные параметры (content — object): (GET _api_functions_messageFunctions-5)
  - name, string, «Наименование функции», обязательный +; пример: getText.
  - description, string, «Описание функции», обязательный +; пример: «Функция возвращает текст json ноды».
  - returnType, «Тип возвращаемых данных функции», обязательный +; пример: String.
  - category, object, «Объект категории функции», обязательный +; пример: «Без категории» / «Текстовое значение».
    - code, string, «Наименование категории», обязательный +; пример: Text value / No category.
    - description, string, «Описание категории», обязательный +; пример: «Текстовое значение» / «Без категории».
  - parameters, object, «Параметры входных данных функции»: type — «Тип входных данных параметра», пример: String; description — «Описание параметра», пример: «Json путь»; value, object, «Предзаполненное значение», обязательный -; пример: null.
  - В таблице выходных параметров присутствует также строка functionType (описание в документе не приведено).
- Пример ответа (раздел 7, до доработки): [{"name":"getText","description":"Функция возвращает текст json ноды","returnType":"String","parameters":[{"type":"String","description":"Json путь","value":null},{"type":"JsonNode","description":"Json нода","value":null}]},{"name":"constant","description":"Функция возвращает полученную строку в виде константы","returnType":"String","parameters":[{"type":"String","description":"Строковое значение, которое необходимо представить в виде константы","value":null}]}] (GET _api_functions_messageFunctions-5)
- Пример ответа с категорией: [{"name":"getText","description":"Функция возвращает текст json ноды","returnType":"String","category":{"code":"Text value","description":"Текстовое значение"}] (GET _api_functions_messageFunctions-5)

### Сообщения и ошибки
- 200 ОК: «Операция выполнена успешно»; сценарий: «Спсок функций получен». (GET _api_functions_messageFunctions-5)
- 400 BadRequest: «Ошибка в синтаксисе запроса (не передан обязательный входной параметр / неверно задано значение входного параметра)»; сценарий: «Ошибка формата запроса». (GET _api_functions_messageFunctions-5)
- 403 Forbidden: «Нет прав для доступа к данным метода»; сценарий: «Доступ запрещен (согласно ролевой модели)». (GET _api_functions_messageFunctions-5)
- 409 Conflict и 423 Locked указаны в перечне кодов без отдельного сообщения и сценария. (GET _api_functions_messageFunctions-5)
- 500: «Сервис временно недоступен»; сценарий: «Внутренняя ошибка сервера». (GET _api_functions_messageFunctions-5)

### Бизнес-правила и ограничения
- 8.1. Доработка для «Конструктора создания технических атрибутов в источнике данных». Контекст: доработка необходима для категоризации функций на фронте. (GET _api_functions_messageFunctions-5)
- 8.1.1. Категоризация функций: дополнить выходные данные контракта объектом данных "category" с атрибутами "code" и "description" для дальнейшей обработки на фронте. (GET _api_functions_messageFunctions-5)
- Таблица категоризации (категория; функции; category.code; category.description): (GET _api_functions_messageFunctions-5)
  - Дата и время: formatDate, formatDateFunction, formatUnixTime, getCurrentTime; «Date and time»; «Дата и время».
  - Конкатенация данных: concatN, concatFCN, concat wsN; «Data concatenation»; «Конкатенация данных».
  - Условия сравнения: caseEqualN; «Comparing condition»; «Условия сравнения».
  - Текстовое значение: getText, formatText, constant; «Text value»; «Текстовое значение».
  - Проверка not null значений: coalesceN, coalesceNByTextValue; «Not null values check»; «Проверка not null значений».
  - Без категорий: extractJson, coalesceAsJsonNode, coalesce3AsJsonNode; «No category»; «Без категорий».

### Открытые вопросы
- Описание строки functionType в таблице выходных параметров не приведено. (GET _api_functions_messageFunctions-5)
- Для кода «No category» в выходных параметрах пример описания «Без категории», в таблице категоризации — «Без категорий». (GET _api_functions_messageFunctions-5)
