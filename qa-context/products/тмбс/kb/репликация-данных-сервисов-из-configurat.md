# Репликация данных Сервисов из configuration_integration_services в таблицу service (и связи с ИС и БС)

> Автоматическая репликация данных Сервисов из интеграционной таблицы configuration_integration_services в таблицу service с последующим заполнением связей Сервисов с Информационными системами (s_system_inf_system) и Бизнес-сервисами (s_system_bs_system).

### Описание
- Документ описывает техническое решение для фичи «Передача метрик из ТМБС в ЗСМ в привязке к сервисам с агрегирующим расчетом на стороне ТМБС». (ТМ. [СА] Список сервисов-10)
- Предусловия: реализована интеграция Сфера.ТМБС со Сфера.Конфигурации; все объекты сущности «Сервисы» записываются в интеграционную таблицу configuration_integration_services; эти объекты участвуют только во внутренней логике бэка для связывания объектов сущностей «Бизнес-сервис» и «Информационные системы». (ТМ. [СА] Список сервисов-10)
- Необходимые изменения: реализовать автоматическую репликацию данных из configuration_integration_services в таблицу service. (ТМ. [СА] Список сервисов-10)

### Поля и элементы
- Таблица маппинга (параметр / тип / пояснение / параметр в config_service.service / параметр в конфигурациях): (ТМ. [СА] Список сервисов-10)
  - id — serial4 — Внутренний айди Сервиса — id — «-»
  - external_id (PK) — string — Внешний айди Сервиса — external_id — number
  - name — string — Наименование — name — name
  - code — string — Код — code — itServCode
  - type — string — Тип — type — itServType
  - status — string — Статус — status — status
  - criticality — string — Критичность — criticality — itServCriticality
  - stream — string — Стрим развития — stream — stream
  - description — string — Описание — description — description
  - created_date — date — Дата создания — created_date — createdDate
  - modify_date — date — Дата обновления — modify_date — updatedDate
  - version (PK) — int4 — Версия — version_string — itsVersion
  - details — JSON — Информация о сервисе — «-»

### Бизнес-правила и ограничения
- Логика репликации в config_service.service: в таблице config_service.configuration_integration_services находим колонку «details»; в json-объекте находим атрибуты «type» и «status». (ТМ. [СА] Список сервисов-10)
- Если «type»: «bizservice_ITService_configItem» (ИТ-Сервис) + «status»: «exploitation» И/ИЛИ «type»: «bizservice_Service_configItem» (Сервис) + «status»: «exploitation» — переносим данные (формируем новые записи) из config_service.configuration_integration_services в config_service.service согласно таблице маппинга. (ТМ. [СА] Список сервисов-10)
- Иначе, если «type»: null или вложено другое значение — репликация для таких объектов не нужна. (ТМ. [СА] Список сервисов-10)
- Если для записи отсутствуют значения в полях «external_id», «name» — такие объекты в config_service.service мигрировать не нужно. (ТМ. [СА] Список сервисов-10)
- Поле «code»: если значение != null — в service попадает записанное значение; если == null — в «code» кладём значение поля «external_id» записи. (ТМ. [СА] Список сервисов-10)
- Поле «type»: если значение != null — в service попадает записанное значение; если == null — записываем дефолтное значение «SERVICE». (ТМ. [СА] Список сервисов-10)
- Связь Сервисов и Информационных систем (config_service.s_system_inf_system): в configuration_integration_services находим колонку «related_is». Если в ней есть запись с идентификатором(-ами) «external_id» И/ИЛИ в колонке «details» (json) есть наполненный атрибут «related_is» с идентификатором(-ами) «external_id» — с найденными «external_id» идём в config_service.information_system и ищем соответствующие идентификаторы в колонке «external_id». (ТМ. [СА] Список сервисов-10)
- Если есть совпадения — устанавливаем связь в config_service.s_system_inf_system по внутренним идентификаторам: «service_id» — config_service.service.id, «inf_system_id» — config_service.information_system.id. Если совпадений нет — связь не проставляется. (ТМ. [СА] Список сервисов-10)
- Если в колонке «related_is» нет записей (null) И в «details» атрибут «related_is» пустой (null) ИЛИ полностью отсутствует — связь между Сервисом и Информационной системой не создаётся. (ТМ. [СА] Список сервисов-10)
- Связь Сервисов и Бизнес-сервисов (config_service.s_system_bs_system): в config_service.configuration_integration_link находим колонку «c1» (Внешние ключи бизнес-сервиса). (ТМ. [СА] Список сервисов-10)
- Ищем записи в config_service.business_services, где «external_id» совпадает с external_id из колонки «CI1» таблицы config_service.configuration_integration_link. На выходе — список записей внутренних и внешних идентификаторов Бизнес-сервиса. (ТМ. [СА] Список сервисов-10)
- Для каждого найденного «external_id» в configuration_integration_link извлекаем «external_id» из колонки «CI2» (Внешние ключи Сервисов). На выходе — связка внешних ключей Бизнес-сервисов и Сервисов. (ТМ. [СА] Список сервисов-10)
- В config_service.service ищем все внешние ключи (колонка «external_id»), совпадающие с внешними ключами из колонки «CI2» таблицы configuration_integration_link. На выходе — список внутренних и внешних ключей Сервисов, совпадающих по связи. (ТМ. [СА] Список сервисов-10)
- Для каждого совпадения добавляем запись в config_service.s_system_bs_system: service_id — внутренний ID найденного Сервиса из config_service.service; bs_id — внутренний ID найденного бизнес-сервиса из config_service.business_service. (ТМ. [СА] Список сервисов-10)

### API и интеграции
- Интеграция Сфера.ТМБС со Сфера.Конфигурации (источник данных — интеграционные таблицы configuration_integration_services и configuration_integration_link). (ТМ. [СА] Список сервисов-10)

### Сценарии
- Данные Сервисов автоматически реплицируются из configuration_integration_services в service; затем по связям related_is и configuration_integration_link заполняются s_system_inf_system и s_system_bs_system. (ТМ. [СА] Список сервисов-10)

### Открытые вопросы
- Раздел «3. E2E процессы» содержит пустую строку (1 — «-», «-», «-»). (ТМ. [СА] Список сервисов-10)
- Разделы «8. Иные изменения», «9. План миграции/релиза», «10. Потенциальные проблемы и риски» содержат только шаблонные пояснения, без содержания. (ТМ. [СА] Список сервисов-10)
