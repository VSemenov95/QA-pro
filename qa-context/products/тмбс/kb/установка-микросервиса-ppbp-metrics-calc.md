# Установка микросервиса ppbp-metrics-calculator-service

> Установка микросервиса ppbp-metrics-calculator-service: добавление keystore/truststore для Kafka по SSL и настройка 57 переменных окружения (таблица 4.2.11-1).

### Описание
- Микросервис ppbp-metrics-calculator-service (раздел 4.2.11). Необходимо учесть переменные среды из таблицы 4.2.11-1 «Данные переменных окружения ppbp-metrics-calculator-service». (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)

### Поля и элементы
Формат: № ИМЯ — описание; по умолчанию; пример; обязательность.
1. JAVA_OPTS — Параметры запуска JVM, включая настройки SSL-хранилищ; Xmx1G; Djavax.net.ssl.trustStorePassword=$(TRUSTSTORE_PASSWORD) -Djavax.net.ssl.trustStore=/opt/keystores/truststore.p12; Нет.
2. KAFKA_BOOTSTRAP_SERVERS — Адрес сервера Kafka; localhost:9092; (10.***.64.21:30195,10.***.64.26:30195,10.***.64.27:30195); Да.
3. KEYSTORE_LOCATION — Путь к файлу хранилища ключей keystore; null; /opt/keystores/keystore.p12; Да.
4. KEYSTORE_PASSWORD — Пароль к keystore; null; secret(certificate-pkcs12-password)[password] visibility; Да.
5. TRUSTSTORE_LOCATION — Путь к truststore; null; /opt/keystores/truststore.p12; Да.
6. TRUSTSTORE_PASSWORD — Пароль к truststore; null; secret(certificate-pkcs12-password)[password]; Да.
7. LOGGING_CONFIG — Путь к файлу конфигурации логирования; classpath:log4j2-kubernetes.xml; classpath:log4j2-local.xml; Нет.
8. LOGGING_LEVEL_ROOT — Уровень логирования; info; debug; Нет.
9. LOGGING_HOST — Адрес fluent-bit (агент сбора и маршрутизации логов) при использовании встроенного log4j2-kubernetes.xml; null; 127.0.0.1; Да.
10. APPLICATION_NAME — Имя приложения; null; ppbp-metrics-calculator-service; Да.
11. DATASOURCE_SCHEMA — Схема БД; null; metrics; Да.
12. MODE — Режим работы приложения; full; metrics; Нет.
13. RDBMS_DATASOURCE_URL — JDBC URL Postgres; null; pg_pass; Да.
14. RDBMS_DATASOURCE_USERNAME — Логин пользователя Postgres; null; jdbc:postgresql://localhost:5432/mydb; Да.
15. RDBMS_DATASOURCE_PASSWORD — Пароль пользователя Postgres; null; pg_user; Да.
16. SERVER_PORT — HTTP-порт; 8000; 8080; Нет.
17. SPRING_AUTOCONFIGURE_EXCLUDE — Исключенные автосборщики Spring Boot; null; org.springframework.boot.autoconfigure.jdbc.DataSourceAutoConfiguration; Нет.
18. TM_CLICKHOUSE_NODEADDRESSES — Список адресов нод clickhouse через запятую; null; host1:8113,host2:8123; Да.
19. TM_CLICKHOUSE_CREDENTIALS_ENABLED — Флаг аутентификации ClickHouse; true; false; Нет.
20. TM_CLICKHOUSE_CREDENTIALS_PASSWORD — Пароль ClickHouse; null; ch_pass; Нет.
21. TM_CLICKHOUSE_CREDENTIALS_USERNAME — Имя пользователя ClickHouse; null; ch_user; Нет.
22. TM_CLICKHOUSE_SSLENABLED — Флаг SSL для ClickHouse; true; true; Нет.
23. TM_CONFIG_ZCM_ENABLED — Флаг интеграции с ZCM (Zero Code Management); true; false; Нет.
24. TM_KAFKA_SSL_ENABLED — Флаг SSL для Kafka; true; false; Нет.
25. TM_METRICS_ZCM_INTEGRATION_KAFKA_PRODUCER_PROPERTIES_SECURITY_PROTOCOL — Протокол безопасности продюсера Kafka в интеграции ZCM; null; PLAINTEXT; Нет.
26. TM_MODE — Режим работы TM (Transaction Manager или аналог); full; default; Нет.
27. TM_REDIS_HOST — Хост Redis; d5ppbp-rdc001lk.corp.dev.***; localhost; Нет.
28. TM_REDIS_PASSWORD — Пароль Redis; по умолчанию в документе задана строка-пароль (не воспроизводится); redis_pass; Нет.
29. TM_REDIS_PORT — Порт Redis; 6379; 6379; Нет.
30. TM_TABLE_NAME_TEMPLATE_WITH_LAST_UPDATE_TIMESTAMP (имя переменной в части 2 не показано) — Шаблон имени таблицы с временной меткой последнего обновления; null; table_name_{timestamp}; Да.
31. MQ_KAFKA_EXPORT_TO_ZSM_BOOTSTRAP_SERVERS — Адреса нод Kafka для интеграции с ЗСМ; localhost9090 (так в документе); 10.0.0.1:9092; Нет.
32. MQ_KAFKA_EXPORT_TO_ZSM_TOPIC — Топики Kafka для ЗСМ; default; export_topic; Нет.
33. MQ_KAFKA_EXPORT_TO_ZSM_KEYSTORE_LOCATION — Расположение keystore для ЗСМ; default; /etc/ssl/certs/keystore.p12; Нет.
34. MQ_KAFKA_EXPORT_TO_ZSM_KEYSTORE_PASSWORD — Пароль keystore для ЗСМ; default; my_secure_password; Нет.
35. MQ_KAFKA_EXPORT_TO_ZSM_TRUSTSTORE_LOCATION — Расположение truststore для ЗСМ; default; /etc/ssl/certs/truststore.p12; Нет.
36. MQ_KAFKA_EXPORT_TO_ZSM_TRUSTSTORE_PASSWORD — Пароль truststore для ЗСМ; default; truststore_pass; Нет.
37. CONFIG_BS_METRIC_NAME — metric_name цепочки сервисов (БС) в конфигурации; ppbp_service_chain; service_chain_name; Нет.
38. CONFIG_RIS_CODE — ris_code в конфигурации; 9998; 9998; Нет.
39. CONFIG_SUB_RIS_CODE — subsystem_code в конфигурации; 0; 0; Нет.
40. LOGGING_LEVEL_RU_T1_SFERA_TM_METRICS_SCHEDULLER_SERVICE_METRICS — Управляет логированием классов заданного пакета/подпакета LOGGING_LEVEL_; info; debug; Нет.
41. TM_TASKS_STARTER_MAX_INSTANCES_COUNT — максимальное количество планируемых инстансов микросервисов; 2; 1; Нет.
42. TM_KAFKA_BATCHSIZE — Размер пакета (байт) для отправки в Kafka; null; 256000; Нет.
43. TM_KAFKA_LINGERMS — Время ожидания перед отправкой пакета (мс); null; 15000; Нет.
44. TM_REDIS_SENTINEL_ENABLED — Переключение на Redis Sentinel (вместо обычного Redis); false; false; Нет.
45. TM_VALIDATION_STRICT — Проводить ли валидацию результата запроса метрик на соответствие типов данных типам в БД Clickhouse; false; false; Нет.
46. TM_CLICKHOUSE_MAXCONNECTIONS — Максимум подключений к ClickHouse; 10; «-»; Нет.
47. TM_REDIS_LOCKS_WAIT_TIME — время ожидания блокировки при получении списка метрик на расчет; 5000; «-»; Нет.
48. TM_REDIS_LOCKS_LEASE_TIME — максимальное время жизни блокировки. Рекомендуемое значение '60000'; 15000; 60000; Нет.
49. TM_REDIS_LOCKS_LOCK_ATTEMPTS — количество попыток блокировки; 5; «-»; Нет.
50. TM_TASKS_STARTER_ENABLED — Режим запуска нескольких подов микросервиса (сейчас используется только этот режим); true; «-»; Нет.
51. TM_TASKS_STARTER_RETRIES_COUNT — Количество попыток выполнить задачу. Для метрик не используется, но должен быть > 0; 2; «-»; Нет.
52. TM_TASKS_STARTER_RETRY_INTERVAL_MS — Интервал между повторами «неуспешной» задачи; 3000; «-»; Нет.
53. TM_TASKS_EXECUTOR_CORE_POOL_SIZE — Стартовый размер пула потоков; 1; «-»; Нет.
54. TM_TASKS_STARTER_EXECUTOR_MAX_POOL_SIZE — Максимальный размер пула потоков; 3; «-»; Нет.
55. TM_TASKS_STARTER_EXECUTOR_QUEUE_CAPACITY — Размер очереди задач, если все потоки заняты; 100; «-»; Нет.
56. CONFIG_MONITORING_EVENT_CRON — Cron-расписание задачи расчета пороговых метрик; 0 * * * * *; 0 0 * * * *; Нет.
57. TM_CLICKHOUSE_DATABASE_NAME — Имя БД Clickhouse; default; «-»; Нет.
(Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)

### Бизнес-правила и ограничения
- В контейнер необходимо добавить keystore и truststore с ключами для доступа к Kafka, если она работает через SSL. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)

### API и интеграции
- ZCM (Zero Code Management): включается TM_CONFIG_ZCM_ENABLED; протокол безопасности продюсера Kafka — TM_METRICS_ZCM_INTEGRATION_KAFKA_PRODUCER_PROPERTIES_SECURITY_PROTOCOL. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- Интеграция с ЗСМ через Kafka: переменные MQ_KAFKA_EXPORT_TO_ZSM_* (адреса нод, топик, keystore/truststore и пароли). (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- Redis: Sentinel-режим, параметры блокировок (WAIT_TIME, LEASE_TIME, LOCK_ATTEMPTS). ClickHouse: максимум подключений, имя БД, строгая валидация типов. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)

### Открытые вопросы
- Примеры для RDBMS_DATASOURCE_URL (pg_pass), RDBMS_DATASOURCE_USERNAME (jdbc:postgresql://localhost:5432/mydb) и RDBMS_DATASOURCE_PASSWORD (pg_user) не соответствуют описаниям; приведено как в документе. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
