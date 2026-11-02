# POST /api/template/{templateId}/metric/update — обновление метрик, созданных из шаблона

> POST /api/template/{templateId}/metric/update — метод массового обновления метрик, созданных из шаблона, с опциональной синхронизацией порогов критичности и параметров шаблона, доступный роли Администратор.

### Описание
- Наименование метода: «Обновление метрик, созданных из шаблона». URL: /api/template/{templateId}/metric/update. Метод HTTP: POST. Способ авторизации: JWT (token) пользователя. Ссылка на swagger: TBD. Обработка ошибок: 400, 403, 404, 500. http-статус коды в ответе: 200. (POST _api_template_{templateId}_metric_update-10)
- История изменений: версия 1.0, автор @Kalinina D.А., дата 02 июл. 2026, описание «Создание страницы», номер задачи PPBP-2309 [SA] Аналитика по функционалу "Массовые операции над сущностями созданными из шаблона". (POST _api_template_{templateId}_metric_update-10)
- Оглавление страницы: Описание метода, История изменений, Входные параметры, Пример запроса, Выходные параметры, Пример ответа, 400, 403, 404, Логика работы. (POST _api_template_{templateId}_metric_update-10)

### Роли и права
- Роли: Администратор. (POST _api_template_{templateId}_metric_update-10)

### API и интеграции
- Входные параметры (таблица: № / Параметр / Тип / Описание / Расположение / Обязательный / Значение по умолчанию / Пример; описания в исходном PDF частично обрезаны, восстановлены по таблице страницы 3; знак обязательности «+»): (POST _api_template_{templateId}_metric_update-10)
  1. templateId — int64 — Идентификатор шаблона — path — обязательный (+) — пример 1851.
  2. entities — object — Массив метрик — body — обязательный (+).
  3. entityRowId — int — Идентификатор метрики — body — обязательный (+).
  4. entityName — string — Название метрики — body — обязательный (+).
  5. syncParameters — object — Параметры шаблона — body — обязательный (+).
  6. syncThresholds — boolean — Синхронизировать пороги критичности — body — обязательный (+) — значение по умолчанию false — пример true.
  7. syncTemplateParameters — array[object] — Параметры шаблона — body — обязательный (+).
  8. code — string — Код переменной — body — обязательный (+).
  9. name — string — Название переменной — body — обязательный (+).
  10. type — TemplateParameterType — Тип переменной — body — обязательный (+).
  11. value — string — Значение переменной — body — обязательный (+).
- Пример запроса: (POST _api_template_{templateId}_metric_update-10)
`{"entities":[{"entityRowId":101,"entityName":"Название метрики","syncParameters":{"syncThresholds":true,"syncTemplateParameters":[{"code":"val1","name":"val1","type":"string","value":"abcdef"},{"code":"val1","name":"val1","type":"string","value":"abcdef"}]}},{"entityRowId":201,"entityName":"Название метрики 2","syncParameters":{"syncThresholds":false,"syncTemplateParameters":[{"code":"val1","name":"val1","type":"string","value":"abcdef"},{"code":"val1","name":"val1","type":"string","value":"abcdef"}]}}]}`
- Выходные параметры (обязательность и значения по умолчанию не заданы, «-»): (POST _api_template_{templateId}_metric_update-10)
  1. skippedIds — array[int] — Список пропущенных идентификаторов метрик.
  2. successIds — array[int] — Список идентификаторов успешно обновленных метрик.
  3. monitoringCardsForUpdating — array[object] — Список карточек мониторинга, в которых начался процесс обновления.
- Пример ответа: (POST _api_template_{templateId}_metric_update-10)
`{"successIds":[101,102],"skippedIds":[103],"monitoringCardsForUpdating":[{"rowId":12345,"name":"1 Имя карточки мониторинга"},{"rowId":23456,"name":"2 Имя карточки мониторинга"}]}`

### Сообщения и ошибки
- 400 — «Ошибка в запросе». (POST _api_template_{templateId}_metric_update-10)
- 403 — «Недостаточно прав». (POST _api_template_{templateId}_metric_update-10)
- 404 — «Ресурс не найден». (POST _api_template_{templateId}_metric_update-10)
- 500 указан в списке обрабатываемых ошибок, описание в документе отсутствует. (POST _api_template_{templateId}_metric_update-10)

### Бизнес-правила и ограничения
- Шаблон должен быть в статусе ACTIVE. (POST _api_template_{templateId}_metric_update-10)
- Пороги критичности не обновляются, если syncThresholds = false. (POST _api_template_{templateId}_metric_update-10)
- Если syncThresholds = true, пороги перезаписываются из шаблона и сбрасывается флаг manual_interval_override. (POST _api_template_{templateId}_metric_update-10)

### Сценарии
- Логика работы: (POST _api_template_{templateId}_metric_update-10)
  1. Проверить, что шаблон в статусе ACTIVE.
  2. Получить текущий набор полей и параметров шаблона.
  3. Для каждой сущности:
     a. Извлечь значения параметров из syncTemplateParameters.
     b. Сгенерировать новый SQL-скрипт (подставить параметры в шаблонный скрипт).
     c. Обновить все поля сущности, которые могут быть изменены шаблоном, кроме порогов критичности, если syncThresholds = false. Если syncThresholds = true – перезаписать пороги из шаблона и сбросить флаг manual_interval_override.
     d. Сохранить новые значения параметров в поле template_parameters_applied.
     e. Установить sync_with_template = true.
     f. Если карточка на мониторинге – запустить Обновление (асинхронно).
  4. Вернуть ответ: id успешно обновленных, пропущенных, id и name карточек мониторинга из очереди на обновление.
