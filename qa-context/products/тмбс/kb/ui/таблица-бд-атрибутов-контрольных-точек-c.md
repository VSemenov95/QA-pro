# Таблица БД атрибутов контрольных точек (checkpoint_attribute)

> Таблица БД checkpoint_attribute хранит атрибуты контрольных точек: их связь с контрольной точкой и техническим атрибутом, признак ключевого идентификатора, тип идентификатора и код атрибута поиска.

### Описание
- Назначение таблицы: «Хранит атрибуты контрольных точек». (7-checkpoint_attribute)
- Название таблицы в тексте фрагмента не указано; имя файла документа — «7-checkpoint_attribute.pdf». (7-checkpoint_attribute)

### Поля и элементы
Структура таблицы (поле · тип данных · описание · ограничения):
- id · SERIAL (INT4) · «Уникальный идентификатор записи» · PK. (7-checkpoint_attribute)
- name · TEXT · «Название атрибута» · NULLABLE (в документе пометка: «зачем?»). (7-checkpoint_attribute)
- checkpoint_id · INT4 · «Связь с контрольной точкой» · NOT NULL (FK). (7-checkpoint_attribute)
- description · TEXT · «Описание назначения атрибута» · NULLABLE. (7-checkpoint_attribute)
- key_identifier · BOOLEAN · Признак "Ключевой идентификатор" · NOT NULL, DEFAULT: FALSE. (7-checkpoint_attribute)
- technical_attribute_id · INT4 · «Связь с техническим атрибутом» · NULLABLE (FK). (7-checkpoint_attribute)
- identifier_type · VARCHAR · «Тип идентификатора» · NOT NULL. Допустимые значения: TRANSACTIONAL, REGISTER. (7-checkpoint_attribute)
- search_attribute_code · string · «Код атрибута поиска» · NULLABLE. (7-checkpoint_attribute)

### Бизнес-правила и ограничения
- id — первичный ключ (автоинкремент). (7-checkpoint_attribute)
- checkpoint_id — обязательное поле (NOT NULL), внешний ключ. (7-checkpoint_attribute)
- technical_attribute_id — необязательное поле (NULLABLE), внешний ключ. (7-checkpoint_attribute)
- key_identifier — обязательное, по умолчанию FALSE. (7-checkpoint_attribute)
- identifier_type — обязательное, допустимые значения только TRANSACTIONAL и REGISTER. (7-checkpoint_attribute)
- Primery Key: id (автоинкремент). (7-checkpoint_attribute)
- Foreign Key: перечень в документе не приведён (раздел обрывается на «Foreign Key:»). (7-checkpoint_attribute)

### Открытые вопросы
- Для поля name указано «NULLABLE (зачем?)» — необходимость поля под вопросом. (7-checkpoint_attribute)
- Перечень внешних ключей в разделе «Ключи и индексы» не заполнен. (7-checkpoint_attribute)
