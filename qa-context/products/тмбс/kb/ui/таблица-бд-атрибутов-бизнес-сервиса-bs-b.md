# Таблица БД атрибутов бизнес-сервиса (bs_{$bs}_attribute_distributed)

> Таблица ClickHouse с результатами расчёта вычисляемых атрибутов бизнес-сервисов (распределённая таблица после фичи PPMON-1382, локальная таблица до неё): колонки, значения по умолчанию, движок, индексы, партиционирование и TTL.

### Описание
- В таблице представлены результаты расчёта вычисляемых атрибутов бизнес-сервисов, которые пользователь может настроить в интерфейсе. (2-bs_{$bs}_attribute_table_distributed; 8-bs_{$bs}_attribute)
- В таблице bs_{$bs}_attribute_distributed хранятся вычисления атрибутов ПОСЛЕ реализации фичи PPMON-1382 ПП. ТМБС. Передача метрик из ТМБС в ЗСМ в привязке к сервисам с агрегирующим расчетом на стороне ТМБС. (2-bs_{$bs}_attribute_table_distributed)
- В таблице bs_{$bs}_attribute хранятся вычисления атрибутов ДО реализации фичи PPMON-1382. Раздел «DDL» содержит пример создаваемой таблицы `default`.bs_6606_attribute. (8-bs_{$bs}_attribute)
- Пример DDL распределённой таблицы приведён для `default.bs_6606_attribute_distributed` (раздел «Примечание», пункт 1; других пунктов в «Примечании» нет). (2-bs_{$bs}_attribute_table_distributed)

### Поля и элементы
Колонки (имя, тип, описание):
- transaction_type, String — ID БС. (2-bs_{$bs}_attribute_table_distributed; 8-bs_{$bs}_attribute)
- transaction_time, DateTime64(3, 'Europe/Moscow') — Время транзакции. (2-bs_{$bs}_attribute_table_distributed; 8-bs_{$bs}_attribute)
- transaction_uuid, UUID — uuid транзакции. (2-bs_{$bs}_attribute_table_distributed; 8-bs_{$bs}_attribute)
- transaction_attribute_value, Int32 — Вычисляемое значение атрибута. (2-bs_{$bs}_attribute_table_distributed; 8-bs_{$bs}_attribute)
- attribute_id, UInt32 — ID атрибута. (2-bs_{$bs}_attribute_table_distributed; 8-bs_{$bs}_attribute)
- attribute_name, String — Наименование атрибута. (2-bs_{$bs}_attribute_table_distributed; 8-bs_{$bs}_attribute)
- attribute_status, String — Статус атрибута. (2-bs_{$bs}_attribute_table_distributed; 8-bs_{$bs}_attribute)
- attribute_threshold_type, String — Значение threshold согласно настроенным интервалам. (2-bs_{$bs}_attribute_table_distributed; 8-bs_{$bs}_attribute)
- unit, String — Единица измерения значения. (2-bs_{$bs}_attribute_table_distributed; 8-bs_{$bs}_attribute)
- transaction_events_count, UInt16 — Количество событий транзакции, на которых расчитан атрибут. (2-bs_{$bs}_attribute_table_distributed; 8-bs_{$bs}_attribute)
- valid, Bool — Признак валидности записи. (2-bs_{$bs}_attribute_table_distributed; 8-bs_{$bs}_attribute)
- replacing_version, UInt16 — описание в документе не указано. (2-bs_{$bs}_attribute_table_distributed; 8-bs_{$bs}_attribute)
- partial, Bool — true, если часть ключей событий транзакции невалидны, т.е. не участвовали в склейке. (2-bs_{$bs}_attribute_table_distributed; 8-bs_{$bs}_attribute)
- user_transaction_time, Nullable(DateTime64(3, 'Europe/Moscow')) — время транзакции, вычисление которого настраивается пользователем. (2-bs_{$bs}_attribute_table_distributed; 8-bs_{$bs}_attribute)
- insert_timestamp, DateTime64(3, 'Europe/Moscow') — Время записи вычисления в ClickHouse. (2-bs_{$bs}_attribute_table_distributed; 8-bs_{$bs}_attribute)
- service_id, int4 — Идентификатор Сервиса (указана только в описании распределённой таблицы). (2-bs_{$bs}_attribute_table_distributed)
- <tech_attr>, Array — Дополнительный тех. атрибут, выбранный пользователем для переноса данных событий в таблицу атрибутов. (2-bs_{$bs}_attribute_table_distributed; 8-bs_{$bs}_attribute)

### Бизнес-правила и ограничения
- Пользователь может добавлять произвольное количество столбцов в таблицу исходя из своей бизнес-потребности. Столбцы определяются на уровне функции "дополнительные поля в вычисляемых атрибутах". (8-bs_{$bs}_attribute)
- Дополнительные столбцы в примере DDL: event_stage, action, event_id_group_1, current_time_fl, event_time, not_existing_fl — все Array(String) DEFAULT []. В тексте документа 8 как такие поля названы только event_stage, action, event_id_group_1. (2-bs_{$bs}_attribute_table_distributed; 8-bs_{$bs}_attribute)
- Значения по умолчанию в DDL: valid = toUInt8(1); partial = toUInt8(0); user_transaction_time = NULL; replacing_version = if(toUInt8(valid), transaction_events_count, toUInt16(65535)). (2-bs_{$bs}_attribute_table_distributed; 8-bs_{$bs}_attribute)
- Движок распределённой таблицы: Distributed('cl1', 'default', 'bs_6606_attribute', reinterpretAsUInt64(transaction_uuid)) — распределение по ключу reinterpretAsUInt64(transaction_uuid) на локальную таблицу 'bs_6606_attribute' в базе 'default' кластера 'cl1'. (2-bs_{$bs}_attribute_table_distributed)
- Индексы (DDL таблицы bs_{$bs}_attribute): insert_timestamp_idx (insert_timestamp, minmax, GRANULARITY 4); user_transaction_time_idx (user_transaction_time, minmax, GRANULARITY 4); для каждого дополнительного Array(String)-столбца индекс <имя>_set_100_index типа set(100), GRANULARITY 1 (event_stage, action, event_id_group_1, current_time_fl, event_time, not_existing_fl). (8-bs_{$bs}_attribute)
- ENGINE = ReplicatedReplacingMergeTree('/clickhouse/tables/{uuid}/{shard}', '{replica}', replacing_version). (8-bs_{$bs}_attribute)
- PARTITION BY toYYYYMM(transaction_time). (8-bs_{$bs}_attribute)
- ORDER BY (attribute_id, transaction_time, transaction_uuid). (8-bs_{$bs}_attribute)
- TTL toDateTime(insert_timestamp) + toIntervalDay(5). (8-bs_{$bs}_attribute)
- SETTINGS index_granularity = 8192. (8-bs_{$bs}_attribute)

### API и интеграции
- Таблица связана с фичей PPMON-1382 (передача метрик из ТМБС в ЗСМ в привязке к сервисам с агрегирующим расчетом на стороне ТМБС). (2-bs_{$bs}_attribute_table_distributed; 8-bs_{$bs}_attribute)
- Данные записываются в ClickHouse (insert_timestamp — время записи вычисления в ClickHouse). (2-bs_{$bs}_attribute_table_distributed; 8-bs_{$bs}_attribute)

### Открытые вопросы
- Для колонки replacing_version описание в документах отсутствует. (2-bs_{$bs}_attribute_table_distributed; 8-bs_{$bs}_attribute)
