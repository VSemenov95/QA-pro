# Таблица БД вычисляемых атрибутов (computed_attribute)

> Таблица БД computed_attribute хранит информацию о вычисляемых атрибутах: их название, описание, методику расчета, статус, связь с карточкой мониторинга, родительским атрибутом и тип транзакции.

### Описание
- Назначение таблицы: «Хранит информацию о вычисляемых атрибутах». (2-computed_attribute)
- Название таблицы в тексте фрагмента явно не указано; имя computed_attribute следует из названия документа «2-computed_attribute.pdf» и из внешнего ключа parent_id -> computed_attribute.id. (2-computed_attribute)

### Поля и элементы
Таблица: название поля, тип данных, описание, ограничения.
- id: INT4; уникальный идентификатор записи; PK. (2-computed_attribute)
- name: TEXT; название вычисляемого атрибута; NOT NULL. (2-computed_attribute)
- description: TEXT; описание назначения атрибута; NULLABLE. (2-computed_attribute)
- calculation_method: TEXT; методика расчета; NULLABLE. (2-computed_attribute)
- status: ENUM; статус атрибута; NOT NULL. Допустимые значения: DRAFT, IN_WORK, CONNECTED, MONITORING, DISCONNECTED, DISCONNECTED_MANUAL. (2-computed_attribute)
- monitoring_card_row_id: INT8; связь с карточкой мониторинга; NOT NULL (FK). (2-computed_attribute)
- computed_attribute_id: INT4; идентификатор вычисляемого атрибута; NOT NULL. (2-computed_attribute)
- parent_id: INT4; связь с родительским выч. атрибутом; NULLABLE (FK). (2-computed_attribute)
- transaction_type: VARCHAR; тип транзакции; NOT NULL, DEFAULT 'TRANSACTIONAL'. Допустимые значения: TRANSACTIONAL, REGISTRY. (2-computed_attribute)

### Бизнес-правила и ограничения
- Primary Key: id. (2-computed_attribute)
- Foreign Key: monitoring_card_row_id -> monitoring_card.row_id. (2-computed_attribute)
- Foreign Key: parent_id -> computed_attribute.id (рекурсивная связь). (2-computed_attribute)
