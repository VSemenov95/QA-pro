# Таблица БД общих вычисляемых атрибутов (general_computed_attribute)

> Таблица БД general_computed_attribute хранит информацию о вычисляемых атрибутах типа «Общие»: SQL-скрипт и связь с единицей измерения.

### Описание
- Назначение таблицы: хранит информацию о вычисляемых атрибутах типа "Общие". (2-general_computed_attribute)

### Поля и элементы
- Структура таблицы (название поля, тип данных, описание, ограничения): (2-general_computed_attribute)
- id — INT4 — Уникальный идентификатор записи — PK (2-general_computed_attribute)
- script — TEXT — SQL-Скрипт — NULLABLE (2-general_computed_attribute)
- unit_id — INT4 — Единица измерения (связь) — NOT NULL (FK) (2-general_computed_attribute)

### Бизнес-правила и ограничения
- Ключи и индексы: Primery Key: id; Foreign Key: unit_id -> dictionary_attribute_unit.id (2-general_computed_attribute)
- Поле script может быть пустым (NULLABLE). (2-general_computed_attribute)
- Поле unit_id обязательно (NOT NULL) и ссылается на поле id таблицы dictionary_attribute_unit. (2-general_computed_attribute)
