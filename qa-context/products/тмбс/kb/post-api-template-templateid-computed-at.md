# POST /api/template/{templateId}/computed-attribute/change-status — изменение статуса вычисляемых атрибутов, созданных из

> POST-метод API для массового изменения статуса вычисляемых атрибутов, созданных из шаблона, с пропуском недопустимых переходов и постановкой карточек мониторинга в очередь на обновление.

### Описание
- Наименование метода: «Изменение статуса вычисляемых атрибутов, созданных из шаблона». URL: /api/template/{templateId}/computed-attribute/change-status. Метод HTTP: POST. Способ авторизации: JWT (token) пользователя. Ссылка на swagger: TBD. (7-POST _api_template_{templateId}_computed-attribute_change-status)
- История изменений: версия 1.0, автор @Kalinina D.А., дата 02 июл. 2026, описание «Создание страницы», задача PPBP-2309 [SA] Аналитика по функционалу "Массовые операции над сущностями созданными из шаблона". (7-POST _api_template_{templateId}_computed-attribute_change-status)

### Бизнес-правила и ограничения
- Проверить, что шаблон существует и имеет статус ACTIVE. Иначе вернуть 400. (7-POST _api_template_{templateId}_computed-attribute_change-status)
- Для каждого Id проверить, что вычисляемый атрибут существует и действительно имеет template_id = templateId. (7-POST _api_template_{templateId}_computed-attribute_change-status)
- Проверить допустимость перехода в newStatus согласно статусной модели атрибута. Если недопустимо — пропустить. (7-POST _api_template_{templateId}_computed-attribute_change-status)
- Если карточка, к которой принадлежит сущность, находится в статусе MONITORING — после обновления поставить карточку в очередь на обновление (асинхронно). (7-POST _api_template_{templateId}_computed-attribute_change-status)
- Собрать статистику: id успешно обновлённых, пропущенных, id и name карточек мониторинга из очереди на обновление. Вернуть ответ. (7-POST _api_template_{templateId}_computed-attribute_change-status)

### API и интеграции
- Обработка ошибок: 400, 403, 404, 500. http-статус коды в ответе: 200. (7-POST _api_template_{templateId}_computed-attribute_change-status)
- Входные параметры: 1) templateId, int64, идентификатор шаблона, path, обязательный; 2) computedAttributeIds, array [int], список идентификаторов вычисляемых атрибутов, body, обязательный; 3) newStatus, string, статус, body, обязательный. Значений по умолчанию нет. (7-POST _api_template_{templateId}_computed-attribute_change-status)
- Пример запроса: {"computedAttributeIds": [101, 102, 103], "newStatus": "MONITORING"} (7-POST _api_template_{templateId}_computed-attribute_change-status)
- Выходные параметры (все необязательные): skippedIds, array [int], список пропущенных идентификаторов выч.атрибутов; successIds, array [int], список идентификаторов успешно обновленных выч. атрибутов; monitoringCardsForUpdating, array [object], список карточек мониторинга, в которых начался процесс обновления. Примеры в таблице частично не читаются (в тексте встречаются значения 101, 102, 103 и 1851). (7-POST _api_template_{templateId}_computed-attribute_change-status)
- Пример ответа: {"successIds": [101, 102], "skippedIds": [103], "monitoringCardsForUpdating": [{"rowId": 12345, "name": "1 Имя карточки мониторинга"}, {"rowId": 23456, "name": "2 Имя карточки мониторинга"}]} (7-POST _api_template_{templateId}_computed-attribute_change-status)

### Сообщения и ошибки
- 400 — Ошибка в запросе. (7-POST _api_template_{templateId}_computed-attribute_change-status)
- 403 — Недостаточно прав. (7-POST _api_template_{templateId}_computed-attribute_change-status)
- 404 — Ресурс не найден. (7-POST _api_template_{templateId}_computed-attribute_change-status)
- 500 указан в списке обработки ошибок, описание в документе не приведено. (7-POST _api_template_{templateId}_computed-attribute_change-status)

### Роли и права
- Роль: Администратор. Авторизация: JWT (token) пользователя. (7-POST _api_template_{templateId}_computed-attribute_change-status)

### Открытые вопросы
- Ссылка на swagger: TBD. (7-POST _api_template_{templateId}_computed-attribute_change-status)
- Допустимые значения newStatus и статусная модель атрибута в документе не приведены. (7-POST _api_template_{templateId}_computed-attribute_change-status)
- Не описаны текст и условия ошибки 500. (7-POST _api_template_{templateId}_computed-attribute_change-status)
