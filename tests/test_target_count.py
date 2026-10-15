"""Количество тестов задаётся перед генерацией: план ограничивается этим числом проверок."""
import pytest


def plan_log(app):
    return [l['text'] for l in app.state("S.run.steps.plan.log")]


def test_default_is_no_limit(app):
    app.add_sample()
    app.generate()
    assert app.state('S.settings.target') is None
    assert not any('План ограничен' in t for t in plan_log(app))


@pytest.mark.parametrize('n', [1, 3])
def test_target_limits_the_plan(app, n):
    app.page.fill('#target-n', str(n))
    app.page.dispatch_event('#target-n', 'change')
    assert app.state('S.settings.target') == n
    app.add_sample()
    app.generate()
    assert f'План ограничен числом проверок: {n} (было 6)' in plan_log(app)


def test_target_is_saved_and_restored(app):
    app.page.fill('#target-n', '4')
    app.page.dispatch_event('#target-n', 'change')
    app.reload()
    assert app.state('S.settings.target') == 4 and app.page.input_value('#target-n') == '4'


def test_empty_or_invalid_means_no_limit(app):
    app.page.fill('#target-n', '')
    app.page.dispatch_event('#target-n', 'change')
    assert app.state('S.settings.target') is None
    app.page.fill('#target-n', '0')
    app.page.dispatch_event('#target-n', 'change')
    assert app.state('S.settings.target') is None


def test_each_group_keeps_one_check_first(app):
    """При малом числе сохраняем по одной проверке из каждой группы плана."""
    assert app.call("a.capChecks([{ type: 'ui', checks: ['a', 'b'] }, { type: 'api', checks: ['c', 'd'] }, { type: 'e2e', checks: ['e'] }], 3).map((it) => it.checks)") == [['a'], ['c'], ['e']]
    assert app.call("a.capChecks([{ type: 'ui', checks: ['a', 'b'] }, { type: 'api', checks: ['c'] }], 2).map((it) => it.checks)") == [['a'], ['c']]


def test_strict_target_does_not_add_cases_and_warns(app):
    """Строгое число: сверка покрытия не добавляет кейсы, а предупреждает о требованиях без проверок."""
    import re
    app.page.fill('#target-n', '1')
    app.page.dispatch_event('#target-n', 'change')
    app.model.on('promptCoverageAudit', lambda call: {'gaps': [{'requirementId': 'R-001', 'type': 'ui', 'checks': ['Ссылка ведёт на /password-reset']}]})
    app.add_sample()
    app.generate()
    log = [l['text'] for l in app.state("S.run.steps.coverage.log")]
    assert any('Строгое число проверок (1)' in t and 'R-001' in t for t in log), log
    assert not any('Дописываю' in t for t in log)
    assert app.state("S.run.plan.filter((p) => p.id.startsWith('C-')).length") == 0
    assert app.state('S.run.coverageGaps.length') == 1


def cases_count(app):
    return app.state('S.run.cases.length')


def coverage_log(app):
    return [l['text'] for l in app.state("S.run.steps.coverage.log")]


def test_target_one_gives_one_case(app):
    """Регрессия: при «Тестов всего = 1» запуск давал десятки кейсов — требования без кейсов дописывались отдельно."""
    app.page.fill('#target-n', '1')
    app.page.dispatch_event('#target-n', 'change')
    app.add_sample()
    app.generate()
    assert cases_count(app) == 1, plan_log(app)


@pytest.mark.parametrize('n', [1, 2, 3])
def test_target_caps_cases_to_the_number(app, n):
    app.page.fill('#target-n', str(n))
    app.page.dispatch_event('#target-n', 'change')
    app.add_sample()
    app.generate()
    assert cases_count(app) == n


def test_uncovered_requirements_are_reported_not_filled(app):
    app.page.fill('#target-n', '1')
    app.page.dispatch_event('#target-n', 'change')
    app.add_sample()
    app.generate()
    log = coverage_log(app)
    assert not any('дописываю' in t.lower() for t in log), log
    assert any('Строгое число проверок (1)' in t and 'без кейсов остались требования' in t for t in log), log
    assert not app.state("S.run.plan.some((p) => p.id.startsWith('G-'))")


def test_without_target_there_is_no_limit(app):
    app.add_sample()
    app.generate()
    assert cases_count(app) > 1
    assert not any('Строгое число' in t for t in coverage_log(app))
