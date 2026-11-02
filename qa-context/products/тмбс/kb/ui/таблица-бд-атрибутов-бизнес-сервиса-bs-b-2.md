# Таблица БД атрибутов бизнес-сервиса (bs_{$bs}_attribute_table_distributed)

> Таблица ClickHouse bs_{$bs}_attribute_table_distributed хранит результаты расчёта настраиваемых пользователем вычисляемых атрибутов бизнес-сервисов после реализации фичи PPMON-1382.

### Описание
- В таблице представлены результаты расчёта вычисляемых атрибутов бизнес-сервисов, которые пользователь может настроить в интерфейсе. (3-bs_{$bs}_attribute_table)
- В таблице хранятся вычисления атрибутов ПОСЛЕ реализации фичи PPMON-1382 ПП. ТМБС. Передача метрик из ТМБС в ЗСМ в привязке к сервисам с агрегирующим расчетом на стороне ТМБС. (3-bs_{$bs}_attribute_table)
- Название файла документа: 3-bs_{$bs}_attribute_table.pdf. В DDL приведён пример создаваемой таблицы default.bs_6606_attribute. (3-bs_{$bs}_attribute_table)

### Поля и элементы
Колонки (имя — тип — описание):
- transaction_type — String — ID БС. (3-bs_{$bs}_attribute_table)
- transaction_time — DateTime64(3, 'Europe/Moscow') — Время транзакции. (3-bs_{$bs}_attribute_table)
- transaction_uuid — UUID — uuid транзакции. (3-bs_{$bs}_attribute_table)
- transaction_attribute_value — Int32 — Вычисляемое значение атрибута. (3-bs_{$bs}_attribute_table)
- attribute_id — UInt32 — ID атрибута. (3-bs_{$bs}_attribute_table)
- attribute_name — String — Наименование атрибута. (3-bs_{$bs}_attribute_table)
- attribute_status — String — Статус атрибута. (3-bs_{$bs}_attribute_table)
- attribute_threshold_type — String — Значение threshold согласно настроенным интервалам. (3-bs_{$bs}_attribute_table)
- unit — String — Единица измерения значения. (3-bs_{$bs}_attribute_table)
- transaction_events_count — UInt16 — Количество событий транзакции, на которых расчитан атрибут. (3-bs_{$bs}_attribute_table)
- valid — Bool — Признак валидности записи. (3-bs_{$bs}_attribute_table)
- replacing_version — UInt16 — описание не указано. (3-bs_{$bs}_attribute_table)
- partial — Bool — true, если часть ключей событий транзакции невалидны, т.е. не участвовали в склейке. (3-bs_{$bs}_attribute_table)
- user_transaction_time — Nullable(DateTime64(3, 'Europe/Moscow')) — время транзакции, вычисление которого настраивается пользователем. (3-bs_{$bs}_attribute_table)
- insert_timestamp — DateTime64(3, 'Europe/Moscow') — Время записи вычисления в ClickHouse. (3-bs_{$bs}_attribute_table)
- service_id — Int4 — Идентификатор сервиса. По умолчанию NULL. (3-bs_{$bs}_attribute_table)
- <tech_attr> — Array — Дополнительный тех. атрибут, выбранный пользователем для переноса данных событий в таблицу атрибутов. (3-bs_{$bs}_attribute_table)

### Бизнес-правила и ограничения
- Пользователь может добавлять произвольное количество столбцов в таблицу исходя из своей бизнес-потребности. Столбцы определяются на уровне функции "дополнительные поля в вычисляемых атрибутах". (3-bs_{$bs}_attribute_table)
- В примере DDL такими полями являются event_stage, action, event_id_group_1 (в DDL также присутствуют current_time_fl, event_time, not_existing_fl). (3-bs_{$bs}_attribute_table)
- Значения по умолчанию в DDL: valid Bool DEFAULT toUInt8(1); partial Bool DEFAULT toUInt8(0); user_transaction_time DEFAULT NULL; replacing_version UInt16 DEFAULT if(toUInt8(valid), transaction_events_count, toUInt16(65535)); дополнительные поля Array(String) DEFAULT []. (3-bs_{$bs}_attribute_table)
- Параметры хранения (DDL): ENGINE = ReplicatedReplacingMergeTree('/clickhouse/tables/{uuid}/{shard}', '{replica}', replacing_version); PARTITION BY toYYYYMM(transaction_time); ORDER BY (attribute_id, transaction_time, transaction_uuid); TTL toDateTime(insert_timestamp) + toIntervalDay(5); SETTINGS index_granularity = 8192. (3-bs_{$bs}_attribute_table)
- Индексы (DDL): insert_timestamp_idx (insert_timestamp, minmax, GRANULARITY 4); user_transaction_time_idx (user_transaction_time, minmax, GRANULARITY 4); event_stage_set_100_index (event_stage, set(100), GRANULARITY 1); action_set_100_index (action, set(100), GRANULARITY 1); event_id_group_1_set_100_index (event_id_group_1, set(100), GRANULARITY 1); current_time_fl_set_100_index (current_time_fl, set(100), GRANULARITY 1); event_time_set_100_index (event_time, set(100), GRANULARITY 1); not_existing_fl_set_100_index (not_existing_fl, set(100), GRANULARITY 1). (3-bs_{$bs}_attribute_table)

### Открытые вопросы
- Для колонки replacing_version описание в документе не указано. (3-bs_{$bs}_attribute_table)
- В колонках таблицы service_id указан тип Int4 (в документе). (3-bs_{$bs}_attribute_table)
