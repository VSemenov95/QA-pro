# Таблица БД истории миграций (flyway_schema_history)

> Таблица БД flyway_schema_history хранит историю миграций базы данных продукта «ТМБС» (назначение в документе не подтверждено).

### Описание
- Назначение таблицы: «Хранит историю миграций бд (?)». В документе назначение отмечено знаком вопроса, то есть формулировка не подтверждена. (2-flyway_schema_history)
- Название таблицы взято из имени документа: «2-flyway_schema_history.pdf». (2-flyway_schema_history)

### Поля и элементы
Структура таблицы (название поля, тип данных, описание, ограничения):
- installed_rank, INT4, Уникальный идентификатор записи, PK (2-flyway_schema_history)
- version, VARCHAR(30), Версия миграции, NULLABLE (2-flyway_schema_history)
- description, VARCHAR(200), Описание миграции, NOT NULL (2-flyway_schema_history)
- type, VARCHAR(20), Тип миграции, NOT NULL (2-flyway_schema_history)
- script, VARCHAR(100), Имя скрипта, NOT NULL (2-flyway_schema_history)
- checksum, INT4, Контрольная сумма, NULLABLE (2-flyway_schema_history)
- installed_by, VARCHAR(200), Пользователь выполнивший миграцию, NOT NULL (2-flyway_schema_history)
- installed_on, INT4, Время выполнения миграции, NOT NULL (2-flyway_schema_history)
- installed_time, INT4, Время выполнения миграции (в мс), NOT NULL (2-flyway_schema_history)
- success, BOOLEAN, Признак успешности, NOT NULL (2-flyway_schema_history)

### Бизнес-правила и ограничения
- Ключи и индексы: Primery Key: installed_rank (написание «Primery» приведено как в документе). (2-flyway_schema_history)
- Поля version и checksum допускают NULL; остальные поля, кроме installed_rank (PK), имеют ограничение NOT NULL. (2-flyway_schema_history)

### Открытые вопросы
- Назначение таблицы указано с вопросительным знаком: «Хранит историю миграций бд (?)». (2-flyway_schema_history)
- Для installed_on указан тип INT4 и описание «Время выполнения миграции», совпадающее по смыслу с описанием installed_time; формат значения в документе не уточнён. (2-flyway_schema_history)
