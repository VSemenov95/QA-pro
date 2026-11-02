# Таблица БД информационных систем (information_system)

> Таблица БД information_system хранит список информационных систем продукта «ТМБС» (поля, типы, ограничения и первичный ключ).

### Описание
- Назначение таблицы: «Таблица списка информационных систем». (2-(R) information_system)
- Название таблицы в тексте фрагмента не указано явно; имя документа — «2-(R) information_system.pdf». (2-(R) information_system)

### Поля и элементы
Структура таблицы (поле — тип — значение по умолчанию — ограничения):
- id — serial4 — PK, NOT_NULL. (2-(R) information_system)
- external_id — text — NOT_NULL. (2-(R) information_system)
- code — text — NOT_NULL. (2-(R) information_system)
- name — text — NOT_NULL. (2-(R) information_system)
- description — text — NOT_NULL. (2-(R) information_system)
- create_date — timestamptz — NOT_NULL. (2-(R) information_system)
- modify_date — timestamptz — ограничений не указано. (2-(R) information_system)
- version — int4 — по умолчанию 1 — NOT_NULL. (2-(R) information_system)
- Описания полей в таблице не заполнены. (2-(R) information_system)

### Бизнес-правила и ограничения
- Поля id, external_id, code, name, description, create_date, version обязательны (NOT_NULL). (2-(R) information_system)
- Поле modify_date не имеет ограничения NOT_NULL. (2-(R) information_system)
- Поле version по умолчанию равно 1. (2-(R) information_system)
- Primery Key (так в документе): id (автоинкремент). Других ключей и индексов во фрагменте не указано. (2-(R) information_system)
