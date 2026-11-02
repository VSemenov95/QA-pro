# Установка микросервиса ppbp-kafka-generator

> Раздел описывает установку микросервиса ppbp-kafka-generator (генератор тестовых сообщений в Kafka): SSL-хранилища и переменные окружения контейнера.

### Описание
- В контейнер необходимо добавить keystore и truststore с ключами для доступа к Kafka, если она работает через SSL. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- Также следует передать переменные окружения (таблица 4.2.14-1 «Данные переменных окружения ppbp-kafka-generator»). Формат таблицы: № ИМЯ — описание; по умолчанию; пример; обязательность. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)

### Поля и элементы
Переменные окружения (имя — описание; по умолчанию; пример; обязательность):
- 1 JAVA_OPTS — Параметры запуска JVM, включая настройки SSL-хранилищ; Xmx=1024m; Djavax.net.ssl.trustStorePassword=$(TRUSTSTORE_PASSWORD) -Djavax.net.ssl.trustStore=/opt/keystores/truststore.p12; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- 2 KAFKA_BOOTSTRAP_SERVERS — описание в документе: «Параметры запуска JVM, включая настройки SSL-хранилищ»; по умолчанию Xmx1024m; пример Djavax.net.ssl.trustStorePassword=$(TRUSTSTORE_PASSWORD) -Djavax.net.ssl.trustStore=/opt/keystores/truststore.p12; Да. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- 3 KEYSTORE_LOCATION — Путь к файлу хранилища ключей keystore; null; /opt/keystores/keystore.p12; Да. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- 4 KEYSTORE_PASSWORD — Пароль к файлу хранилища ключей keystore; null; secret(certificate-pkcs12-password)[password] visibility; Да. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- 5 TRUSTSTORE_LOCATION — Путь к файлу хранилища ключей truststore; null; /opt/keystores/truststore.p12; Да. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- 6 TRUSTSTORE_PASSWORD — Пароль к файлу хранилища ключей truststore; null; secret(certificate-pkcs12-password)[password]; Да. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- 7 TM_KAFKATESTER_ENABLE — Признак включения тестовых сообщений в Kafka; false; «-»; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- 8 TM_KAFKATESTER_GENERATORS — Имя или идентификатор генератора тестовых сообщений в Kafka; null; test_message_generator; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- 9 TM_KAFKATESTER_RATE — Частота генерации тестовых сообщений (например, в мс или кол-во в сек); 0; 1000; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- 10 TM_KAFKATESTER_SOURCES_BANK_EVENT — Топик источника событий банка для тестирования; null; bank.events; Да. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- 11 TM_KAFKATESTER_SOURCES_BLOCK_REQUEST_EVENT — Топик источника запросов на блокировку для тестирования; null; block.requests; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- 12 TM_KAFKATESTER_SOURCES_BLOCK_RESPONSE_EVENT — Топик источника ответов на блокировку для тестирования; null; block.responses; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- 13 TM_KAFKATESTER_SOURCES_COMPLETE_FL_EVENT — Топик источника событий завершения ФЛ для тестирования; null; fl.complete; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- 14 TM_KAFKATESTER_SOURCES_DOCUMENT_PREPARATION — Топик источника событий подготовки документов для тестирования; null; docs.preparation; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- 15 TM_KAFKATESTER_SOURCES_DOCUMENT_PROCESS — Топик источника событий обработки документов для тестирования; null; docs.processing; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- 16 TM_KAFKATESTER_SOURCES_DOSTUPNOST_REQUEST_EVENT — Топик источника запросов доступности для тестирования; null; dostupnost.requests; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- 17 TM_KAFKATESTER_SOURCES_DOSTUPNOST_RESPONSE_EVENT — Топик источника ответов доступности для тестирования; null; dostupnost.responses; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- 18 TM_KAFKATESTER_SOURCES_START_FL_EVENT — Топик источника событий старта ФЛ для тестирования; null; fl.start; Нет. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)

### Бизнес-правила и ограничения
- Все пароли должны храниться в разделе secrets. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- Обязательные (Да): KAFKA_BOOTSTRAP_SERVERS, KEYSTORE_LOCATION, KEYSTORE_PASSWORD, TRUSTSTORE_LOCATION, TRUSTSTORE_PASSWORD, TM_KAFKATESTER_SOURCES_BANK_EVENT. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)

### Открытые вопросы
- Для KAFKA_BOOTSTRAP_SERVERS в таблице 4.2.14-1 описание, значение по умолчанию и пример совпадают со строкой JAVA_OPTS (параметры JVM, Xmx1024m, настройки trustStore); фактическое описание, значение по умолчанию и пример для списка Kafka-серверов не указаны, возможна ошибка в документе. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- Значение по умолчанию JAVA_OPTS записано как «Xmx=1024m», а у KAFKA_BOOTSTRAP_SERVERS как «Xmx1024m»; написание различается. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
