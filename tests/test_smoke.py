"""Страница открывается, мок-модель отвечает, возможности подключены."""


def test_page_opens(app):
    assert app.state('S.caps.ready') is True
    assert app.state('!!S.caps.sample') is True and app.state('!!S.caps.db') is True
    assert app.count('#btn-run') == 1


def test_sample_generation_end_to_end(app):
    app.add_sample()
    app.generate()
    assert app.state('S.run.status') == 'done', app.state('S.run.error')
    assert app.state('S.run.cases.length') > 0
    kinds = {c.kind for c in app.model.calls}
    assert {'promptAnalyze', 'promptPlan', 'promptGenerate'} <= kinds, kinds
    assert 'unknown' not in kinds
