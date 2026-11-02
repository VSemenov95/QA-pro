# Установка микросервиса ppbp-ecm-integration-service

> Установка микросервиса ppbp-ecm-integration-service, который читает входящие сообщения из Kafka и отправляет их в ECM, с настройкой через переменные окружения (таблица 4.2.13-1).

### Описание
- В контейнер необходимо добавить keystore и truststore с ключами для доступа к Kafka, если она работает через SSL. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- Переменные среды описаны в таблице 4.2.13-1 «Данные переменных окружения ppbp-ecm-integration-service». Формат: № ИМЯ — описание; по умолчанию; пример; обязательность. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)

### Поля и элементы
Формат: ИМЯ — описание; по умолчанию; пример; обязательность.
- 1 JAVA_OPTS — параметры запуска JVM, включая настройки SSL-хранилищ; Xmx1G; Djavax.net.ssl.trustStorePassword=$(TRUSTSTORE_PASSWORD) -Djavax.net.ssl.trustStore=/opt/keystores/truststore.p12; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- 2 KAFKA_BOOTSTRAP_SERVERS — адрес сервера Kafka; localhost:9092; (10.***.64.21:30195,10.***.64.26:30195,10.***.64.27:30195); Да. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- 3 KEYSTORE_LOCATION — путь к файлу хранилища ключей keystore; null; /opt/keystores/keystore.p12; Да. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- 4 KEYSTORE_PASSWORD — пароль к файлу keystore; null; secret(certificate-pkcs12-password)[password] visibility; Да. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- 5 TRUSTSTORE_LOCATION — путь к файлу truststore; null; /opt/keystores/truststore.p12; Да. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- 6 TRUSTSTORE_PASSWORD — пароль к файлу truststore; null; secret(certificate-pkcs12-password)[password]; Да. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- 7 LOGGING_CONFIG — путь к файлу конфигурации логирования; classpath:log4j2-kubernetes.xml; classpath:log4j2-local.xml; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- 8 LOGGING_LEVEL_ROOT — уровень логирования; info; debug; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- 9 LOGGING_HOST — адрес fluent-bit (агент для сбора и маршрутизации логов), на который отправляются логи, в случае использования встроенного log4j2-kubernetes.xml; null; 127.0.0.1; Да. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- 10 SERVER_PORT — HTTP-порт приложения; 8000; 8080; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- 11 SPRING_CLOUD_STREAM_KAFKA_BINDER_CONFIGURATION_SECURITY_PROTOCOL — протокол безопасности для Kafka биндера; SSL; PLAINTEXT; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- 12 SPRING_KAFKA_SECURITY_PROTOCOL — протокол безопасности для стандартного клиента Spring Kafka; SSL; PLAINTEXT; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- 13 TM_KAFKA_FALLBACKTOPIC — топик для сообщений, которые не удалось отправить в основной топик; null; fallback_topic; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- 14 TM_KAFKA_GROUPID — ID группы потребителей Kafka; trmonbs-ecm-integration-service; my_consumer_group; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- 15 TM_KAFKA_INPUTTOPICS — топик для входящих сообщений, которые необходимо отправлять в ECM; null; input_topic; Да. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- 16 TM_KAFKA_SSL_ENABLED — флаг включения SSL для Kafka; true; false; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- 17 TM_MONITORINGEVENT_APPLICATIONNAME — имя приложения для мониторинговых событий; null; my-app-service; Да. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- 18 TM_MONITORINGEVENT_ECM_SERVICES_INTEGRATION_HOST — адрес ECM-сервиса, куда отправляются события мониторинга; null; http://ecm-service:8080; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- 19 CONFIG_PPPM_DEVIATION_MESSAGE_MAX_SIZE_IN_KB — максимальный размер сообщения (в КБ) для отклонений при интеграции с ЗСМ; 900; 1024; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- 20 MQ_KAFKA_PPPM_BOOTSTRAP_SERVERS — адрес внешней Kafka для отправки сообщений во внешние продукты; default; external.kafka.host:9092; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- 21 MQ_KAFKA_PPPM_KEYSTORE_LOCATION — расположение keystore для внешней Kafka; null; /etc/ssl/certs/keystore.p12; Да. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- 22 MQ_KAFKA_PPPM_KEYSTORE_PASSWORD — пароль от keystore для внешней Kafka; null; my_secure_password; Да. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- 23 MQ_KAFKA_PPPM_TRUSTSTORE_LOCATION — расположение truststore для внешней Kafka; null; /etc/ssl/certs/truststore.p12; Да. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- 24 MQ_KAFKA_PPPM_TRUSTSTORE_PASSWORD — пароль от truststore для внешней Kafka; null; truststore_pass; Да. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- 25 MQ_KAFKA_PPPM_SECURITY_PROTOCOL — протокол безопасности для внешней Kafka; SSL; PLAINTEXT; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- 26 MQ_KAFKA_PPPM_TOPIC_NAME — имя топика внешней Kafka; default; external_topic; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- 27 FEATURE_PPPM_EVENTS_INTEGRATION_METHOD — способ интеграции (KAFKA или REST); KAFKA; REST; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- 28 CONFIG_PPPM_DEVIATION_MESSAGE_INSTANCEID — идентификатор экземпляра для сообщений об отклонениях; null; INSTANCE-01; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- 29 TM_KAFKA_BATCHSIZE — размер пакета (в байтах) для отправки сообщений в Kafka; null; 256000; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- 30 TM_KAFKA_LINGERMS — время ожидания перед отправкой пакета, чтобы накопить больше сообщений (в миллисекундах); null; 15000; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- 31 TM_KAFKA_PRODUCER_COMPRESSIONTYPE — тип сжатия сообщений, отправляемых в Kafka (доступен стандартный список); по умолчанию «Нет»; пример «-»; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- 32 TM_MONITOR_METRICS_ENABLED — включает/выключает метрики технического мониторинга (количество отправленных сообщений, …) микросервиса; true; false; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- 33 TM_KAFKA_UNPROCESSED_KOEFF — коэффициент обработки количества сообщений retry топика по отношению к количеству входящих сообщений. Количество_из_retry = Кол_вх * коэфф; 0.2; 0.2; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- 34 TM_KAFKA_UNPROCESSED_TOPIC_NAME — топик для сообщений, которые не удалось отправить в ECM; trmonbs_metrics_retry; trmonbs_metrics_retry; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)

### Бизнес-правила и ограничения
- Способ интеграции событий — KAFKA или REST (FEATURE_PPPM_EVENTS_INTEGRATION_METHOD, по умолчанию KAFKA). (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- Обязательные (Да): KAFKA_BOOTSTRAP_SERVERS, KEYSTORE_*/TRUSTSTORE_* (LOCATION и PASSWORD), LOGGING_HOST, TM_KAFKA_INPUTTOPICS, TM_MONITORINGEVENT_APPLICATIONNAME, MQ_KAFKA_PPPM_KEYSTORE_LOCATION, MQ_KAFKA_PPPM_KEYSTORE_PASSWORD, MQ_KAFKA_PPPM_TRUSTSTORE_LOCATION, MQ_KAFKA_PPPM_TRUSTSTORE_PASSWORD. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)

### API и интеграции
- Входящие сообщения для отправки в ECM читаются из топика TM_KAFKA_INPUTTOPICS; события мониторинга отправляются на адрес ECM-сервиса из TM_MONITORINGEVENT_ECM_SERVICES_INTEGRATION_HOST. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- Сообщения, которые не удалось отправить в основной топик, — в TM_KAFKA_FALLBACKTOPIC; не отправленные в ECM — в TM_KAFKA_UNPROCESSED_TOPIC_NAME. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
