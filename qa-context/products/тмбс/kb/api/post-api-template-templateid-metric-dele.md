# POST /api/template/{templateId}/metric/delete — удаление метрик, созданных из шаблона

> Метод POST /api/template/{templateId}/metric/delete удаляет по списку идентификаторов метрики, созданные из шаблона, и возвращает списки удалённых и пропущенных id, а также карточек мониторинга, поставленных на обновление.

### Описание
- Наименование метода: «Удаление метрик, созданных из шаблона». URL: /api/template/{templateId}/metric/delete. Метод HTTP: POST. Способ авторизации: JWT (token) пользователя. (POST _api_template_{templateId}_metric_delete-7)
- Оглавление страницы: Описание метода, История изменений, Входные параметры, Пример запроса, Выходные параметры, Пример ответа, 400, 403, 404, Логика работы. (POST _api_template_{templateId}_metric_delete-7)
- История изменений: версия 1.0, автор @Kalinina D.А., дата 02 июл. 2026, описание «Создание страницы», номер задачи PPBP-2309 [SA] Аналитика по функционалу "Массовые операции над сущностями созданными из шаблона". (POST _api_template_{templateId}_metric_delete-7)

### Роли и права
- Роли: Администратор. (POST _api_template_{templateId}_metric_delete-7)

### API и интеграции
- Ссылка на swagger: TBD. (POST _api_template_{templateId}_metric_delete-7)
- Обработка ошибок: 400, 403, 404, 500. http-статус коды в ответе: 200. (POST _api_template_{templateId}_metric_delete-7)
- Входные параметры: (POST _api_template_{templateId}_metric_delete-7)
  1. templateId — тип int64, «Идентификатор шаблона», расположение: path, обязательный: +, значение по умолчанию: -, пример: 1851.
  2. metricIds — тип array [int], «Список идентификаторов метрик», расположение: body, обязательный: +, значение по умолчанию: -, пример: 101, 102, 103.
- Пример запроса (body): {"metricIds": [101, 102, 103]} (POST _api_template_{templateId}_metric_delete-7)
- Выходные параметры (обязательность и значение по умолчанию: -): (POST _api_template_{templateId}_metric_delete-7)
  1. skippedIds — array [int], «Список пропущенных идентификаторов метрик».
  2. successIds — array [int], «Список успешно удаленных идентификаторов метрик».
  3. monitoringCardsForUpdating — array [object], «Список карточек мониторинга, в которых начался процесс обновления».
- Пример ответа: {"successIds": [101, 102], "skippedIds": [103], "monitoringCardsForUpdating": [{"rowId": 12345, "name": "1 Имя карточки мониторинга"}, {"rowId": 23456, "name": "2 Имя карточки мониторинга"}]} (POST _api_template_{templateId}_metric_delete-7)

### Сообщения и ошибки
- 400 — Ошибка в запросе. (POST _api_template_{templateId}_metric_delete-7)
- 403 — Недостаточно прав. (POST _api_template_{templateId}_metric_delete-7)
- 404 — Ресурс не найден. (POST _api_template_{templateId}_metric_delete-7)
- В списке обработки ошибок также указан код 500 (описание в документе не приведено). (POST _api_template_{templateId}_metric_delete-7)

### Бизнес-правила и ограничения
- Шаблон должен существовать и иметь статус ACTIVE, иначе возвращается 400. (POST _api_template_{templateId}_metric_delete-7)
- Для каждого Id проверяется, что вычисляемый атрибут существует и действительно имеет template_id = templateId. (POST _api_template_{templateId}_metric_delete-7)
- Если карточка, к которой принадлежит сущность, находится в статусе MONITORING, то после удаления карточка ставится в очередь на обновление (асинхронно). (POST _api_template_{templateId}_metric_delete-7)

### Сценарии
- Логика работы: (POST _api_template_{templateId}_metric_delete-7)
  1. Проверить, что шаблон существует и имеет статус ACTIVE. Иначе вернуть 400.
  2. Для каждого Id проверить, что выч.атрибут существует и действительно имеет template_id = templateId.
  3. Если карточка, к которой принадлежит сущность, находится в статусе MONITORING — после удаления поставить карточку в очередь на обновление (асинхронно).
  4. Собрать статистику: id успешно удалённых, пропущенных, id и name карточек мониторинга из очереди на обновление.
  5. Вернуть ответ.

### Открытые вопросы
- Ссылка на swagger: TBD. (POST _api_template_{templateId}_metric_delete-7)
- В логике работы проверяется «выч.атрибут», хотя метод называется удалением метрик и параметр — metricIds; документ это не поясняет. (POST _api_template_{templateId}_metric_delete-7)
- Для кода 500 описание не приведено. (POST _api_template_{templateId}_metric_delete-7)
