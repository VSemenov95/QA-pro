# Установка микросервиса ppbp-fe

> Раздел описывает установку микросервиса ppbp-fe (фронтенд ТМБС) через Helm, а именно конфигурацию ingress для входа в сервис.

### Описание
- Вход разделяется согласно приведённой конфигурации ingress. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)

### Поля и элементы
Конфигурация ingress (значения, замаскированные в документе, обозначены ******):
- enabled: true. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- className: nginx. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- ingress.annotations: cert-manager.io/cluster-issuer: ******.ru; cert-manager.io/common-name: trmon-fe.ppmon.test.******.ru; nginx.ingress.kubernetes.io/proxy-body-size: 1024m; nginx.ingress.kubernetes.io/ssl-redirect: "true". (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- hosts: host trmon-fe.ppmon.test.******.ru; paths: path /, pathType ImplementationSpecific, port 8000. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
- tls: hosts trmon-fe.ppmon.test.******.ru; secretName trmon-fe.ppmon.test.******.ru. (Сфера.ТМБС_Руководство_администратора_PPBP-26.3.0-4)
