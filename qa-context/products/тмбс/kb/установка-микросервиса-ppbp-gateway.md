# Установка микросервиса ppbp-gateway

> Установка микросервиса ppbp-gateway в составе продукта ТМБС: подготовка хранилища доверенных сертификатов для проверки jwt-токенов, настройка ingress и переменные окружения.

### Описание
- Необходимо установить микросервисы, перечисленные в подразделах 4.2 (ppbp-gateway, ppbp-configuration-service, ppbp-admin-service). (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- ppbp-gateway: подготовить хранилище доверенных сертификатов для проверки jwt-токенов в канале и разместить его в подсистеме вашего сервиса. Настроить доступ к этой подсистеме извне. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)

### Поля и элементы
- Пример конфигурации ingress: (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
  - annotations: cert-manager.io/cluster-issuer: ******.ru; cert-manager.io/common-name: ppbp-gateway.ppmon.dev.******.ru; nginx.ingress.kubernetes.io/proxy-body-size: 1024m; nginx.ingress.kubernetes.io/ssl-redirect: "true".
  - enabled: true; className: nginx.
  - hosts: host ppbp-gateway.ppmon.dev.******.ru; paths: path `/`, pathType ImplementationSpecific, port 8080.
  - tls: hosts ppbp-gateway.ppmon.dev.******.ru; secretName ppbp-gateway.ppmon.dev.******.ru.
- Таблица 4.2.1-1 — переменные окружения ppbp-gateway (по умолчанию / пример / обязательность): (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
  1. JAVA_OPTS — параметры запуска JVM, включая настройки SSL-хранилищ; Xmx1G; Djavax.net.ssl.trustStorePassword=$(TRUSTSTORE_PASSWORD) -Djavax.net.ssl.trustStore=/opt/keystores/truststore.p13; обязательность: Нет.
  2. SFERA_CORE_GATEWAY_URL — gateway канального приложения; по умолчанию null; пример https://sfera.ppcps-stable.***.******.ru; обязательность: Да.
  3. SERVER_PORT — HTTP-порт приложения; 8000; 8000; Нет.
  4. APP_NAME — имя приложения; sfera-trmonbs-gateway; -; Нет.
  5. ASSIGNMENT_SERVICE_URL — URL assignment-service; http://ppam-subject-assigment-service:8000; Нет.
  6. TRMONBS_ADMIN_URL — URL admin-service; http://trmonbs-admin-service:8000; Нет.
  7. TRMONBS_APP_URL — URL фронт приложения; https://app-ppbp-dev.oslb-dev01.corp.dev.***; Нет.
  8. APP_VERSION — версия приложения; null; -; Нет.
