# Таблица БД истории миграций (flyway_admin_schema_history)

> Таблица БД flyway_admin_schema_history хранит историю миграций базы данных (назначение в документе отмечено как неподтверждённое).

### Описание
- Назначение таблицы: «Хранит историю миграций бд (?)». Знак вопроса в исходном документе указывает на неуверенность в формулировке назначения. (2-flyway_admin_schema_history)
- Документ: «2-flyway_admin_schema_history.pdf». (2-flyway_admin_schema_history)

### Поля и элементы
| Название поля | Тип данных | Описание | Ограничения |
|---|---|---|---|
| installed_rank | INT4 | Уникальный идентификатор записи | PK |
| version | VARCHAR(30) | Версия миграции | NULLABLE |
| description | VARCHAR(200) | Описание миграции | NOT NULL |
| type | VARCHAR(20) | Тип миграции | NOT NULL |
| script | VARCHAR(100) | Имя скрипта | NOT NULL |
| checksum | INT4 | Контрольная сумма | NULLABLE |
| installed_by | VARCHAR(200) | Пользователь выполнивший миграцию | NOT NULL |
| installed_on | INT4 | Время выполнения миграции | NOT NULL |
| success | BOOLEAN | Признак успешности | NOT NULL |
(2-flyway_admin_schema_history)

### Бизнес-правила и ограничения
- Primery Key: installed_rank (написание «Primery Key» дословно из документа). (2-flyway_admin_schema_history)
- Поля version и checksum допускают NULL; остальные поля NOT NULL. (2-flyway_admin_schema_history)

### Открытые вопросы
- Назначение таблицы в документе отмечено знаком «(?)» — формулировка не подтверждена. (2-flyway_admin_schema_history)
- Поле installed_on («Время выполнения миграции») имеет тип INT4; формат значения в документе не указан. (2-flyway_admin_schema_history)
