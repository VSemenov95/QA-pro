# POST /api/template/{templateId}/metric/change-status — изменение статуса метрик, созданных из шаблона

> Административный метод POST /api/template/{templateId}/metric/change-status массово меняет статус метрик, созданных из шаблона, и возвращает списки обновлённых и пропущенных метрик, а также карточек мониторинга, поставленных на обновление.

### Описание
- Наименование метода: «Изменение статуса метрик, созданных из шаблона». URL: /api/template/{templateId}/metric/change-status. Метод HTTP: POST. (5-POST _api_template_{templateId}_metric_change-status)
- Способ авторизации: JWT (token) пользователя. Ссылка на swagger: TBD. (5-POST _api_template_{templateId}_metric_change-status)
- История изменений: версия 1.0, автор @Kalinina D.А., дата 02 июл. 2026, описание «Создание страницы», задача PPBP-2309 [SA] Аналитика по функционалу "Массовые операции над сущностями созданными из шаблона". (5-POST _api_template_{templateId}_metric_change-status)

### Роли и права
- Роль: Администратор. (5-POST _api_template_{templateId}_metric_change-status)

### API и интеграции
- Обработка ошибок: 400, 403, 404, 500. http-статус коды в ответе: 200. (5-POST _api_template_{templateId}_metric_change-status)
- Входные параметры:
  1. templateId — int64, идентификатор шаблона, path, обязательный, пример 1851.
  2. metricIds — array [int], список идентификаторов метрик, body, обязательный, пример 101, 102, 103.
  3. newStatus — string, статус, body, обязательный; пример значения в таблице не указан. (5-POST _api_template_{templateId}_metric_change-status)
- Значение по умолчанию для всех входных параметров: «-». (5-POST _api_template_{templateId}_metric_change-status)
- Пример запроса: {"metricIds": [101, 102, 103], "newStatus": "MONITORING"} (5-POST _api_template_{templateId}_metric_change-status)
- Выходные параметры (обязательность и значение по умолчанию: «-»):
  1. skippedIds — array [int], список идентификаторов пропущенных метрик.
  2. successIds — array [int], список идентификаторов успешно обновленных метрик.
  3. monitoringCardsForUpdating — array [object], список карточек мониторинга, в которых начался процесс обновления. (5-POST _api_template_{templateId}_metric_change-status)
- Пример ответа: {"successIds": [101, 102], "skippedIds": [103], "monitoringCardsForUpdating": [{"rowId": 12345, "name": "1 Имя карточки мониторинга"}, {"rowId": 23456, "name": "2 Имя карточки мониторинга"}]} (5-POST _api_template_{templateId}_metric_change-status)

### Сообщения и ошибки
- 400 — Ошибка в запросе. (5-POST _api_template_{templateId}_metric_change-status)
- 403 — Недостаточно прав. (5-POST _api_template_{templateId}_metric_change-status)
- 404 — Ресурс не найден. (5-POST _api_template_{templateId}_metric_change-status)
- 500 указан в списке обработки ошибок, описание в документе отсутствует. (5-POST _api_template_{templateId}_metric_change-status)

### Бизнес-правила и ограничения
- Шаблон должен существовать и иметь статус ACTIVE, иначе возвращается 400. (5-POST _api_template_{templateId}_metric_change-status)
- Метрика должна существовать и иметь template_id = templateId. (5-POST _api_template_{templateId}_metric_change-status)
- Переход в newStatus должен быть допустим согласно статусной модели метрики; если недопустим — метрика пропускается. (5-POST _api_template_{templateId}_metric_change-status)
- Если карточка, к которой принадлежит сущность, находится в статусе MONITORING, то после обновления карточка ставится в очередь на обновление (асинхронно). (5-POST _api_template_{templateId}_metric_change-status)

### Сценарии
- Логика работы: 1) проверить, что шаблон существует и имеет статус ACTIVE, иначе вернуть 400; 2) для каждого Id проверить, что метрика существует и имеет template_id = templateId; 3) проверить допустимость перехода в newStatus по статусной модели метрики, если недопустимо – пропустить; 4) если карточка в статусе MONITORING – после обновления поставить её в очередь на обновление (асинхронно); 5) собрать статистику: id успешно обновленных, пропущенных, id и name карточек мониторинга из очереди на обновление; 6) вернуть ответ. (5-POST _api_template_{templateId}_metric_change-status)

### Открытые вопросы
- Ссылка на swagger: TBD. (5-POST _api_template_{templateId}_metric_change-status)
- Для newStatus не указаны пример значения в таблице и перечень допустимых статусов (в примере запроса — "MONITORING"). (5-POST _api_template_{templateId}_metric_change-status)
- Не описано, как обрабатываются метрики, у которых template_id не совпадает с templateId или которые не существуют (шаг 2 не уточняет: пропуск или ошибка). (5-POST _api_template_{templateId}_metric_change-status)
- Описание ошибки 500 отсутствует. (5-POST _api_template_{templateId}_metric_change-status)
