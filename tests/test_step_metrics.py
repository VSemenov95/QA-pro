"""Панель этапа в «Агенте»: сколько раз звали модель и сколько токенов, что попало в запрос, последний промпт."""


def test_each_stage_shows_calls_tokens_and_what_it_used(app):
    app.add_sample()
    app.generate()
    app.tab('agent')
    timeline = app.text('ol.timeline')
    assert 'Вызовов' in timeline and 'токены: вход' in timeline, timeline
    assert 'Использовано:' in timeline and 'документ' in timeline, timeline
    assert app.count('details.st-prompt') >= 1
    assert app.state("Object.values(S.run.usage.by).every((b) => b.calls > 0)")


def test_step_metrics_are_kept_with_the_run(app):
    app.add_sample()
    app.generate()
    by = app.state('S.run.usage.by')
    assert by and all('sections' in b for b in by.values() if b['calls'])


def test_checklist_stage_names_the_rules_it_used(app):
    """Правила без заголовков (лимит, наборы) тоже попадают в «Использовано», а не только разделы с заголовками."""
    from tests.test_generation import set_outputs
    app.page.fill('#target-n', '3')
    app.page.dispatch_event('#target-n', 'change')
    app.add_sample()
    set_outputs(app, cases=False)
    app.generate()
    app.tab('agent')
    timeline = app.text('ol.timeline')
    assert 'лимит количества' in timeline and 'наборы смоук/регресс' in timeline, timeline
