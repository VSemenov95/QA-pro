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
