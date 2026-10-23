# Таблица БД интервалов метрик (metric_interval)

> Таблица БД metric_interval хранит значения критичности (интервалы min/max) метрик Бизнес-сервиса и Сервиса и связывается внешними ключами с таблицами metric и metric_service.

### Описание
- Таблица предназначена для хранения значений Критичности метрик Бизнес-сервиса и Сервиса. (3-(R) metric_interval)
- Название таблицы в документе явно не указано; имя файла — «3-(R) metric_interval.pdf». (3-(R) metric_interval)

### Поля и элементы
Структура таблицы (поле · тип · описание · значение по умолчанию · ограничения):
- id · serial4 · Идентификатор записи · по умолчанию не указано · PK, NOT_NULL (3-(R) metric_interval)
- type · metric_interval_type · Тип критичности · по умолчанию не указано · NOT_NULL (3-(R) metric_interval)
- active · bool · Признак включения критичности для метрики · значение по умолчанию и ограничения не указаны (3-(R) metric_interval)
- min_value · int8 · Минимальное значение · значение по умолчанию и ограничения не указаны (3-(R) metric_interval)
- max_value · int8 · Максимальное значение · значение по умолчанию и ограничения не указаны (3-(R) metric_interval)
- metric_id · int4 · Идентификатор метрики Бизнес-Сервиса · по умолчанию не указано · NOT_NULL (3-(R) metric_interval)
- metric_service_id · int4 · Идентификатор метрики Сервиса · значение по умолчанию «-» · NOT_NULL (3-(R) metric_interval)

### Бизнес-правила и ограничения
- Primery Key: id (автоинкремент). (3-(R) metric_interval)
- Foreign Key: metric_id -> metric.id; metric_service_id -> metric_service.id. (3-(R) metric_interval)
- Поля metric_id и metric_service_id помечены NOT_NULL. (3-(R) metric_interval)
