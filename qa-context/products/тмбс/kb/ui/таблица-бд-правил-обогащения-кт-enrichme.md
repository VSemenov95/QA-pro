# Таблица БД правил обогащения КТ (enrichment_rule)

> Таблица БД enrichment_rule хранит правила обогащения контрольных точек (КТ), связывая каждую контрольную точку с техническим атрибутом.

### Описание
- Назначение таблицы: «Таблица для хранения правил обогащения в КТ». (2-enrichment_rule)
- Название таблицы в тексте фрагмента не указано; имя файла документа — 2-enrichment_rule.pdf. (2-enrichment_rule)

### Поля и элементы
| Название поля | Тип данных | Описание | Ограничения |
|---|---|---|---|
| id | SERIAL(INT4) | Уникальный идентификатор записи | PK |
| checkpoint_id | INT4 | Связь с контрольной точкой | NOT NULL (FK) |
| technical_attribute_id | INT4 | Связь с техническим атрибутов | NOT NULL (FK) |
(2-enrichment_rule)

### Бизнес-правила и ограничения
- Primary Key (в документе написано «Primery Key»): id. (2-enrichment_rule)
- Foreign Key: checkpoint_id -> checkpoint.id. (2-enrichment_rule)
- Foreign Key: technical_attribute_id -> technical_attribute.id. (2-enrichment_rule)
- Поля checkpoint_id и technical_attribute_id обязательны (NOT NULL). (2-enrichment_rule)
- Каждая запись связывает контрольную точку с техническим атрибутом. (2-enrichment_rule)
