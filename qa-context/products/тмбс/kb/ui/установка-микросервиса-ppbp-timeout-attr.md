# Установка микросервиса ppbp-timeout-attributes-service

> Установка микросервиса ppbp-timeout-attributes-service: добавление keystore/truststore для Kafka по SSL и настройка его переменных окружения (Kafka, ClickHouse, логирование, формат передачи данных).

### Описание
- Микросервис ppbp-timeout-attributes-service (раздел 4.2.10). В контейнер необходимо добавить keystore и truststore с ключами для доступа к Kafka, если она работает через SSL. Необходимо учесть переменные среды из таблицы 4.2.10-1 «Данные переменных окружения ppbp-timeout-attributes-service». (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)

### Поля и элементы
Формат: переменная — описание; по умолчанию; пример; обязательность. Таблица 4.2.10-1.
1. JAVA_OPTS — Параметры запуска JVM, включая настройки SSL-хранилищ; Xmx1G; Djavax.net.ssl.trustStorePassword=$(TRUSTSTORE_PASSWORD) -Djavax.net.ssl.trustStore=/opt/keystores/truststore.p12; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
2. KAFKA_BOOTSTRAP_SERVERS — Адрес сервера Kafka; localhost:9092; (10.***.64.21:30195,10.***.64.26:30195,10.***.64.27:30195); Да. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
3. KEYSTORE_LOCATION — Путь к файлу хранилища ключей keystore; null; /opt/keystores/keystore.p12; Да. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
4. KEYSTORE_PASSWORD — Пароль к файлу хранилища ключей keystore; null; secret(certificate-pkcs12-password)[password] visibility; Да. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
5. TRUSTSTORE_LOCATION — Путь к файлу хранилища ключей truststore; null; /opt/keystores/truststore.p12; Да. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
6. TRUSTSTORE_PASSWORD — Пароль к файлу хранилища ключей truststore; null; secret(certificate-pkcs12-password)[password]; Да. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
7. LOGGING_CONFIG — Путь к файлу с конфигурацией логирования; classpath:log4j2-kubernetes.xml; classpath:log4j2-local.xml; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
8. LOGGING_LEVEL_ROOT — Уровень логирования; info; debug; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
9. SERVER_PORT — HTTP-порт приложения; 8000; 8080; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
10. LOGGING_HOST — Адрес fluent-bit (агент для сбора и маршрутизации логов), на который отправляются логи, в случае использования встроенного log4j2-kubernetes.xml; null; 127.0.0.1; Да. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
11. SPRING_CLOUD_STREAM_KAFKA_BINDER_CONFIGURATION_SECURITY_PROTOCOL — Протокол безопасности для Kafka биндера; SSL; PLAINTEXT; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
12. SPRING_KAFKA_SECURITY_PROTOCOL — Протокол безопасности для стандартного клиента Spring Kafka; null; PLAINTEXT; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
13. TM_CLICKHOUSE_NODEADDRESSES — Содержит список адресов нод clickhouse, разделенных запятой; null; host1:8113,host2:8123; Да. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
14. TM_CLICKHOUSE_CREDENTIALS_ENABLED — Флаг включения аутентификации для ClickHouse; true; false; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
15. TM_CLICKHOUSE_CREDENTIALS_PASSWORD — Пароль для подключения к ClickHouse; null; ch_pass; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
16. TM_CLICKHOUSE_CREDENTIALS_USERNAME — Имя пользователя для подключения к ClickHouse; null; ch_user; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
17. TM_CLICKHOUSE_SSLENABLED — Флаг включения SSL для подключения к ClickHouse; true; true; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
18. TM_KAFKA_SSL_ENABLED — Флаг включения SSL для Kafka; true; false; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
19. TM_KAFKA_BATCHSIZE — Размер пакета (в байтах) для отправки сообщений в Kafka; null; 256000; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
20. TM_KAFKA_LINGERMS — Время ожидания перед отправкой пакета, чтобы накопить больше сообщений (в миллисекундах); null; 15000; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
21. TM_KAFKA_PRODUCER_COMPRESSIONTYPE — Тип сжатия данных для отправителя (producer); null; lz5; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
22. CONFLUENT_SCHEMA_REGISTRY_URL — Адрес реестра avro схем. Используется, если TM_KAFKA_TOCLICKSENDER_FORMAT=AVRO; http://localhost:8080; пример: не указан; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
23. TM_KAFKA_TOCLICKSENDER_FORMAT — Формат передачи данных в кафка → clickhouse. [JSON, AVRO]. Для AVRO необходимо настраивать реестр схем (параметр CONFLUENT_SCHEMA_REGISTRY_URL); JSON; AVRO; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
24. TM_CLICKHOUSE_DATABASE_NAME — Имя БД Clickhouse; default; -; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)

### Бизнес-правила и ограничения
- keystore и truststore добавляются в контейнер, если Kafka работает через SSL. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- Для TM_KAFKA_TOCLICKSENDER_FORMAT=AVRO необходимо настроить реестр схем (CONFLUENT_SCHEMA_REGISTRY_URL). (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
