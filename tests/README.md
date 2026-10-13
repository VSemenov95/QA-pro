# Тесты QA pro

Браузерные тесты на pytest и Playwright. Они запускают собранное приложение в Chromium, подменяют модель, базу и скачивание файлов и проверяют, что видит и получает пользователь. Ничего не нужно скачивать вручную: входные файлы создаются на лету, библиотеки разбора документов при первом запуске подтягиваются через `npm pack` в `tests/.cache/`.

## Запуск

```bash
pip install pytest playwright python-docx openpyxl reportlab
playwright install chromium            # или QA_PRO_CHROMIUM=/путь/к/chrome
python3 -m pytest tests                # весь набор; перед ним сам собирает приложение (build.py)
python3 -m pytest tests/test_product_cases.py -k rename
QA_PRO_NO_BUILD=1 python3 -m pytest tests   # не пересобирать приложение
```

Нет сети или `npm` — тесты с метками `needs_libs` (разбор docx, xlsx, pdf) пропускаются с понятной причиной. Тесты, которым нужны внешние программы (упаковщик `.mcpb`, модель распознавания речи), тоже пропускаются, а не падают.

## Как это устроено

| Файл | Что делает |
|---|---|
| `conftest.py` | сборка приложения, браузер, фикстуры `app` и `make_app` |
| `support/app.py` | обёртка над страницей: `app.state(...)`, `app.call(...)`, `app.generate()`, `app.upload(...)`, `app.import_product(...)` |
| `support/model.py` | мок модели: тип запроса определяется по первой строке `prompts/*.md`, поэтому правка формулировок промптов тесты не ломает |
| `support/db.py` | база артефакта в памяти, переживает перезагрузку страницы |
| `support/caps.js` | возможности артефакта на странице: база, модель, пользователь, скачивание |
| `support/files.py` | ТЗ, файлы с кейсами (json, xlsx), docx, pdf — создаются в `tmp_path` |
| `support/seed.py` | готовые запуски и выгрузки продуктов |
| `support/libs.py` | локальные копии библиотек, которые приложение грузит с CDN |

Фикстура `app` — страница нового пользователя: приложение само создаёт «Мой продукт» с примером ТЗ. `make_app(kind='standalone', ...)` открывает автономную версию (`qa-pro.html`) — она нужна для подключений по ключу API и локального хранения. Подключения по ключу в артефакте не работают: на claude.ai страница изолирована от интернета.

## Как писать тест

```python
def test_generation_adds_tags(app):
    app.add_sample()
    app.generate()
    assert app.state("S.run.cases.every((c) => a.pickTitleText(c.testCase).startsWith('['))")
```

Свой ответ модели на один вид запросов:

```python
from tests.support.model import ModelError

app.model.on('promptGenerate', lambda call: {'cases': []})
app.model.on('promptReviewCases', ModelError('rate_limited'))
app.model.prompts_of('promptMap')          # тексты запросов этого вида
```

- Любая необработанная ошибка страницы (`pageerror`) валит тест, глушить её не нужно.
- Ждать — через `wait_for_function` и `wait_for_selector`, не через `sleep`.
- Внутренности приложения доступны через `window.__qa` (включается флагом `window.__qaTest`, который ставит фикстура). Новое для тестов добавляйте в список в конце `app3.js`.
- Тест, который выявил реальную ошибку приложения, нельзя ослаблять: пометьте `@pytest.mark.xfail(strict=True, reason='БАГ: ...')`.

## Интеграции

Тесты интеграций (Test IT, Qase, TestRail, загрузчик Сферы, мост, API провайдеров) исходят из того, что внешняя система присылает корректные данные. Такие тесты не проверяют некорректные ответы и не пишут об этом в комментариях и названиях. Проверки ошибок касаются только ответов самой системы: код ответа, сообщение, повтор.
