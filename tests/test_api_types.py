"""Проверка типа данных в API: правило в запросах и средний приоритет в коде."""
import re

from tests.support import model


def test_type_checks_in_api_get_medium_priority(app):
    p = lambda t, x, pr='P4_CRITICAL': app.call(f"a.apiTypePrio({t!r}, {x!r}, {pr!r})")
    assert p('api', 'POST {baseURL}/api/v1/orders — amount строкой вместо числа: 400') == 'P2_MEDIUM'
    assert p('api', 'Неверный тип данных в поле email — 400 VALIDATION_ERROR') == 'P2_MEDIUM'
    assert p('api', 'Поле qty другого типа (объект) — ошибка валидации', 'P1_LOW') == 'P2_MEDIUM'
    assert p('api', 'Создание заказа с корректными данными — 201') == 'P4_CRITICAL'
    assert p('api', 'Тип пользователя «Администратор» видит все заказы') == 'P4_CRITICAL'
    assert p('ui', 'Ввод строки вместо числа в поле «Количество»') == 'P4_CRITICAL'   # правило — только для API


def test_rule_reaches_checklist_plan_and_generation(app):
    app.add_sample()
    app.generate()
    for kind in ('promptChecklist', 'promptPlan', 'promptGenerate'):
        ps = app.model.prompts_of(kind)
        if ps:
            assert 'В API проверяй тип данных полей запроса' in ps[0] and 'Приоритет такой проверки — P2_MEDIUM' in ps[0], kind


def test_generated_type_check_case_is_medium(app):
    def cases(call):
        ids = re.findall(r'### ([A-Z]+-\d+)\.', call.prompt)
        title = '[BE] POST {baseURL}/api/v1/password-reset — email числом вместо строки'
        return {'cases': [{'planItem': pid, 'requirementIds': [], 'suites': ['smoke'],
                           'testCase': {'title': title, 'id': '', 'priority': 'P4_CRITICAL', 'preconditions': ['—'],
                                        'steps': [{'step': 1, 'action': 'a', 'expected': '400'}]}} for pid in ids]}

    def critical(call):
        r = model._analyze(call)
        for x in r['requirements']:
            x['priority'] = 'P4_CRITICAL'
        return r
    app.model.on('promptGenerate', cases).on('promptAnalyze', critical)
    app.add_sample()
    from tests.test_generation import set_outputs
    set_outputs(app, checklist=False)
    app.generate()
    api = app.state("S.run.cases.filter((c) => c.type === 'api').map((c) => c.testCase.priority)")
    ui = app.state("S.run.cases.filter((c) => c.type === 'ui').map((c) => c.testCase.priority)")
    assert api and set(api) == {'P2_MEDIUM'}
    assert ui and set(ui) == {'P4_CRITICAL'}   # в UI такой заголовок приоритет не меняет


RUN = "{ settings: { depth: 'smoke' }, reqById: { R1: { priority: 'P3_HIGH' } } }"
TYPE = 'Поле amount строкой вместо числа — 400'


def test_type_checks_are_cut_first_by_checklist_budget(app):
    """Смоук, требование P3: одна проверка. Тип данных среднего приоритета уступает даже негативной низкого."""
    r = app.call(f"""(() => {{
      const it = (check, kind, priority) => ({{ check, kind, priority, type: 'api', requirementIds: ['R1'] }});
      const groups = [{{ title: 'API', items: [it({TYPE!r}, 'negative', 'P2_MEDIUM'), it('Пустое тело — 400', 'negative', 'P1_LOW')] }}];
      return a.budgetChecklist({RUN}, groups).groups.flatMap((g) => g.items.map((i) => i.check));
    }})()""")
    assert r == ['Пустое тело — 400']


def test_type_checks_go_last_under_checklist_limit(app):
    r = app.call(f"""(() => {{
      const it = (check, kind, priority) => ({{ check, kind, priority, type: 'api', requirementIds: [] }});
      const groups = [{{ title: 'API', items: [it({TYPE!r}, 'positive', 'P2_MEDIUM'), it('Создание заказа — 201', 'positive', 'P1_LOW'), it('Пустое тело — 400', 'negative', 'P1_LOW')] }}];
      return a.capChecklist(groups, 2).groups.flatMap((g) => g.items.map((i) => i.check));
    }})()""")
    assert r == ['Создание заказа — 201', 'Пустое тело — 400']


def test_type_checks_go_last_in_plan(app):
    r = app.call(f"""(() => {{
      const items = [{{ type: 'api', title: 'Заказ', requirementIds: ['R1'], checks: [{TYPE!r}, 'Создание заказа — 201'] }}];
      a.budgetPlan({RUN}, items);
      const capped = a.capChecks([{{ type: 'api', title: 'Заказ', requirementIds: [], checks: [{TYPE!r}, 'Создание заказа — 201', 'Пустое тело — 400'] }}], 2);
      return {{ budget: items[0].checks, capped: capped[0].checks }};
    }})()""")
    assert r == {'budget': ['Создание заказа — 201'], 'capped': ['Создание заказа — 201', 'Пустое тело — 400']}


def test_rule_says_type_checks_come_last(app):
    app.add_sample()
    app.generate()
    p = app.model.prompts_of('promptChecklist')[0]
    assert 'включай её в последнюю очередь' in p
