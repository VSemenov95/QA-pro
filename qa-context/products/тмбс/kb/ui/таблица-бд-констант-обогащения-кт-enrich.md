# Таблица БД констант обогащения КТ (enrichment_constant)

> Таблица БД enrichment_constant хранит константы (имя и значение), привязанные к контрольной точке (checkpoint).

### Описание
- Документ «2-enrichment_constant.pdf» описывает структуру таблицы БД с константами, связанными с контрольной точкой (имя таблицы — по названию файла: enrichment_constant). (2-enrichment_constant)
- Раздел «Назначение таблицы» в документе не заполнен: указано «????». (2-enrichment_constant)

### Поля и элементы
Структура таблицы (Название поля / Тип данных / Описание / Ограничения):
- id — SERIAL(INT4) — Уникальный идентификатор записи — PK (2-enrichment_constant)
- name — TEXT — Название константы — NOT NULL (2-enrichment_constant)
- value — TEXT — Значение константы — NULLABLE (2-enrichment_constant)
- checkpoint_id — INT4 — Связь с контрольной точкой — NOT NULL (FK) (2-enrichment_constant)

### Бизнес-правила и ограничения
- Primery Key: id; (2-enrichment_constant)
- Foreign Key: checkpoint_id -> checkpoint.id (2-enrichment_constant)
- name обязательно (NOT NULL); value может быть пустым (NULLABLE); checkpoint_id обязательно (NOT NULL). (2-enrichment_constant)

### Открытые вопросы
- Назначение таблицы не описано (в документе стоит «????»). (2-enrichment_constant)
