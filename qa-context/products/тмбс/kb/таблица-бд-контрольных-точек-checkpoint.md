# Таблица БД контрольных точек (checkpoint)

> Таблица БД контрольных точек (checkpoint) хранит данные о контрольных точках мониторинга бизнес-сервисов, связанных с информационной системой, источником данных и карточкой мониторинга.

### Описание
- Назначение таблицы: хранит информацию о контрольных точках (checkpoints) для мониторинга бизнес-сервисов. Каждая контрольная точка связана с информационной системой, источником данных и карточкой мониторинга. (checkpoint-4)
- Название таблицы в явном виде во фрагменте не указано. (checkpoint-4)

### Поля и элементы
Структура таблицы (поле — тип; описание; ограничения):
- id — SERIAL (INT4); уникальный идентификатор записи; PK. (checkpoint-4)
- name — TEXT; название контрольной точки; NULLABLE (в документе пометка «зачем?»). (checkpoint-4)
- status — ENUM; статус контрольной точки; NOT NULL. Доступные для обработки значения: DRAFT, IN_ANALYSIS, CONNECTED, IN_WORK, MONITORING, DISCONNECTED, DISCONNECTED_MANUAL. DEFAULT: DRAFT. (checkpoint-4)
- mandatory — BOOLEAN; признак обязательности контрольной точки; NOT NULL; DEFAULT: FALSE. (checkpoint-4)
- inf_system_id — INT4; связь с информационной системой; NOT NULL (FK). (checkpoint-4)
- monitoring_object — TEXT; объект мониторинга; NULLABLE. (checkpoint-4)
- process_step — TEXT; шаг процесса, на котором появляется контрольная точка; NULLABLE. (checkpoint-4)
- monitoring_desc — TEXT; описание логики мониторинга; NULLABLE. (checkpoint-4)
- description — TEXT; общее описание контрольной точки; NULLABLE. (checkpoint-4)
- data_source_row_id — INT4; связь с источником данных; NULLABLE (FK). (checkpoint-4)
- monitoring_card_row_id — INT8; связь с карточкой мониторинга; NOT NULL (FK). (checkpoint-4)
- checkpoint_id — INT4; уникальный идентификатор контрольной точки в рамках мониторинга; NOT NULL. (checkpoint-4)
- parent_id — INT4; связь с родительской контрольной точкой; NULLABLE. (checkpoint-4)
- type — VARCHAR; тип контрольной точки; NOT NULL. Допустимые значения: TRANSACTIONAL, REGISTER, COMBINED. (checkpoint-4)

### Бизнес-правила и ограничения
- Primary Key: id (автоинкремент). (checkpoint-4)
- Foreign Key: inf_system_id -> information._system.id (так в документе); data_source_row_id -> data_source.row_id; monitoring_card_row_id -> monitoring_card.row_id; parent_id -> checkpoint_id (рекурсивная связь). (checkpoint-4)

### Открытые вопросы
- У поля name в ограничениях стоит пометка «NULLABLE (зачем?)». (checkpoint-4)
- В описании внешнего ключа указано «information._system.id» (возможная опечатка в документе). (checkpoint-4)
