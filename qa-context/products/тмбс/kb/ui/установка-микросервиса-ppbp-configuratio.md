# Установка микросервиса ppbp-configuration-service

> Установка микросервиса ppbp-configuration-service: подготовка хранилищ ключей для SSL-доступа к Kafka и настройка его переменных окружения (таблица 4.2.2-1).

### Описание
- В папку с ключами подложить keystore и truststore с ключами для доступа к Kafka, если она работает через SSL. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)

### API и интеграции
- Таблица 4.2.2-1 — переменные окружения ppbp-configuration-service (формат: назначение; по умолчанию; пример; обязательность): (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
1. JAVA_OPTS — параметры запуска JVM, включая настройки SSL-хранилищ; по умолчанию Xmx1G; пример Djavax.net.ssl.trustStorePassword=$(TRUSTSTORE_PASSWORD) -Djavax.net.ssl.trustStore=/opt/keystores/truststore.p13; обязательность: Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
2. KAFKA_BOOTSTRAP_SERVERS — адрес сервера Kafka; по умолчанию localhost:9092; пример (10.***.64.21:30195,10.***.64.26:30195,10.***.64.27:30195); обязательность: Да. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
3. KEYSTORE_LOCATION — путь к файлу keystore; по умолчанию null; пример /opt/keystores/keystore.p12; обязательность: Да. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
4. KEYSTORE_PASSWORD — пароль к keystore; по умолчанию null; пример secret(certificate-pkcs12-password)[password] visibility; обязательность: Да. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
5. TRUSTSTORE_LOCATION — путь к truststore; по умолчанию null; пример /opt/keystores/truststore.p12; обязательность: Да. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
6. TRUSTSTORE_PASSWORD — пароль к truststore; по умолчанию null; пример secret(certificate-pkcs12-password)[password]; обязательность: Да. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
7. LOGGING_CONFIG — путь к файлу конфигурации логирования; по умолчанию classpath:log4j2-kubernetes.xml; пример classpath:log4j2-local.xml; обязательность: Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
8. SERVER_PORT — HTTP-порт приложения; по умолчанию 8000; пример 8080; обязательность: Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
9. SPRING_CLOUD_STREAM_KAFKA_BINDER_CONFIGURATION_SECURITY_PROTOCOL — протокол безопасности для подключения к Kafka; по умолчанию SSL; пример SSL; обязательность: Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
10. SPRING_DATASOURCE_PASSWORD — пароль пользователя Postgres; по умолчанию null; пример secret(postgres-creds)[password] visibility; обязательность: Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
11. SPRING_DATASOURCE_URL — JDBC URL для подключения к БД Postgres; по умолчанию null; пример jdbc:postgresql://pgsql-shared-rw.shared:5432/trmonbs_config; обязательность: Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
12. SPRING_DATASOURCE_USERNAME — логин пользователя БД Postgres; по умолчанию null; пример secret(postgres-creds)[username] visibility; обязательность: Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
13. DATASOURCE_SCHEMA — наименование схемы подключения; по умолчанию null; пример config_service; обязательность: Да. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
14. RDBMS_DATASOURCE_URL — JDBC URL для подключения к БД Postgres; по умолчанию null; пример jdbc:postgresql://d5ppbp-pgc001lk.****.dev.***:5432/trmonbs_config; обязательность: Да. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
15. RDBMS_DATASOURCE_USERNAME — логин пользователя БД Postgres; по умолчанию null; пример ppbp_config_admin; обязательность: Да. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
16. RDBMS_DATASOURCE_PASSWORD — пароль пользователя БД Postgres; по умолчанию null; пример -; обязательность: Да. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)

### Открытые вопросы
- В таблице 4.2.2-1 пути truststore различаются: в JAVA_OPTS указан /opt/keystores/truststore.p13, в TRUSTSTORE_LOCATION — /opt/keystores/truststore.p12 (возможна опечатка в документе). (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- Заданы две группы параметров подключения к Postgres (SPRING_DATASOURCE_* — необязательные; RDBMS_DATASOURCE_* — обязательные); их соотношение в выдержке не описано. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
