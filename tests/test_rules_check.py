"""Правила команды проверяет код: безопасные исправления на месте, нарушения — замечаниями ревью."""
import pytest

from tests.support import model_generation as MG


def case(ty='ui', title='[FE] Вход', pre=(), steps=(), **extra):
    tc = {'title': title, 'priority': 'P3_HIGH', 'preconditions': list(pre), 'steps': [{'step': i + 1, 'action': a, 'expected': e} for i, (a, e) in enumerate(steps)], 'expectedResult': 'ok'}
    tc.update(extra)
    return {'type': ty, 'testCase': tc, 'suites': ['regression'], 'requirementIds': [], 'dispId': 'X-001'}


CLEAN = case(pre=['Пользователь зарегистрирован'], steps=[('Открыть /login', 'Открыта страница')])


def ids(app, c):
    return [v['id'] for v in app.call('a.ruleViolations(arg)', c)]


def fixed(app, c):
    """Исправления выполняются в браузере: возвращаем исправленный объект, а не мутируем копию из Python."""
    return app.call("(() => { const x = arg; const n = a.applyRuleFixes(x); return [n, x]; })()", c)


def test_clean_case_has_no_violations(app):
    assert app.call('a.ruleViolations(arg)', CLEAN) == []


@pytest.mark.parametrize('pre', [
    ['Сервис получения данных из Kafka запущен и подписан на топик ppcm-dataEvent'],
    ['Консьюмер подписан на топик orders'],
    ['Сервис оплаты работает'],
])
def test_service_state_in_preconditions(app, pre):
    assert 'service-state' in ids(app, case(pre=pre, steps=[('Открыть /login', 'ok')]))


def test_service_state_in_steps(app):
    assert 'service-state' in ids(app, case(steps=[('Убедиться, что сервис заказов запущен', 'ok')]))


def test_normal_preconditions_are_fine(app):
    assert 'service-state' not in ids(app, case(pre=['Пользователь зарегистрирован и активен'], steps=[('Открыть /login', 'ok')]))


def test_kafka_message_with_http_method(app):
    c = case('api', '[Kafka] Событие order.created', steps=[('Отправить POST в топик orders', 'ok')])
    assert 'kafka-method' in ids(app, c)


def test_kafka_banned_steps(app):
    c = case('api', '[Kafka] Событие', steps=[('Подготовь сообщение', 'ok'), ('Отправить подготовленное сообщение', 'ok')])
    assert 'kafka-steps' in ids(app, c)


def test_kafka_send_step_is_fine(app):
    c = case('api', '[Kafka] Событие', steps=[('Отправить сообщение:\n\n```json\n{"id": 1}\n```', 'ok')])
    assert 'kafka-method' not in ids(app, c) and 'kafka-steps' not in ids(app, c)


def test_api_call_must_use_the_form(app):
    assert 'api-call' in ids(app, case('api', '[BE] POST', steps=[('Отправить POST /api/v1/orders', 'ok')]))
    assert 'api-call' not in ids(app, case('api', '[BE] POST', steps=[('Вызвать POST /api/v1/orders с телом:', 'ok')]))


def test_requirement_ids_in_text(app):
    assert 'req-refs' in ids(app, case(steps=[('Проверить по требованию R-001', 'ok')]))


def test_out_of_scope_checks(app):
    assert 'scope' in ids(app, case(steps=[('Свободное исследование формы на усмотрение тестировщика', 'ok')]))
    assert 'scope' in ids(app, case('api', '[BE] X', steps=[('Выполнить INSERT INTO users и проверить ответ', 'ok')]))


def test_fixes_apply_in_place(app):
    c = case('api', 'POST /x', steps=[('Вызвать POST /x с телом:', 'ok')], priority='High', request={'method': 'POST'})
    c['suites'] = []
    n, x = fixed(app, c)
    assert n == 2  # блок request и приоритет; название и наборы здесь не меняются
    assert x['testCase']['priority'] == 'P3_HIGH' and 'request' not in x['testCase']


def test_critical_gets_smoke_in_fixes(app):
    c = case(steps=[('Открыть /login', 'ok')], priority='P4_CRITICAL')
    _, x = fixed(app, c)
    assert x['suites'] == ['smoke', 'regression']


def bad_service_cases(call):
    ids_ = [pid for pid in __import__('re').findall(r'### ([A-Z]+-\d+)\.', call.prompt)]
    return {'cases': [{'planItem': pid, 'requirementIds': [], 'suites': ['regression'],
                       'testCase': {'title': f'[BE] Кейс {pid}', 'id': '', 'priority': 'P3_HIGH', 'preconditions': ['Сервис получения данных из Kafka запущен и подписан на топик ppcm-dataEvent'],
                                    'steps': [{'step': 1, 'action': 'Открыть /login', 'expected': 'ok'}], 'expectedResult': 'ok'}} for pid in ids_]}


def test_model_breaking_a_rule_shows_up_in_review(app):
    """Модель нарушила правило: ревью показывает замечание «Правило», а журнал — сводку по правилам."""
    app.model.on('promptGenerate', bad_service_cases)
    app.add_sample()
    app.generate()
    app.tab('review')
    app.page.click('[data-act=start-review]')
    app.wait_idle()
    rule_findings = app.state("S.run.findings.filter((f) => f.category === 'Правило')")
    assert rule_findings and all(f['rule'] == 'service-state' for f in rule_findings)
    log = [l['text'] for l in app.state("S.run.steps.review.log")]
    assert any('Нарушения правил: service-state' in t for t in log), log
