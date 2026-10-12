"""Метки вида теста в названии кейса: [BE] — API, [Kafka] — сообщения Kafka, [FE] — UI, [E2E] — сквозные."""
import pytest

CASES = [
    # (вид, название от модели, ожидаемое название)
    ('api', 'POST /api/v1/orders — создание заказа', '[BE] POST /api/v1/orders — создание заказа'),
    ('api', '[BE] POST /api/v1/orders — создание заказа', '[BE] POST /api/v1/orders — создание заказа'),
    ('api', '[API] GET /users', '[BE] GET /users'),
    ('api', 'Kafka: сообщение order.created уходит в топик после оплаты', '[Kafka] Kafka: сообщение order.created уходит в топик после оплаты'),
    ('api', '[Kafka] Событие order.created в топике', '[Kafka] Событие order.created в топике'),
    ('api', '[BE][Kafka] Событие order.created', '[Kafka] Событие order.created'),
    ('api', 'POST /orders — событие в Kafka после создания', '[BE] POST /orders — событие в Kafka после создания'),
    ('api', 'Чтение сообщения из топика кафка', '[Kafka] Чтение сообщения из топика кафка'),
    ('ui', 'Восстановление пароля: ошибка', '[FE] Восстановление пароля: ошибка'),
    ('ui', '[UI] Восстановление пароля', '[FE] Восстановление пароля'),
    ('ui', '[BE] Восстановление пароля', '[FE] Восстановление пароля'),
    ('ui', '  [fe]   Восстановление пароля', '[FE] Восстановление пароля'),
    ('ui', '[Smoke] Восстановление пароля', '[FE] [Smoke] Восстановление пароля'),
    ('e2e', 'Восстановление доступа: сквозной', '[E2E] Восстановление доступа: сквозной'),
    ('e2e', '[e2e] Восстановление', '[E2E] Восстановление'),
    ('e2e', '[Kafka] Сквозной', '[E2E] Сквозной'),
]


@pytest.fixture
def tag(app):
    def run(ty, title, key='title'):
        return app.call('a.orderLikeTemplate({[arg.key]: arg.title, steps: []}, a.tplInfo(arg.ty), arg.ty)[arg.key]', {'ty': ty, 'title': title, 'key': key})
    return run


@pytest.mark.parametrize('ty,title,expected', CASES)
def test_tag_by_type(tag, ty, title, expected):
    assert tag(ty, title) == expected


def test_idempotent(tag):
    assert tag('api', tag('api', 'GET /x')) == '[BE] GET /x'


def test_other_title_field(tag):
    assert tag('ui', 'Вход', 'name') == '[FE] Вход'


@pytest.mark.parametrize('title', ['', '[FE]'])
def test_empty_title_or_bare_tag_is_left_alone(tag, title):
    assert tag('ui', title) == title


def test_no_type_no_tag(app):
    assert app.call("a.orderLikeTemplate({title: 'Вход'}, a.tplInfo('ui')).title") == 'Вход'


@pytest.mark.parametrize('case,ok', [
    ({'type': 'ui', 'testCase': {'title': '[FE] Вход'}}, True), ({'type': 'ui', 'testCase': {'title': 'Вход'}}, False),
    ({'type': 'api', 'testCase': {'title': '[Kafka] x'}}, True), ({'type': 'api', 'testCase': {'title': 'x'}}, False)])
def test_title_tag_ok_for_review(app, case, ok):
    assert app.call('a.titleTagOk(arg)', case) is ok


def test_templates_show_tags_in_examples(app):
    titles = app.call("['api', 'ui', 'e2e'].map((t) => a.tplInfo(t).structure.title)")
    assert [t.split(' ')[0] for t in titles] == ['[BE]', '[FE]', '[E2E]']


def test_generated_cases_get_tags(app):
    """Мок-модель отвечает названиями без меток — после генерации метки стоят у всех кейсов."""
    app.add_sample()
    app.generate()
    titles = app.state('S.run.cases.map((c) => [c.type, a.pickTitleText(c.testCase)])')
    assert titles, 'кейсы не созданы'
    expect = {'api': '[BE]', 'ui': '[FE]', 'e2e': '[E2E]'}
    for ty, title in titles:
        assert title.startswith(expect[ty] + ' '), (ty, title)


def test_rule_is_in_generation_prompts(app):
    app.add_sample()
    app.generate()
    p = app.model.prompts_of('promptGenerate')[0]
    for tag in ('[BE]', '[Kafka]', '[FE]', '[E2E]'):
        assert tag in p
