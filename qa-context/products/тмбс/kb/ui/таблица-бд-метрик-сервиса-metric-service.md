# Таблица БД метрик Сервиса (metric_service)

> Таблица БД metric_service хранит данные о метриках Сервиса: идентификаторы, наименование, статус, код расчёта, периодичность, настройки оповещений и выгрузки в ЗСМ.

### Описание
- Таблица предназначена для хранения данных о метрикам Сервиса. (5-metric_service)
- Раздел «Логика обработки.» в документе присутствует только как заголовок, содержимого нет. (5-metric_service)

### Поля и элементы
Формат: поле · тип · описание · значение по умолчанию · ограничения.
- id · serial4 · Идентификатор метрики Сервиса · «-» · PK, NOT_NULL (5-metric_service)
- metricId · int32 · Сквозной идентификатор метрики · «-» · NOT_NULL (5-metric_service)
- name · text · Наименование метрики Сервиса · «-» · NOT_NULL (5-metric_service)
- description · text · Описание метрики Сервиса · «-» · NULLABLE (5-metric_service)
- calculation_method · text · Методичка расчета метрики Сервиса · «-» · NULLABLE (5-metric_service)
- status · metric_status · Статус метрики Сервиса · DRAFT · NOT_NULL (5-metric_service)
- script · text · Код метрики Сервиса · «-» · NULLABLE (5-metric_service)
- unit_id · int4 · Идентификатор единицы измерения · «-» · NOT_NULL (5-metric_service)
- event_script · text · Код события мониторинга Сервиса · значение по умолчанию не указано · NULLABLE (5-metric_service)
- calculation_period · int4 · Периодичность расчета · 60 · NOT_NULL (5-metric_service)
- calculation_period_in_minutes · int2 · Периодичность расчета в минутах · значение по умолчанию не указано · NULLABLE (5-metric_service)
- alerted_object_url_template · text · Шаблон ссылки на дашборд · значение по умолчанию не указано · NOT_NULL (5-metric_service)
- sending_enabled · bool · Признак включения оповещений · false · NOT_NULL (5-metric_service)
- service_id · int4 · Идентификатор Сервиса · значение по умолчанию не указано · NOT_NULL (5-metric_service)
- label · string · Метки для сервиса · «-» · NULLABLE (5-metric_service)
- metric_schedule · varchar(255) · Частота запроса для метрики Сервиса · "type": "MINUTE" · NOT_NULL (5-metric_service)
- export_to_kafka · boolean · Признак отправки метрики в ЗСМ · false · NOT_NULL (5-metric_service)

### Бизнес-правила и ограничения
- Primery Key: id (автоинкремент). (5-metric_service)
- Foreign Key: unit_id -> dictionary_metric_unit.id. (5-metric_service)
- Foreign Key: service_id -> service.id. (5-metric_service)
