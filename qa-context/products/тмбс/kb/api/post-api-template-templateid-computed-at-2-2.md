# POST /api/template/{templateId}/computed-attribute/update — обновление вычисляемых атрибутов, созданных из шаблона

> POST-метод API ТМБС, который обновляет вычисляемые атрибуты, созданные из шаблона: подставляет параметры шаблона в SQL-скрипт, при необходимости синхронизирует пороги критичности и запускает обновление карточек мониторинга.

### Описание
- Наименование метода: «Обновление вычисляемых атрибутов, созданных из шаблона». URL: /api/template/{templateId}/computed-attribute/update. Метод HTTP: POST. Способ авторизации: JWT (token) пользователя. Ссылка на swagger: TBD. (12-POST _api_template_{templateId}_computed-attribute_update)
- Обработка ошибок: 400, 403, 404, 500. http-статус коды в ответе: 200. (12-POST _api_template_{templateId}_computed-attribute_update)
- История изменений: версия 1.0, автор @Kalinina D.А., дата 02 июл. 2026, описание «Создание страницы», задача PPBP-2309 [SA] Аналитика по функционалу "Массовые операции над сущностями созданными из шаблона". (12-POST _api_template_{templateId}_computed-attribute_update)
- Оглавление документа: Описание метода, История изменений, Входные параметры, Пример запроса, Выходные параметры, Пример ответа, 400, 403, 404, Логика работы. (12-POST _api_template_{templateId}_computed-attribute_update)

### Поля и элементы
- Входные параметры (колонки: №, Параметр, Тип, Описание, Расположение, Обязательный, Значение по умолчанию, Пример). Значок «+» в колонке «Обязательный» у всех параметров; «-» — нет значения по умолчанию/примера; текст описаний в PDF частично усечён. (12-POST _api_template_{templateId}_computed-attribute_update)
  1. templateId — int64 — Идентификатор шаблона — path — +; пример: 1851.
  2. entities — object — Массив вычисляемых атрибутов — body — +.
  3. entityRowId — int — Идентификатор вычисляемого атрибута — body — +.
  4. entityName — string — Название вычисляемого атрибута — body — +.
  5. syncParameters — object — Параметры шаблона — body — +.
  6. syncThresholds — boolean — Синхронизировать пороги критичности — body — +; по умолчанию: false; пример: true.
  7. syncTemplateParameters — array[object] — Параметры шаблона — body — +.
  8. code — string — Код переменной — body — +.
  9. name — string — Название переменной — body — +.
  10. type — TemplateParameterType — Тип переменной — body — +.
  11. value — string — Значение переменной — body — +.
- Выходные параметры (колонки: №, Параметр, Тип, Описание, Обязательный, Значение по умолчанию, Пример): (12-POST _api_template_{templateId}_computed-attribute_update)
  1. skippedIds — array[int] — Список пропущенных идентификаторов выч.атрибутов — обязательный: -, по умолчанию: -.
  2. successIds — array[int] — Список идентификаторов успешно обновленных выч. атрибутов — -, -.
  3. monitoringCardsForUpdating — array[object] — Список карточек мониторинга, в которых начался процесс обновления — -, -. Элементы содержат rowId и name (по примеру ответа).

### Бизнес-правила и ограничения
- Логика работы: (12-POST _api_template_{templateId}_computed-attribute_update)
  1. Проверить, что шаблон в статусе ACTIVE.
  2. Получить текущий набор полей и параметров шаблона.
  3. Для каждой сущности: a. Извлечь значения параметров из syncTemplateParameters. b. Сгенерировать новый SQL-скрипт (подставить параметры в шаблонный скрипт). c. Обновить все поля сущности, которые могут быть изменены шаблоном, кроме порогов критичности, если syncThresholds = false. Если syncThresholds = true – перезаписать пороги из шаблона и сбросить флаг manual_interval_override. d. Сохранить новые значения параметров в поле template_parameters_applied. e. Установить sync_with_template = true. f. Если карточка на мониторинге – запустить обновление (асинхронно).
  4. Вернуть ответ: id успешно обновленных, пропущенных, id и name карточек мониторинга из очереди на обновление.

### API и интеграции
- Пример запроса (тело): {"entities":[{"entityRowId":101,"entityName":"Название вычисляемого атрибута","syncParameters":{"syncThresholds":true,"syncTemplateParameters":[{"code":"val1","name":"val1","type":"string","value":"abcdef"},{"code":"val1","name":"val1","type":"string","value":"abcdef"}]}},{"entityRowId":102,"entityName":"Другое название вычисляемого атрибута","syncParameters":{"syncThresholds":false,"syncTemplateParameters":[{"code":"val1","name":"val1","type":"string","value":"abcdef"},{"code":"val1","name":"val1","type":"string","value":"abcdef"}]}}]} (12-POST _api_template_{templateId}_computed-attribute_update)
- Пример ответа (200): {"successIds":[101,102],"skippedIds":[103],"monitoringCardsForUpdating":[{"rowId":12345,"name":"1 Имя карточки мониторинга"},{"rowId":23456,"name":"2 Имя карточки мониторинга"}]} (12-POST _api_template_{templateId}_computed-attribute_update)

### Сообщения и ошибки
- 400 — Ошибка в запросе; 403 — Недостаточно прав; 404 — Ресурс не найден. (12-POST _api_template_{templateId}_computed-attribute_update)
- 500 указан в списке обработки ошибок, описание в документе не приведено. (12-POST _api_template_{templateId}_computed-attribute_update)

### Роли и права
- Роль: Администратор. Авторизация: JWT (token) пользователя. (12-POST _api_template_{templateId}_computed-attribute_update)

### Открытые вопросы
- Ссылка на swagger: TBD. (12-POST _api_template_{templateId}_computed-attribute_update)
- Описание ошибки 500 не приведено. (12-POST _api_template_{templateId}_computed-attribute_update)
