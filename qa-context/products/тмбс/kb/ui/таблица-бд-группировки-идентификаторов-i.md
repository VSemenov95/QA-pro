# Таблица БД группировки идентификаторов (identifier_group)

> Таблица БД identifier_group предназначена для группировки идентификаторов и связана с карточкой мониторинга через внешний ключ monitoring_card_row_id.

### Описание
- Назначение таблицы: группировка идентификаторов. (2-(R) identifier_group)
- Название таблицы в самом фрагменте явно не указано; имя файла документа: «2-(R) identifier_group.pdf». (2-(R) identifier_group)

### Поля и элементы
Структура таблицы (название поля · тип данных · значение по умолчанию · ограничения; колонка «Описание» в таблице пустая):
- id · serial4 · значение по умолчанию не указано · PK (2-(R) identifier_group)
- name · text · значение по умолчанию не указано · NOT_NULL (2-(R) identifier_group)
- monitoring_card_row_id · int8 · значение по умолчанию не указано · NOT_NULL (2-(R) identifier_group)
- identifier_group_id · int4 · значение по умолчанию не указано · NOT_NULL (2-(R) identifier_group)
- parent_id · int4 · значение по умолчанию не указано · ограничений не указано (2-(R) identifier_group)
- identifier_type · varchar · значение по умолчанию TRANSACTIONAL · NOT_NULL (2-(R) identifier_group)

### Бизнес-правила и ограничения
- Primary Key: id (автоинкремент). (2-(R) identifier_group)
- Foreign Key: monitoring_card_row_id -> monitoring_card.row_id. (2-(R) identifier_group)
- Поля name, monitoring_card_row_id, identifier_group_id, identifier_type имеют ограничение NOT_NULL. (2-(R) identifier_group)
- Для поля identifier_type значение по умолчанию — TRANSACTIONAL. (2-(R) identifier_group)
- Поле parent_id (int4) без ограничений. (2-(R) identifier_group)
