# Установка микросервиса ppbp-admin-service и его переменные окружения

> Микросервис ppbp-admin-service устанавливается через Helm, а его поведение задаётся переменными окружения: JVM и логирование, Kafka, Postgres, ClickHouse, Scylla, аудит, OIDC, интеграция с Сфера: Конфигурации, ext-api.

### Описание
- Переменные ppbp-admin-service перечислены в таблице 4.2.3-1 (п. 1–151). На неё ссылается п. 3 установки Helm как на полный список. Здесь приведены п. 1–95 и 96–151 (стр. 37–47). Формат записи: описание; по умолчанию; пример; обязательность. Если не указано иное, переменная необязательна. Один «значение» означает, что по умолчанию и пример не разделены. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- В контейнер нужно добавить keystore и truststore с ключами для доступа к Kafka, если она работает по SSL. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)

### Поля и элементы
**JVM, логирование, порт**
- JAVA_OPTS — параметры JVM, включая SSL-хранилища; Xmx1G; пример -Djavax.net.ssl.trustStorePassword=$(TRUSTSTORE_PASSWORD) -Djavax.net.ssl.trustStore=/opt/keystores/truststore.p12.
- LOGGING_CONFIG — classpath:log4j2-kubernetes.xml; пример classpath:log4j2-local.xml. LOGGING_LEVEL_ROOT — info; пример debug. LOGGING_ENCODING — UTF-8. LOGGING_HOST (обяз.) — адрес fluent-bit при встроенном log4j2-kubernetes.xml; null; 127.0.0.1. LOGGING_LEVEL_RU_SFERA_TM_TRMONBSADMINSERVICE_SERVICE — info. SERVER_PORT — 8000; пример 8080.
- POD_NAME, POD_NAMESPACE — имя и namespace пода; Null. MS_PROPERTIES_INFOSYSTEMCODE — PPBP. TM_ACTUATOR_LOGGING_ENABLE — логирование запросов к актуатору; false.

**Kafka внутренняя**
- KAFKA_BOOTSTRAP_SERVERS (обяз.) — null; (10.***.64.21:30195,10.***.64.26:30195,10.***.64.27:30195). KEYSTORE_LOCATION (обяз.) — /opt/keystores/keystore.p12. KEYSTORE_PASSWORD (обяз.) — secret(certificate-pkcs12-password)[password] visibility. TRUSTSTORE_LOCATION (обяз.) — /opt/keystores/truststore.p12. TRUSTSTORE_PASSWORD (обяз.) — secret(certificate-pkcs12-password)[password]. Все по умолчанию null.
- SPRING_CLOUD_STREAM_KAFKA_BINDER_CONFIGURATION_SECURITY_PROTOCOL — SSL. SPRING_KAFKA_SECURITY_PROTOCOL — SSL. TM_KAFKA_SSL_ENABLED — false.
- Для kafkaAdmin (null; по умолчанию берутся значения ниже): SPRING_KAFKA_ADMIN_SECURITY_PROTOCOL (из SPRING_CLOUD_STREAM...), SPRING_KAFKA_ADMIN_SSL_KEY_STORE_LOCATION/PASSWORD (из KEYSTORE_*), SPRING_KAFKA_ADMIN_SSL_TRUST_STORE_LOCATION/PASSWORD (из TRUSTSTORE_*), SPRING_KAFKA_BOOTSTRAP_SERVERS (из KAFKA_BOOTSTRAP_SERVERS).

**Kafka внешняя, *** Cloud, топики**
- MQ_KAFKA_EXT_BOOSTRAP_SERVERS — localhost9090; пример kafka-kafka-bootstrap.shared:9092. MQ_KAFKA_EXT_KEYSTORE_LOCATION/PASSWORD, _TRUSTSTORE_PASSWORD — default; _TRUSTSTORE_LOCATION — default; /opt/keystores/truststore.p12. MQ_KAFKA_EXT_SECURITY_PROTOCOL — PLAINTEXT; SSL/PLAINTEXT. MQ_KAFKA_EXT_TOPIC_NAME — default; external_api_topik. TM_EXTERNAL_KAFKA_SSL_ENABLED — true.
- TM_KAFKA_ADMIN_TYPE — kafkaAdmin или kafkaCloud; по умолчанию kafkaAdmin; пример kafkaCloud. TM_KAFKA_CLOUD_ADMIN_IGNORECLOUDEXCEPTION — игнорировать обращения в *** Cloud при создании топиков; игнорировать ли исключения при обращении по kafkaAdmin; false; true. TM_KAFKA_CLOUD_ADMIN_URL — null; http://localhost:7777. TM_KAFKA_CLOUD_ADMIN_ITEM_ID — item_id в api *** Kafka cloud; пример b895ba44-f1e0-5b13-8d20-30b1cd92631e. TM_KAFKA_CLOUD_ADMIN_CN — client_cn для acl топиков; null. TM_ADMIN_KAFKA_DEFAULT_TOPICS_PROP_GLOBAL_DEFAULT — {"partitions": 1, "replicas": 1}; null. TM_ADMIN_KAFKA_DEFAULT_TOPICS_PROP_MAINTOPICS — если задан, переопределяет GLOBAL_DEFAULT для заданного topicType; null.
- ADM_SERVICE_USERNAME, ADM_SERVICE_PASSWORD (обяз.) — доступ к *** Cloud; null. TM_CLOUD_AUTH_URL (обяз.) — получение токена; null; http://localhost:7777. TM_CLOUD_AUTH_CLIENTID — пример sa_proj-h3nkz773kh-1dx. TM_CLOUD_AUTH_CLIENTSECRET — null.

**Postgres**
- DATASOURCE_SCHEMA (обяз.) — config_service. RDBMS_DATASOURCE_URL (обяз.) — jdbc:postgresql://d5ppbp-pgc001lk.****.dev.***:5432/trmonbs_config. RDBMS_DATASOURCE_USERNAME (обяз.) — ppbp_config_admin. RDBMS_DATASOURCE_PASSWORD (обяз.). Все по умолчанию null.

**ClickHouse**
- TTL в днях (TM_ADMIN_CLICKHOUSE_TTLINDAYS_DEFAULT_…): ATTRIBUTES 180, EVENTMESSAGES 10, EVENTS 180, METRICS 360, MONITORINGEVENTS 360, TIMEOUTATTRIBUTES 30.
- TM_CLICKHOUSE_CLUSTER_NAME — null; cl1. TM_CLICKHOUSE_NODEADDRESSES (обяз.) — адреса через запятую; host1:8113,host2:8123. TM_CLICKHOUSE_CREDENTIALS_ENABLED — false; true. TM_CLICKHOUSE_CREDENTIALS_USERNAME/PASSWORD (secret) — null. TM_CLICKHOUSE_SSLENABLED — true; false. TM_CLICKHOUSE_SOCKETTIMEOUT — 60000; 120000. TM_CLICKHOUSE_DATABASE_NAME — default. TM_KAFKA_TOCLICKSENDER_FORMAT — JSON.

**Scylla**
- TM_SCYLLA_CONTACTPOINTS — null; d5ppbp-scc004lk.corp.dev.***. TM_SCYLLA_KEYSPACE — trmonbs_merge; ppbp_merge. TM_SCYLLA_LOCALDC — dc1; ppmon. TM_SCYLLA_PASSWORD (secret). TM_SCYLLA_PORT (обяз.) — пример 9142. TM_SCYLLA_REQUESTTIMEOUT — 5000; 10000 мс. TM_SCYLLA_SSL_ENABLED (обяз.) — null; true. TM_SCYLLA_USERNAME (secret) — trmonbs_admin.

**Авторизация, конфигурация, интерфейс**
- TM_AUTHORIZATION_TYPE — ppamV2; ppamV1. TM_CHANNEL_URL (обяз.) — https://sfera.ppcps-stable.test.******.ru/. TM_CONFIG_SERVER — http://trmon-configuration-service:8000. CONFIG_AUTHENTICATION_JWTALTERNATIVEHEADERS — через запятую; custom_header_1,custom_header_2. CONFIG_AUTHENTICATION_CHANNELJWTFIELDVALUE — альтернативное поле channel для аудита; default. TM_SCRIPT_GENERATION_ATTRIBUTE_ADDITIONAL_ATTRIBUTES_LIMIT — лимит элементов ADDITIONAL_ATTRIBUTES в скрипте; 44. TM_FRONTEND_OLDDIR_ENABLED — true (старый ДиР)/false (новый) по стенду; false. TM_FRONTEND_NEWTECHCONSTRUCTOR_ENABLED — новый конструктор тех. атрибутов; false; установить true. TM_FILTERING_ATTRIBUTES_MAX_COUNT (обяз.) — макс. число доп. атрибутов фильтрации; null; 10. TM_METRIC_SERVICE_DEBUG_ENABLED — true; false (см. «Поля для настройки фильтров в вычисляемых атрибутах и метриках», вкладка «Вычисляемые атрибуты»).
- ATTR_NAME_REPLACEMENT_RULES — правила замены имён технических атрибутов (null; см. GET /technical-attribute/name-replacement-rules, HTTP 200, NameReplacementRules). Пример: { "top-level-only": [ { "from": "transactionId" , "to": "transaction_id" } ], "after-top-level": [ { "from": "businessId", "to": "business_id" } ] }.
- События мониторинга: TM_CALCULATION_PERIOD_IN_MINUTES — 10; TM_AUTO_MONITORING_EVENT_SEND_INTERVAL_VALUE — 7; ..._UNIT — DAY (минуты, часы, дни); TM_AUTO_MONITORING_EVENT_DEFAULT_ALERTED_OBJECT_URL_TEMPLATE — шаблон URL в событиях, по умолчанию пустой, null.

**ext-api**
- FEATURE_INTEGRATION_REST_ENABLED — глобальный флаг для POST /ext-api/v1/transactions-search, /transactions-attributes, /transactions-events; true. FEATURE_FRONTEND_METRICEXPORTTOKAFKA_ENABLED — чек-бокс «Отправка в ЗСМ»; false.
- CONFIG_INTEGRATION_REST_TRANSACTIONS_SEARCH_ATTRIBUTES_LIST — справочник атрибутов поиска для БС из ..._BS_LIST, маппинг для transactions-search; null; [ { "code": "clientExtId", "name": "Идентификатор организации в ДБО", "type": "STRING", "order": 1 } ]. «order» задаётся строго для селективности; атрибут типа «Date» — «0». ..._SEARCH_DEPTH_IN_DAY — 31; 18. ..._SEARCH_BS_LIST — описание обрывается.

**Сфера: Конфигурации, интеграции**
- TM_INTEGRATION_CATALOG_ENABLED (обяз.) — флаг задачи по расписанию (получение и обновление списка сервисов); null; true. Если true, обязательны TM_INTEGRATION_CATALOG_URL (URL Сфера: Конфигурации), _USERNAME, _PASSWORD (null).
- TM_INTEGRATION_CONFIGURATION_KAFKA_BOOTSTRAP_SERVERS (обяз.) — Kafka Сфера: Конфигурации; null. TM_INTEGRATION_SFERA_CONFIGURATION_KAFKA_SSL_ENABLED — true; false. SFERA_CONFIGURATION_TOPIC — 2078.ppcm-dataEvent-ke-output-1.0. SFERA_CONFIGURATION_PATH — /ppcm-fw/configuration-items. SFERA_CONFIGURATION_USERNAME — username. SFERA_CONFIGURATION_PASSWORD — null. SFERA_CONFIGURATION_URL, TM_INTEGRATION_ASSIGNMENTS_URL (назначения по ppam-assignments-v2) — sfera_host. PPBP_USERNAME/PPBP_PASSWORD — аутентификация по ppam-assignment и ppam-assignments-v2; username/password.
- SFERA_CORE_GATEWAY_URL — URL access-token; значения https://sfera.ppcps-stable.dev.sfera-t1.ru/api/auth/openid-connect/token и https://api-sfera.***.ru'. PPBP_CLIENT_ID/PPBP_CLIENT_SECRET — для токена из SFERA_CORE_GATEWAY_URL; stub.
- TM_OIDC_ENABLED — true. TM_OIDC_CLIENTID, TM_OIDC_CLIENTSECRET, TM_OIDC_AUTH_URL — null. CONFLUENT_SCHEMA_REGISTRY_URL — localhost:8080.

**Аудит**
- AUDIT_ENABLED (обяз.) — внешний аудит; true; false. AUDIT_LOCAL-MODE — false; true. AUDIT_KAFKA_SECURITY_PROTOCOL — PLAINTEXT; SSL. AUDIT_KAFKA_BOOTSTRAPSERVERS — localhost:9092; d5ppbp-kfc001lk.****.dev.***:****. AUDIT_KAFKA_SSL_KEYSTORE_LOCATION /_TRUSTSTORE_LOCATION — /opt/keystores/keystore.p12 и truststore.p12; _PASSWORD (secret) — null.
- SFERA_AUDIT_ENABLED (обяз.) — false; false. SFERA_AUDIT_METADATA — classpath.yml; sfera-audit-events-metadata.yml. SFERA_AUDIT_SYSTEM_CODE — PPBP. SFERA_AUDIT_SYSTEM_ID — 2099. SFERA_AUDIT_ADAPTER_URL (обяз.) — http://sfera-audit-adapter:8000/api. SFERA_AUDIT_TRANSPORT_MODE (обяз.) — KAFKA; пример REST. SFERA_AUDIT_OUTBOX_SCHEDULER_INTERVAL — */15 * * * * *.
- Producer (мс): MAX_BLOCK_MS 60000, DELIVERY_TIMEOUT 120000, LINGER 0, REQUEST_TIMEOUT 30000. SFERA_AUDIT_KAFKA_BOOTSTRAP_SERVERS (обяз.) — kafka-server:9092. _TOPIC (обяз.) — ppbp.audit-topic; ppbp.audit_1. _SECURITY_PROTOCOL (обяз.) — SSL. _KEYSTORE_LOCATION (обяз.) — /opt/keystore.p12. _KEYSTORE_PASSWORD, _TRUSTSTORE_PASSWORD (обяз.) — «-»; password. _KEYSTORE_TYPE, _TRUSTSTORE_TYPE (обяз.) — PKCS12 (или JKS). _TRUSTSTORE_LOCATION (обяз.) — /opt/truststore.p12.
(Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)

### Бизнес-правила и ограничения
- Один из аудитов (Сфера аудит или внешний аудит) должен быть выключен (AUDIT_ENABLED и SFERA_AUDIT_ENABLED).
- TM_OIDC_ENABLED: если true, обращение идёт по tm.oidc.auth.url, иначе по tm.channel.url.
- ATTR_NAME_REPLACEMENT_RULES: top-level-only применяются только к атрибутам верхнего уровня JSON; after-top-level — к вложенным.
- SFERA_AUDIT_TRANSPORT_MODE: [KAFKA, REST]; SFERA_AUDIT_ADAPTER_URL — только для REST. SFERA_AUDIT_KAFKA_SECURITY_PROTOCOL: PLAINTEXT, SSL, SASL_PLAINTEXT, SASL_SSL.
- CONFLUENT_SCHEMA_REGISTRY_URL: URL через запятую; для тестов — mocked-реестр «mock://my-scope-name».
(Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)

### Открытые вопросы
- Выдержка из таблицы 4.2.3-1 обрывается на п. 80; п. 81–83 и 85–87 не приведены.
- В документе переменная FEATURE_INTEGRATION_REST_ENABLED повторяется (п. 16 и 84), с разным примером (true/false и true).
