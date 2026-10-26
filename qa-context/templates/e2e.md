# Шаблон E2E

idPrefix: E2E-

## Правила

- Кейс описывает сквозной сценарий пользователя от начала до бизнес-результата через несколько экранов, сервисов или систем.
- Проверяй не только интерфейс, но и итоговое состояние данных.
- Пиши запрос в БД целиком и оборачивай в блок кода также, как запрос или ответ от API
- postconditions описывают, в каком состоянии остаётся система.
- Не дублируй мелкие проверки валидации — их покрывают UI- и API-кейсы.
- priority: P3_HIGH — основной пользовательский путь, P2_MEDIUM — валидации и сообщения, P1_LOW — косметика и редкие случаи, P4_CRITICAL — блокирует работу или безопасность. Других значений нет.

## Образец

```json
{
	"ti_regressive": false,
	"name": "Копия [E2E] Импорт нового значения справочника из эксель файла",
	"sectionId": 212573,
	"description": "",
	"type": "T1_TEST_CASE",
	"priority": "P3_HIGH",
	"automationStatus": "A2_NOT_AUTOMATED",
	"preConditions": [
		{
			"action": "<p>Подготовить файл в формате xlsx со значением справочника, например: </p>",
			"expectedResult": "",
			"actionAttachments": [],
			"resultAttachments": [
				"3d692588-ea1e-43ba-aea1-5c1c6011043f"
			]
		},
		{
			"action": "<p>Существует:</p>\n<p>Команда: TEM-1 Тестовая команда</p>",
			"expectedResult": "",
			"actionAttachments": [],
			"resultAttachments": []
		}
	],
	"steps": [
		{
			"action": "<p><strong>Отправить PATCH запрос:</strong><br><b data-rtc-uid=\"ed34a360-18e7-4d34-8a36-d8bef267cec3\" style=\"background-color: rgb(255, 255, 255);\">/api/v1/configuration/catalogs/import</b></p>\n<p><b data-rtc-uid=\"ed34a360-18e7-4d34-8a36-d8bef267cec3\" style=\"background-color: rgb(255, 255, 255);\"></b></p>\n<p>В body выбрать form-data <br>key = file<br>value = выбрать подготовленный файл со значением справочника в xlsx формате </p>",
			"expectedResult": "<p>API вернул 200 ОК</p>",
			"actionAttachments": [],
			"resultAttachments": []
		},
		{
			"action": "<p>Перейти в приложение Сфера.Команда по ссылке<br>https://sfera.ppcps-stable.test.sfera-t1.ru/teams</p>",
			"expectedResult": "<p>Открыто приложение</p>",
			"actionAttachments": [],
			"resultAttachments": []
		},
		{
			"action": "<p>Перейти Структура-&gt;Команда </p>",
			"expectedResult": "<p>Открыто вью Команды</p>",
			"actionAttachments": [],
			"resultAttachments": []
		},
		{
			"action": "<p>Нажать кнопку Создать-&gt;Позиция ФС</p>",
			"expectedResult": "<p>Открыта карточка позиции ФС в режиме создания</p>",
			"actionAttachments": [],
			"resultAttachments": []
		},
		{
			"action": "<p>Добавить команду из предусловия в поле команда</p>",
			"expectedResult": "<p>Поле Команда заполнено</p>",
			"actionAttachments": [],
			"resultAttachments": []
		},
		{
			"action": "<p>Нажать на поле Командная роль</p>",
			"expectedResult": "<p>Отображен выпадающий список с ролями для сущностей типа команда</p>",
			"actionAttachments": [],
			"resultAttachments": []
		},
		{
			"action": "<p>Проверить наличие импортированного значения \"Тестовое значение справочника\"</p>",
			"expectedResult": "<p>Значение \"Тестовое значение справочника\" присутствует</p>",
			"actionAttachments": [],
			"resultAttachments": []
		}
	],
	"postConditions": [
		{
			"action": "",
			"expectedResult": "<p>Отправить запрос в БД для удаления тестового значения:<br>delete from entities e <br>where type_id = (select id from entity_types et where code = 'teamRole') and name = 'Тестовое значение справочника'</p>",
			"actionAttachments": [],
			"resultAttachments": []
		}
	],
	"referencedTestIssues": [],
	"order": 0,
	"links": [
	],
	"attachments": [],
	"labels": [
		"1.28",
		"E2E"
	],
	"externalId": "890be816-2038-420d-b8be-3873ef8ed102",
	"statusId": "0ce9b9d2-5080-11f1-96c8-005056053b2e"
}
```
