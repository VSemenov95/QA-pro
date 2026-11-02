# POST /api/functions/evaluate — вычисление значения технического атрибута по заданному выражению

> Административный метод POST /api/functions/evaluate для отладки вычисления технических атрибутов: применяет заданную функцию к переданному примеру сообщения из источника данных.

### Описание
- URL: /api/functions/evaluate; метод HTTP: POST. (2-POST _api_functions_evaluate_)
- Наименование метода: «Вычисление значения технического атрибута по заданному выражению» (используется для отладки вычисления тех. атрибутов на примере из источника данных). (2-POST _api_functions_evaluate_)
- Метод применяет заданную функцию (набор функций) к переданному сообщению (параметр message: «Сообщение на котором будет применён набор функций»). (2-POST _api_functions_evaluate_)
- Swagger: https://trmonbs-admin-service.ppmon.dev.sfera-t1.ru/swagger-ui/index.html#/FunctionsController/evaluateFunction (2-POST _api_functions_evaluate_)
- История изменений: версия 1.0, автор @Perekin D.С., 06 февр. 2026, «Создание страницы», задача PPBP-1629 [Analytics][SA] Доработки конструктора создания технических атрибутов в источники данных. (2-POST _api_functions_evaluate_)
- Оглавление документа: Описание метода, История изменений, Входные параметры, Пример запроса, Выходные параметры, Пример ответа, Логика работы. (2-POST _api_functions_evaluate_)

### Поля и элементы
- Входные параметры (параметр | тип | описание | расположение | обязательный | по умолчанию | пример). Колонки таблицы в извлечённом тексте разнесены по страницам, соответствие значений полям восстановлено по порядку и может быть неточным. (2-POST _api_functions_evaluate_)
- authorization | string | JWT (token) пользователя | header | обязательный (+). (2-POST _api_functions_evaluate_)
- function | object | Описание функции | body | обязательный (+). (2-POST _api_functions_evaluate_)
  - branchId | тип не указан | «Идентификатор проверки?» | body | + | пример 853302007516.
  - description | тип не указан | Описание функции | body | не обязательный | пример «Функция возвращает текст json ноды».
  - idUI | string | Идентификатор отображаемый на UI | body | + | пример 384881804140.
  - name | тип не указан | Наименование функции | body | + | пример getText.
  - parameters | array object | Входные параметры функции | body | +:
    - items | object | Объект атрибута | body | +.
    - description | тип не указан | Описание атрибута | body | не обязательный | пример «Json путь».
    - type | тип не указан | Тип атрибута | body | + | пример String.
    - value | object | описание не указано | body | не обязательный.
    - functionType | тип не указан | Значение параметра функции. Принимает два значения: VALUE (обычное стринговое значение), FUNCTION (функция) | body | не обязательный | по умолчанию VALUE.
    - value (внутри value) | тип не указан | Значение параметра | body | не обязательный | пример qrcodeid.
  - returnType | string | Тип возвращаемого значения | body | + | пример String.
- message | тип не указан | Сообщение на котором будет применён набор функций | body | признак обязательности не указан. (2-POST _api_functions_evaluate_)
- Пример запроса: function{name: getText, description: «Функция возвращает текст json ноды», returnType: String, parameters: [{type: String, description: «Json путь», value:{value: qrcodeid, functionType: VALUE}}, {type: JsonNode, description: «Json нода», value:{value: #message, branchId: 853302007516, functionType: VALUE}}], idUI: 384881804140, branchId: 853302007516}, message — JSON-строка события (createDate, qrcodeid555, action, status, amount, status_base_localizedname, last_modify_date, payer_name, payer_account, receiver_name, receiver_account, transactionUuid). (2-POST _api_functions_evaluate_)

### API и интеграции
- Способ авторизации: JWT (token) пользователя. (2-POST _api_functions_evaluate_)
- Успех: HTTP 200 ОК, данные в теле ответа отсутствуют. (2-POST _api_functions_evaluate_)
- Обработка ошибок: 400, 403, 409, 423, 500. (2-POST _api_functions_evaluate_)
- Выходные параметры при ошибке: errorCode | string | Код состояния ошибки | обязательный (+) | пример 999; errorMessage | string | Описание ошибки по обработке функции | обязательный (+) | пример «Внутренняя ошибка сервиса.». (2-POST _api_functions_evaluate_)

### Сообщения и ошибки
- Пример ответа (ошибка): {"errorCode":999,"errorMessage":"Внутренняя ошибка сервиса."} (2-POST _api_functions_evaluate_)

### Роли и права
- Роли: Администратор. (2-POST _api_functions_evaluate_)
- Авторизация: JWT (token) пользователя. (2-POST _api_functions_evaluate_)

### Открытые вопросы
- Раздел «Логика работы» присутствует в оглавлении и заголовках, но содержимого не содержит. (2-POST _api_functions_evaluate_)
- Назначение параметра branchId обозначено с вопросом: «Идентификатор проверки?». (2-POST _api_functions_evaluate_)
- Описание успешного ответа (200 без тела) выглядит неочевидным для метода «вычисления», результат вычисления в документе не описан. (2-POST _api_functions_evaluate_)
