# Таблица БД источников данных (data_source)

> Таблица БД data_source хранит информацию об источниках данных: название, статус, тип подключения, настройки обогащения и дедупликации, версионирование, блокировку и связь с родительским источником.

### Описание
- Назначение таблицы: «Хранит информацию об источниках данных». (2-data_source)
- Название таблицы в явном виде во фрагменте не указано; по внешнему ключу parent_id -> data_source.row_id это data_source (файл «2-data_source.pdf»). (2-data_source)

### Поля и элементы
Структура таблицы (поле, тип, описание, ограничения):
- row_id, INT4: уникальный идентификатор записи. PK. (2-data_source)
- name, TEXT: название источника данных. NOT NULL. (2-data_source)
- status, ENUM: статус источника. NULLABLE. Доступные значения: DRAFT, IN_ANALYSIS, IN_WORK, CONNECTED, DISCONNECTED, INCIDENT. (2-data_source)
- description, TEXT: описание назначения источника. NULLABLE. (2-data_source)
- message_template, TEXT: пример сообщения источника. NULLABLE. (2-data_source)
- connector_type, ENUM: тип подключения. NOT NULL, DEFAULT: KAFKA. Допустимые значения: KAFKA, ASTROM_KEY. (2-data_source)
- template, BOOLEAN: признак, что источник является шаблоном (в документе после описания стоит «(?)»). NOT NULL, DEFAULT: false. (2-data_source)
- split_enable, BOOLEAN: включение обогащение данных (формулировка документа). NOT NULL, DEFAULT: false. (2-data_source)
- split_type, ENUM: тир обогащения (формулировка документа). NOT NULL, DEFAULT: WITHOUT_ENRICHMENT. Допустимые значения: WITHOUT_ENRICHMENT, WITH_ENRICHMENT. (2-data_source)
- split_path, TEXT: json-path для разделения данных. NULLABLE. (2-data_source)
- duplication_ttl, INT4: время действия дедупликации. NOT NULL, DEFAULT: 86400. (2-data_source)
- data_source_id, INT4: идентификатор источника данных. NOT NULL. (2-data_source)
- version, INT4: версия источника данных (в документе «Верия источника данных»). NOT NULL. (2-data_source)
- create_user_id, INT4: идентификатор пользователя, создавшего запись. NULLABLE (FK). (2-data_source)
- create_date, TIMESTAMP: дата создания записи. NOT NULL. (2-data_source)
- modify_user_id, INT4: идентификатор пользователя, отредактировавшего запись (источник). NULLABLE (FK). (2-data_source)
- modify_date, TIMESTAMP: дата и время последнего изменения записи. NOT NULL. (2-data_source)
- comment, TEXT: комментарий к источнику данных. NULLABLE. (2-data_source)
- is_locked, BOOLEAN: признак блокировки источника данных. NOT NULL. (2-data_source)
- parent_id, INT8: связь с родительским источником. NULLABLE (FK). (2-data_source)

### Бизнес-правила и ограничения
- Primary Key: row_id. (2-data_source)
- UNIQUE INDEX: пара значений (data_source_id, version) должна быть уникальной. (2-data_source)
- Foreign Key: create_user_id -> users.id; modify_user_id -> users.id; parent_id -> data_source.row_id. (2-data_source)

### Открытые вопросы
- Назначение поля template помечено знаком вопроса: «Признак, что источник является шаблоном (?)». (2-data_source)
