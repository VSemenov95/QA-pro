"""Шаг вызова API: «Вызвать МЕТОД ЭНДПОИНТ с телом:» и блок кода с телом."""


def test_rule_is_in_generation_prompt(app):
    app.add_sample()
    app.generate()
    p = app.model.prompts_of('promptGenerate')[0]
    assert 'Вызвать МЕТОД {baseURL}/ЭНДПОИНТ с телом:' in p and 'блок кода с телом запроса' in p


def test_api_example_uses_the_call_form(app):
    action = app.state("a.tplInfo('api').structure.steps[0].action")
    assert action.startswith('Вызвать POST {baseURL}/api/v1/password-reset с телом:')
    assert '```json' in action


def test_service_state_rule_is_in_generation_prompt(app):
    app.add_sample()
    app.generate()
    assert 'Не пиши в шагах и предусловиях, что сервис или потребитель запущен' in app.model.prompts_of('promptGenerate')[0]


def test_generated_api_case_has_no_request_block(app):
    app.add_sample()
    app.generate()
    keys = app.state("S.run.cases.filter((c) => c.type === 'api').map((c) => Object.keys(c.testCase))")
    assert keys and all('request' not in k for k in keys), keys


# ---------- адрес вызова API везде одинаково: {baseURL}/путь ----------
import pytest  # noqa: E402


@pytest.mark.parametrize('src,out', [
    ('Вызвать POST /api/v1/orders с телом:', 'Вызвать POST {baseURL}/api/v1/orders с телом:'),
    ('Вызвать GET https://stage.company.ru/api/v1/orders/1', 'Вызвать GET {baseURL}/api/v1/orders/1'),
    ('Вызвать GET http://10.0.0.5:8080/api/v1/orders?status=NEW', 'Вызвать GET {baseURL}/api/v1/orders?status=NEW'),
    ('Вызвать DELETE {{baseUrl}}/api/v1/orders/1', 'Вызвать DELETE {baseURL}/api/v1/orders/1'),
    ('Вызвать PUT {base_url}/api/v1/orders/1', 'Вызвать PUT {baseURL}/api/v1/orders/1'),
    ('Вызвать PATCH ${host}/api/v1/orders/1', 'Вызвать PATCH {baseURL}/api/v1/orders/1'),
    ('Вызвать POST {baseURL}/api/v1/orders', 'Вызвать POST {baseURL}/api/v1/orders'),
    ('[BE] POST /api/v1/password-reset — 202', '[BE] POST {baseURL}/api/v1/password-reset — 202'),
    ('Запрос «GET /api/v1/orders» вернул 200', 'Запрос «GET {baseURL}/api/v1/orders» вернул 200'),
    ('Открыть страницу https://stage.company.ru/login', 'Открыть страницу https://stage.company.ru/login'),   # не вызов API — не трогаем
    ('Нажать «Отправить»', 'Нажать «Отправить»'),
])
def test_api_address_is_normalized(app, src, out):
    assert app.call('a.baseUrlText(arg)', src) == out


def test_rule_with_base_url_is_in_generation_prompt(app):
    app.add_sample()
    app.generate()
    p = app.model.prompts_of('promptGenerate')[0]
    assert '«Вызвать МЕТОД {baseURL}/ЭНДПОИНТ с телом:»' in p and '{baseURL} — адрес тестового стенда' in p


def test_generated_cases_use_base_url_everywhere(app):
    from tests.support.model import DEFAULTS
    gen = DEFAULTS['promptGenerate']

    def with_hosts(c):
        res = gen(c)
        for x in res.get('cases', []):
            tc = x['testCase']
            tc['preconditions'] = list(tc.get('preconditions') or []) + ['Выполнен GET https://stage.company.ru/api/v1/health']
            for s in tc.get('steps') or []:
                s['action'] = 'Вызвать POST /api/v1/password-reset с телом:\n\n```json\n{"email": "u@example.ru"}\n```'
        return res
    app.model.on('promptGenerate', with_hosts)
    app.add_sample()
    app.generate()
    texts = app.state('JSON.stringify(S.run.cases.map((c) => c.testCase))')
    assert 'stage.company.ru' not in texts and 'POST /api' not in texts
    assert 'Вызвать POST {baseURL}/api/v1/password-reset с телом:' in texts and 'GET {baseURL}/api/v1/health' in texts


def test_review_fixes_old_address_in_place(app):
    c = {'type': 'api', 'dispId': 'API-001', 'suites': ['regression'], 'requirementIds': [],
         'testCase': {'title': '[BE] GET /api/v1/x', 'priority': 'P3_HIGH', 'steps': [{'step': 1, 'action': 'Вызвать GET https://dev.host/api/v1/x', 'expected': '200'}]}}
    n, x = app.call('(() => { const x = arg; const n = a.applyRuleFixes(x); return [n, x]; })()', c)
    assert n == 2 and x['testCase']['title'] == '[BE] GET {baseURL}/api/v1/x' and x['testCase']['steps'][0]['action'] == 'Вызвать GET {baseURL}/api/v1/x'
    assert app.call('a.ruleViolations(arg)', x) == []
