# Таблица БД метрик (metric)

> Таблица БД метрик (metric) продукта «ТМБС» — описание структуры таблицы метрик: поля, типы, значения по умолчанию, ограничения, первичный и внешние ключи.

### Описание
- Документ описывает таблицу метрик («Таблица метрик»); разделы документа: «Назначение таблицы», «Структура таблицы», «Ключи и индексы». (metric-3)
- Текст раздела «Назначение таблицы» во фрагменте отсутствует (указан только заголовок «Таблица метрик»). (metric-3)

### Поля и элементы
Структура таблицы (поле · тип · значение по умолчанию · ограничения · описание):
- id · serial4 · PK, NOT_NULL (metric-3)
- name · text · NOT_NULL (metric-3)
- description · text (metric-3)
- calculation_method · text (metric-3)
- status · metric_status · NOT_NULL; в документе рядом со статусом стоит «?» (metric-3)
- script · text (metric-3)
- unit_id · int4 · NOT_NULL (metric-3)
- event_script · text (metric-3)
- calculation_period · int4 · по умолчанию 60 · NOT_NULL (metric-3)
- calculation_period_in_minutes · int2 (metric-3)
- alerted_object_url_template · text · NOT_NULL (metric-3)
- sending_enabled · bool · по умолчанию false · NOT_NULL (metric-3)
- monitoring_card_row_id · int8 · NOT_NULL (metric-3)
- metric_id · int4 · NOT_NULL (metric-3)
- parent_id · int4 (metric-3)
- metric_schedule · varchar(255) · по умолчанию "type": "MINUTE" · NOT_NULL (metric-3)
- export_to_kafka · boolean · по умолчанию false · NOT_NULL · «Признак отправки метрики в ЗСМ» (metric-3)

### Бизнес-правила и ограничения
- Primary Key: id (автоинкремент). (metric-3)
- Foreign Key: unit_id -> dictionary_metric_unit.id. (metric-3)
- Foreign Key: monitoring_card_row_id -> monitoring_card.row_id. (metric-3)
- Обязательные (NOT_NULL) поля: id, name, status, unit_id, calculation_period, alerted_object_url_template, sending_enabled, monitoring_card_row_id, metric_id, metric_schedule, export_to_kafka. (metric-3)

### Открытые вопросы
- «ВОПРОС: для поля calculation_period по умолчанию значение 60, но в данных прописывается 5 для всех данных». (metric-3)
