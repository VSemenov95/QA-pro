# Таблица БД карточки мониторинга (monitoring_card)

> Таблица БД monitoring_card хранит карточки мониторинга: их структуру полей, статус, версию, признаки отправки во внешние системы и связи с бизнес-сервисами и пользователями.

### Описание
- Таблица карточки мониторинга; документ содержит структуру таблицы и перечень ключей. (monitoring_card-7)

### Поля и элементы
Формат: название поля — тип данных — описание — значение по умолчанию — ограничения.
- row_id — int8 — PK, NOT_NULL. (monitoring_card-7)
- name — text. (monitoring_card-7)
- bs_id — int4. (monitoring_card-7)
- status — mcard_status — по умолчанию DRAFT — NOT_NULL. (monitoring_card-7)
- create_date — timestamptz — NOT_NULL. (monitoring_card-7)
- modify_date — timestamptz — NOT_NULL. (monitoring_card-7)
- version — int4 — по умолчанию 1 — NOT_NULL. (monitoring_card-7)
- monitoring_card_id — int4 — NOT_NULL. (monitoring_card-7)
- create_user_id — int4. (monitoring_card-7)
- modify_user_id — int4. (monitoring_card-7)
- is_locked — bool — по умолчанию false — NOT_NULL. (monitoring_card-7)
- parent_id — int8. (monitoring_card-7)
- dashboard_link — varchar. (monitoring_card-7)
- merging_period — int4 — по умолчанию 1 — NOT_NULL. (monitoring_card-7)
- send_deviation — boolean — «Признак отправки отклонений и событий во внешние системы» — по умолчанию true — NOT_NULL. (monitoring_card-7)
- send_monitoring_events — boolean — «Признак отправки событий мониторинга» — по умолчанию true — NOT_NULL. (monitoring_card-7)
- send_metric — boolean — «Признак отправки метрик во внешние системы» — по умолчанию true — NOT_NULL. (monitoring_card-7)
- check_interval_minutes — int4 — «Частота проверки отклонений» — по умолчанию 1 — NULLABLE. (monitoring_card-7)

### Бизнес-правила и ограничения
- Foreign Key: bs_id -> busness_service.id (написание как в документе). (monitoring_card-7)
- Foreign Key: create_user_id -> users.id. (monitoring_card-7)
- Foreign Key: modify_user_id -> users.id. (monitoring_card-7)

### Расхождения между документами
- Первичный ключ: в таблице полей PK помечен row_id, а в разделе «Ключи и индексы» указан Primary Key «id (автоинкремент)» — названия различаются. (monitoring_card-7)
