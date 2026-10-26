# Эталон API-кейса: TEAM-3834 «[BE][Стрим] Базовое создание»

Источник: выгрузка из системы управления тестами (Команда / TEAM / Тестовая модель / BE-кейсы / API / v1). Метки: baseEntities, API, v1. Приоритет: Критический. Регрессионный: Да. Автоматизация: не автоматизирован.

Что в эталоне важно:
- предусловия — цепочка: токен, выбор значений справочников, подстановка выбранного номера в поля;
- один шаг — один запрос; адрес стенда задан через `{{baseURL}}`, значение: `https://sfera.ppcps-stable.test.sfera-t1.ru/app/teams`;
- проверка в два уровня: ответ API, затем значения в БД по SQL и сравнение API с БД;
- ожидаемые результаты короткие и конкретные.

## Предусловия
1. В системе существует: бизнес-юнит BUT-1; департамент DPT-1 связан с BUT-1 связью parentOf.
2. Получить access_token (Bearer Token): POST `{{baseURL}}/api/auth/login`, тело `{"username": "<логин>", "password": "<пароль>"}` — учётная запись пользователя, от имени которого выполняется запрос.
3. GET `{{baseURL}}/api/v1/entities?type=streamType&archivalSign=false` (справочник «Вид стрима»).
   3.1. Выбрать любой number из ответа, например CATALOG-383 («ИТ-стрим»).
   3.2. Подставить выбранный номер в поле `streamTypeCode`.
4. GET `…/api/v1/entities?type=activityArea&archivalSign=false` (справочник «Тип по принадлежности продукта к направлению деятельности»).
   4.1. Выбрать любой number, например CATALOG-606 («Внесите изменения»).
   4.2. Подставить выбранный номер в поле `Activities`.
5. GET `…/api/v1/entities?type=…&archivalSign=false` (справочник «Тип по архитектуре»).
   5.1. Выбрать любой number, например CATALOG-1555 («Канальные»).
   5.2. Подставить выбранный номер в поле `streamArchTypeCode`.

## Шаги
1. Отправить POST `{{baseURL}}/api/v1/entities` с Bearer Token и телом:
   `{"name": "Тестовый стрим", "area": "FuncStruct", "type": "stream", "parent": "DPT-1", "description": "Тестовый Стрим", "streamTypeCode": "<CATALOG-383>", "Activities": "<CATALOG-606>", "streamArchTypeCode": "<CATALOG-1555>", "approvalDateCode": "2024-03-10", "startDate": "2024-03-10", "streamPerimeter": "Тестовый периметр", "restrictions": "Нет ограничений"}`.
   Ожидаемый результат: код 201 Created.
2. Проверить поля ответа: `name = "Тестовый стрим"`, `area = "FuncStruct"`, `type = "stream"`, `status = draft`, `description = "Тестовый Стрим"`, `parentNumber = DPT-1`.
3. Получить `name` из БД: `select name from entities where number = 'STR-1'`. Ожидаемый результат: «Тестовый стрим».
4. Проверить кастомные поля в ответе API: `Activities`, `streamArchTypeCode`, `startDate`, `approvalDateCode`, `streamPerimeter`, `restrictions`, `streamTypeCode`. Ожидаемый результат: значения из шага 1 (даты `2024-03-10`, периметр и ограничения — как в теле).
5. Проверить кастомные поля в БД: `select properties -> '{codeField}' from teams.entities where number = 'STR-1'`, где `{codeField}` — код кастомного поля.
6. Сравнить значения кастомных полей в ответе API со значениями в БД. Ожидаемый результат: значения совпадают.
7. Проверить наличие массива `catalogs` в ответе API и в нём объектов с number из шагов 3.2, 4.2 и 5.2.

## Что исправить при переносе в свои кейсы
- В эталоне опечатки и расхождения (`streamArcType` вместо `streamArchTypeCode`, «принадлжености»). В новых кейсах их не повторять.
- Не вставлять в ожидаемый результат целые JSON-ответы — только проверяемые поля.
- Не оставлять плейсхолдеры `{{Значение справочника …}}`: выбирать конкретный номер в предусловии и подставлять его.
