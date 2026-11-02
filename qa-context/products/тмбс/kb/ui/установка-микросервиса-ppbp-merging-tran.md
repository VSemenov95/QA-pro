# Установка микросервиса ppbp-merging-transactions-service

> Установка микросервиса ppbp-merging-transactions-service (раздел 4.2.8): добавление keystore/truststore для Kafka по SSL и настройка переменных окружения (Kafka, Redis, Scylla, потоки, восстановление транзакций, топики БС).

### Описание
- Микросервис ppbp-merging-transactions-service (раздел 4.2.8). В контейнер необходимо добавить keystore и truststore с ключами для доступа к Kafka, если она работает через SSL. Нужно учесть переменные среды из таблицы 4.2.8-1 «Данные переменных окружения ppbp-merging-transactions-service». (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)

### Поля и элементы
Колонки таблицы 4.2.8-1: №, Переменная окружения, Описание, Значение по умолчанию, Пример, Обязательность. Формат: переменная — описание; по умолчанию; пример; обязательность.
**Общие, JVM, логирование**
- JAVA_OPTS — параметры запуска JVM, включая настройки SSL-хранилищ; Xmx1G; Djavax.net.ssl.trustStorePassword=$(TRUSTSTORE_PASSWORD) -Djavax.net.ssl.trustStore=/opt/keystores/truststore.p12; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- LOGGING_CONFIG — путь к файлу конфигурации логирования; classpath:log4j2-kubernetes.xml; classpath.xml; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- LOGGING_LEVEL_ROOT — уровень логирования; info; debug; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- LOGGING_HOST — адрес fluent-bit (агент сбора и маршрутизации логов), на который отправляются логи, при использовании встроенного log4j2-kubernetes.xml; null; 127.0.0.1; Да. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- SERVER_PORT — HTTP-порт приложения; 8000; 8080; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
**Kafka и SSL**
- KAFKA_BOOTSTRAP_SERVERS — адрес сервера Kafka; null; 10.0.0.1:9092,10.0.0.2:9092; Да.
- KEYSTORE_LOCATION — путь к keystore; null; /etc/ssl/certs/keystore.p12; Да.
- KEYSTORE_PASSWORD — пароль к keystore; null; my_secure_password; Да.
- TRUSTSTORE_LOCATION — путь к truststore; null; /etc/ssl/certs/truststore.p12; Да.
- TRUSTSTORE_PASSWORD — пароль к truststore; null; truststore_pass; Да.
- SPRING_CLOUD_STREAM_KAFKA_BINDER_CONFIGURATION_SECURITY_PROTOCOL — протокол безопасности Kafka биндера; SSL; PLAINTEXT; Нет.
- TM_KAFKA_SSL_ENABLED — флаг включения SSL для Kafka; true; false; Нет.
- TM_KAFKA_FETCHMINBYTES — мин. байт для получения от брокера; null; 256000; Нет.
- TM_KAFKA_MAXPOLLRECORDS — макс. записей за один poll(); null; 5000; Нет.
- TM_KAFKA_BATCHSIZE — размер пакета (байт) для отправки; null; 256000; Нет.
- TM_KAFKA_FETCHMAXWAITMS — макс. время ожидания данных от брокера (мс); null; 20000; Нет.
- TM_KAFKA_MAXPARTITIONFETCHBYTES — макс. данных из одной партиции за запрос (байт); null; 20000000; Нет.
- TM_KAFKA_LINGERMS — ожидание перед отправкой пакета (мс); null; 15000; Нет.
- TM_KAFKA_LISTENER_FORMAT — формат сериализации для слушателя (consumer); JSON; AVRO; Нет.
- TM_KAFKA_TOMSSENDER_FORMAT — формат сериализации для отправителя (producer); JSON; AVRO; Нет.
- TM_KAFKA_PRODUCER_COMPRESSIONTYPE — тип сжатия для producer; null; lz5; Нет.
- TM_KAFKA_SENDING_CLICKHOUSE_EVENT_MESSAGES_TOPIC — тема Kafka для событий в ClickHouse (флаг булевого значения или имя темы); null; false; Да. (все Kafka-пункты: Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
**Redis**
- TM_MERGETRANSACTION_REDISLOCKS_LOCKATTEMPTS — число попыток получения блокировки в Redis при слиянии; null; 3; Да.
- TM_REDIS_USERNAME — имя пользователя Redis; null; username; Нет.
- TM_MERGETRANSACTION_REDISLOCKS_LEASETIME — время аренды блокировки (мс); 17000; 25000; Нет.
- TM_MERGETRANSACTION_REDISLOCKS_LOCKATTEMPTSDELAYMS — задержка между попытками (мс); 0; 50; Нет.
- TM_REDISNODES_CREDENTIALS__USERNAME — имя пользователя для index-ой ноды Redis, index из таблицы postgres redis_node_availability.id; null; username; Да.
- TM_REDISNODES_CREDENTIALS__PASSWORD — пароль для index-ой ноды Redis, index из redis_node_availability.id; null; password; Да.
- TM_REDIS_AVAILABILITY_NODES — список доступных нод Redis (пользователю не передавать, вручную не задавать, задаётся автоматически админ-сервисом через таблицу configuration); null; пример: список объектов с полями id: 1, host: 10.228.64.18, port: 31479, database: 0, enabled: true; Да. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
**Scylla**
- TM_SCYLLA_CONTACTPOINTS — адреса узлов; null; d5ppbp-scc004lk.corp.***.***; Нет.
- TM_SCYLLA_KEYSPACE — keyspace; trmonbs_merge; my_keyspace; Нет.
- TM_SCYLLA_LOCALDC — локальный Data Center; dc1; dc1; Нет.
- TM_SCYLLA_PASSWORD — пароль; по умолчанию в документе строка-пароль (не воспроизводится); пример: scylla_pass; Нет.
- TM_SCYLLA_PORT — порт; null; 9042; Да.
- TM_SCYLLA_SSL_ENABLED — SSL для Scylla; true; false; Нет.
- TM_SCYLLA_USERNAME — имя пользователя; trmonbs_admin; scylla_user; Нет.
- CACHED_SCYLLA_PREPAREDSTATEMENT — True — PreparedStatement, False — not PreparedStatement; рекомендуется всегда True; null; true; Да.
- TM_MERGETRANSACTION_EXCEPTION_HANDLER_SCYLLA — количество потоков или размер очереди для обработчика исключений Scylla; по умолчанию: {enabled: true, timeout: 2000}; пример: 1000; Нет.
- TM_MERGETRANSACTION_EXCEPTION_HANDLER_SCYLLA_TIMEOUT — таймаут обработчика исключений Scylla (мс); 2000; 1000; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
**Потоки и восстановление транзакций**
- TM_MERGETRANSACTION_LOCK_THREADS_COUNT — потоки управления блокировками; 1000; 3960; Нет.
- TM_MERGETRANSACTION_SAVERESULT_THREADS_COUNT — потоки сохранения результатов; 2000; 3630; Нет.
- TM_MERGETRANSACTION_SELECTIVEMESPROC_THREADS_COUNT — потоки selective message processing; 600; 1430; Нет.
- TM_MERGETRANSACTION_UNDEFINEDMESPROC_THREADS_COUNT — потоки undefined message processing; 600; 2200; Нет.
- TM_MERGETRANSACTION_RESTORE_MAXRESTORECOUNT — макс. число попыток восстановления транзакции; 0; 10; Нет.
- TM_MERGETRANSACTION_RESTORE_MINRESTORESECONDS — мин. время между попытками восстановления (с); 60; 30; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
**Топики Бизнес-сервисов**
- TM_MERGETRANSACTION_BSTOPICS_ — для каждого БС список топиков в виде json (пользователю не передавать, вручную не задавать, задаётся админ-сервисом через таблицу configuration); null; Да. Ключи примера: enrichedEventsTopic: bs_8053_enriched_events; enrichedEventsFallbackTopic: bs_8053_enriched_events_fallback; clickhouseEvents: bs_8053_clickhouse_events; clickhouseEventsMessages: bs_8053_clickhouse_messages; mergedEventUuidsTopic: bs_8053_merged_event_uuids; enrichedEventsRestoreTopic: bs_8053_enriched_events_restore. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)

### Бизнес-правила и ограничения
- keystore и truststore добавляются в контейнер, если Kafka работает через SSL. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- TM_MERGETRANSACTION_BSTOPICS_ и TM_REDIS_AVAILABILITY_NODES задаются автоматически админ-сервисом через таблицу configuration; вручную не рекомендуется. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- CACHED_SCYLLA_PREPAREDSTATEMENT рекомендуется всегда ставить True. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)

### Открытые вопросы
- Для TM_MERGETRANSACTION_EXCEPTION_HANDLER_SCYLLA описание («количество потоков или размер очереди») и значение по умолчанию (JSON с enabled и timeout) выглядят несогласованными; приведено как в документе. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
