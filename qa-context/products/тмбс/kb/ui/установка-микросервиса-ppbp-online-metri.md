# Установка микросервиса ppbp-online-metrics-service

> Установка микросервиса ppbp-online-metrics-service: добавление keystore/truststore для Kafka по SSL и настройка переменных окружения (JVM, Kafka, Scylla, встроенная БД, расчёт метрик).

### Описание
- Микросервис ppbp-online-metrics-service (раздел 4.2.9). В контейнер необходимо добавить keystore и truststore с ключами для доступа к Kafka, если она работает через SSL. Необходимо учесть переменные среды из таблицы 4.2.9-1 «Данные переменных окружения ppbp-online-metrics-service». (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)

### Поля и элементы
Формат: переменная — описание; по умолчанию; пример; обязательность.
**Общие, JVM, логирование**
- JAVA_OPTS — параметры запуска JVM, включая настройки SSL-хранилищ; Xmx1G; -Djavax.net.ssl.trustStorePassword=$(TRUSTSTORE_PASSWORD) -Djavax.net.ssl.trustStore=/opt/keystores/truststore.p12; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- LOGGING_CONFIG — путь к файлу конфигурации логирования; classpath:log4j2-kubernetes.xml; classpath:log4j2-local.xml; Нет. LOGGING_LEVEL_ROOT — уровень логирования; info; debug; Нет. SERVER_PORT — HTTP-порт; 8000; 8080; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- LOGGING_HOST — адрес fluent-bit (агент сбора и маршрутизации логов) при использовании встроенного log4j2-kubernetes.xml; null; 127.0.0.1; Да. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- LOGGING_LEVEL_RU_T1_SFERA_TM_METRICS_ONLINE_CORE_SERVICE — уровень логирования пакета ru.t1.sfera.tm.metrics.online.core.service; INFO; INFO; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
**Kafka и SSL**
- KAFKA_BOOTSTRAP_SERVERS — адрес Kafka; localhost:9092; (10.***.64.21:30195,10.***.64.26:30195,10.***.64.27:30195); Да.
- KEYSTORE_LOCATION — путь к keystore; null; /opt/keystores/keystore.p12; Да. KEYSTORE_PASSWORD — пароль keystore; null; secret(certificate-pkcs12-password)[password] visibility; Да.
- TRUSTSTORE_LOCATION — путь к truststore; null; /opt/keystores/truststore.p12; Да. TRUSTSTORE_PASSWORD — пароль truststore; null; secret(certificate-pkcs12-password)[password]; Да.
- SPRING_CLOUD_STREAM_KAFKA_BINDER_CONFIGURATION_SECURITY_PROTOCOL — протокол безопасности Kafka биндера; SSL; PLAINTEXT; Нет. TM_KAFKA_SSL_ENABLED — флаг SSL для Kafka; true; false; Нет.
- TM_KAFKA_GROUPID — ид группы consumer входящих сообщений; trmonbs-online-metrics-service; trmonbs-online-metrics-service; Нет.
- TM_KAFKA_MAXPOLLRECORDS — макс. записей за poll(); null; 5000; Нет. TM_KAFKA_BATCHSIZE — размер пакета (байт) для отправки в Kafka; null; 256000; Нет. TM_KAFKA_FETCHMAXWAITMS — макс. ожидание данных от брокера (мс); null; 20000; Нет. TM_KAFKA_MAXPARTITIONFETCHBYTES — макс. данных из одной партиции за запрос (байт); null; 20000000; Нет. TM_KAFKA_LINGERMS — ожидание перед отправкой пакета (мс); null; 15000; Нет.
- TM_KAFKA_LISTENER_FORMAT — формат сериализации для слушателя (consumer); JSON; AVRO; Нет. TM_KAFKA_PRODUCER_COMPRESSIONTYPE — тип сжатия producer; null; lz5; Нет.
- CONFLUENT_SCHEMA_REGISTRY_URL — адрес реестра avro схем, используется если TM_KAFKA_TOCLICKSENDER_FORMAT=AVRO; http://localhost:8080; пример: -; Нет.
- TM_KAFKA_TOCLICKSENDER_FORMAT — формат передачи данных kafka → clickhouse [JSON, AVRO]; JSON; AVRO; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
**Scylla**
- TM_SCYLLA_CONTACTPOINTS — адреса узлов; d5ppbp-scc004lk.corp.***.***; 10.0.0.1,10.0.0.2; Нет.
- TM_SCYLLA_LOCALDC — локальный ЦОД; dc0; dc1; Нет.
- TM_SCYLLA_PASSWORD — пароль; значение по умолчанию указано в документе строкой-паролем (здесь не воспроизводится); пример: scylla_pass; Нет.
- TM_SCYLLA_PORT — порт; null; 9042; Да. TM_SCYLLA_SSL_ENABLED — флаг SSL; null; false; Да. TM_SCYLLA_USERNAME — имя пользователя; trmonbs_admin; scylla_user; Нет.
- CACHED_SCYLLA_PREPAREDSTATEMENT — True — PreparedStatement, False — not PreparedStatement; null; true; Да.
- TM_SCYLLA_KEYSPACE — keyspace scylla с данными по событиям; trmonbs_merge; пример: -; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
**Встроенная БД и кэши**
- CACHE_SQLPARAMSCACHE_MAXENTRIESLOCALHEAP — макс. число кэшируемых событий; 500; 5000000; Нет.
- SPRING_DATASOURCE_HIKARI_MAXIMUMPOOLSIZE — макс. число соединений к встроенной БД; 250; 40; Нет.
- SPRING_DATASOURCE_URL — адрес внутренней БД; по умолчанию jdbc:h2:mem:onlinedb;LOCK_MODE=0;QUERY_CACHE_SIZE=${H2_QUERY_CACHE_SIZE:10000}; пример не указан; Нет.
- H2_QUERY_CACHE_SIZE — размер кэша prepared-statement для внутренней БД; 10000; -; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
**Расчёт и прочее**
- TM_MONITOR_METRICS_ENABLED — метрики технического мониторинга (число входящих сообщений, задержки чтения, ...); true; true; Нет.
- TM_ONLINECALC_CONCURRENCY — число потоков параллельной обработки входящих сообщений; 250; 24; Нет.
- STRING_ATTRIBUTE_MAX_VALUE_LENGTH — макс. длина строки результата строкового вычисляемого атрибута; 256; 256; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
**Переменные, задаваемые админ-сервисом** (пользователю не передавать, вручную задавать не рекомендуется; задаются автоматически через таблицу configuration; по умолчанию null; обязательность Да)
- TM_ONLINE-CALC_BSTOPICS_ — для каждого БС список топиков в json. Ключи: mergedEventUuidsTopic: bs_8053_merged_event_uuids; mergedEventUuidsFallbackTopic: bs_8053_merged_event_uuids_fallback; clickhouseAttributesTopic: bs_8053_clickhouse_attributes; clickhouseTimeoutAttributesTopic: bs_8053_clickhouse_timeout_attributes.
- TM_ONLINE-CALC_METRICS_ — для каждого БС правила расчёта атрибутов в json. Пример: additionalFields: [event_time, action, check_status]; metrics — одна: type: VALUE, metricId: 1315, metricName: Количество событий транзакций, transactionType: TRANSACTIONAL, valueTypeProp: {valueQuery: select count(1) from data; thresholds: [{type: CRITICAL, min: null, max: 9}, {type: NORMAL, min: 9, max: null}]}, valueTimeoutTypeProp, durationTimeoutTypeProp, stringValueTypeProp: null.
- TM_ONLINE-CALC_TRANSACTION-DATA-TABLES--DESC_ — для каждого БС правила описания внутренних таблиц в json. fieldTransformations (fieldName / type / outputType / params): service, type, status, global_transaction_uuid, event_id_payment_id, event_id_qrcode_id, event_id_document_id, event_stage, action, check_status — type COPY, outputType VARCHAR, params null; event_time — type DATE_TIME, outputType TIMESTAMP_WITH_TIMEZONE, params null. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)

### Бизнес-правила и ограничения
- keystore и truststore добавляются в контейнер, если Kafka работает через SSL.
- SPRING_DATASOURCE_HIKARI_MAXIMUMPOOLSIZE должно быть больше значения TM_ONLINECALC_CONCURRENCY.
- Для TM_KAFKA_TOCLICKSENDER_FORMAT=AVRO необходимо настроить реестр схем (CONFLUENT_SCHEMA_REGISTRY_URL).
- Для CACHED_SCYLLA_PREPAREDSTATEMENT рекомендуется всегда ставить True.
- TM_SCYLLA_KEYSPACE соответствует значению в admin-service. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
