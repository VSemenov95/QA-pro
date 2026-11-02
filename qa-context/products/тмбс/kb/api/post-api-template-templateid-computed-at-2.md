# POST /api/template/{templateId}/computed-attribute/delete — удаление вычисляемых атрибутов, созданных из шаблона

> Метод POST /api/template/{templateId}/computed-attribute/delete удаляет вычисляемые атрибуты, созданные из шаблона, и возвращает списки удалённых и пропущенных идентификаторов, а также карточек мониторинга, поставленных на обновление.

### Описание
- Наименование метода: «Удаление вычисляемых атрибутов, созданных из шаблона». URL: /api/template/{templateId}/computed-attribute/delete. Метод HTTP: POST. Ссылка на swagger: TBD. (POST _api_template_{templateId}_computed-attribute_delete-6)
- История изменений: версия 1.0, автор @Kalinina D.А., дата 02 июл. 2026, описание «Создание страницы», номер задачи PPBP-2309 [SA] Аналитика по функционалу "Массовые операции над сущностями созданными из шаблона". (POST _api_template_{templateId}_computed-attribute_delete-6)

### Поля и элементы
**Входные параметры**
- templateId: int64, идентификатор шаблона, расположение path, обязательный (+), значение по умолчанию «-». (POST _api_template_{templateId}_computed-attribute_delete-6)
- computedAttributeIds: array [int], список идентификаторов вычисляемых атрибутов, расположение body, обязательный (+), значение по умолчанию «-». (POST _api_template_{templateId}_computed-attribute_delete-6)

**Выходные параметры** (все необязательные, значение по умолчанию «-»)
- skippedIds: array [int], список пропущенных идентификаторов выч.атрибутов. (POST _api_template_{templateId}_computed-attribute_delete-6)
- successIds: array [int], список успешно удалённых идентификаторов выч.атрибутов. (POST _api_template_{templateId}_computed-attribute_delete-6)
- monitoringCardsForUpdating: array [object], список карточек мониторинга, в которых начался процесс обновления. (POST _api_template_{templateId}_computed-attribute_delete-6)
- Страница 3 документа с примерами значений таблицы выходных параметров отображена фрагментарно (видны только «1851» и «101, 102, 103»); соответствие примеров параметрам однозначно не восстанавливается. (POST _api_template_{templateId}_computed-attribute_delete-6)

### Бизнес-правила и ограничения
- Шаблон должен существовать и иметь статус ACTIVE, иначе возвращается 400. (POST _api_template_{templateId}_computed-attribute_delete-6)
- Для каждого Id проверяется, что вычисляемый атрибут существует и действительно имеет template_id = templateId. (POST _api_template_{templateId}_computed-attribute_delete-6)
- Если карточка, к которой принадлежит сущность, находится в статусе MONITORING, то после удаления карточка ставится в очередь на обновление (асинхронно). (POST _api_template_{templateId}_computed-attribute_delete-6)

### API и интеграции
- Способ авторизации: JWT (token) пользователя. (POST _api_template_{templateId}_computed-attribute_delete-6)
- http-статус коды в ответе: 200. Обработка ошибок: 400, 403, 404, 500. (POST _api_template_{templateId}_computed-attribute_delete-6)
- Пример запроса (тело): {"computedAttributeIds": [101, 102, 103]} (POST _api_template_{templateId}_computed-attribute_delete-6)
- Пример ответа: {"successIds": [101, 102], "skippedIds": [103], "monitoringCardsForUpdating": [{"rowId": 12345, "name": "1 Имя карточки мониторинга"}, {"rowId": 23456, "name": "2 Имя карточки мониторинга"}]} (POST _api_template_{templateId}_computed-attribute_delete-6)

### Сообщения и ошибки
- 400 — Ошибка в запросе. (POST _api_template_{templateId}_computed-attribute_delete-6)
- 403 — Недостаточно прав. (POST _api_template_{templateId}_computed-attribute_delete-6)
- 404 — Ресурс не найден. (POST _api_template_{templateId}_computed-attribute_delete-6)
- 500 указан в списке обработки ошибок, описание отдельно не приведено. (POST _api_template_{templateId}_computed-attribute_delete-6)

### Роли и права
- Роли: Администратор. (POST _api_template_{templateId}_computed-attribute_delete-6)

### Сценарии
- Логика работы: 1) проверить, что шаблон существует и имеет статус ACTIVE, иначе вернуть 400; 2) для каждого Id проверить, что выч.атрибут существует и имеет template_id = templateId; 3) если карточка, к которой принадлежит сущность, в статусе MONITORING, после удаления поставить карточку в очередь на обновление (асинхронно); 4) собрать статистику: id успешно удалённых, пропущенных, id и name карточек мониторинга из очереди на обновление; 5) вернуть ответ. (POST _api_template_{templateId}_computed-attribute_delete-6)
