# Таблица БД ключевых атрибутов КТ (identifier)

> Таблица БД identifier хранит ключевые атрибуты контрольных точек (КТ), по которым сообщения сливаются в транзакцию.

### Описание
- Назначение таблицы: таблица ключевых атрибутов КТ, по которым происходит слияние сообщений в транзакцию. (3-(R) identifier)

### Поля и элементы
- `id` — тип serial4; описание: «Идентификатор записи»; значение по умолчанию: не указано; ограничения: PK, NOT_NULL. (3-(R) identifier)
- `group_id` — тип int4; описание: «Идентификатор группы»; значение по умолчанию: не указано; ограничения: NOT_NULL. (3-(R) identifier)
- `checkpoint_id` — тип int4; описание: «Идентификатор КТ»; значение по умолчанию: не указано; ограничения: NOT_NULL. (3-(R) identifier)
- `technical_attribute_id` — тип int4; описание: «Идентификатор тех атрибута»; значение по умолчанию: не указано; ограничения: NOT_NULL. (3-(R) identifier)
- `identifier_type` — тип varchar; описание: «Тип идентификатора»; значение по умолчанию: TRANSACTIONAL; ограничения: NOT_NULL. (3-(R) identifier)

### Бизнес-правила и ограничения
- Primery Key (так в документе): `id` (автоинкремент). (3-(R) identifier)
- Foreign Key: `group_id` -> `identifier_group.id`; `checkpoint_id` -> `checkpoint.id`; `technical_attribute_id` -> `technical_attribute.id`. (3-(R) identifier)
