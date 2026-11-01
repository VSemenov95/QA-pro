"""Ответ модели, который не читается как JSON: починка переносов, оборванный хвост, повтор с напоминанием о формате."""
from tests.support import model
from tests.support.model import ModelError


def repair(app, text):
    return app.call('a.repairJSON(arg)', text)


def test_newlines_inside_strings_are_escaped(app):
    r = repair(app, '{"title": "Шаг 1\nШаг 2", "body": "```json\n{\\"a\\": 1}\n```"}')
    assert r == {'value': {'title': 'Шаг 1\nШаг 2', 'body': '```json\n{"a": 1}\n```'}, 'cut': False}


def test_text_around_json_is_dropped(app):
    r = repair(app, 'Вот результат:\n{"items": [1, 2]}\nГотово, ещё {вопросы}?')
    assert r == {'value': {'items': [1, 2]}, 'cut': False}


def test_cut_reply_keeps_complete_items(app):
    r = repair(app, '{"summary": "ок", "requirements": [{"title": "A", "criteria": ["x"]}, {"title": "B"}, {"title": "C", "crit')
    assert r == {'value': {'summary': 'ок', 'requirements': [{'title': 'A', 'criteria': ['x']}, {'title': 'B'}]}, 'cut': True}


def test_plain_text_cannot_be_repaired(app):
    assert repair(app, 'В документе нет требований к этому разделу.') is None


def test_bad_reply_is_asked_again_once(app):
    state = {'n': 0}

    def flaky(call):
        state['n'] += 1
        if state['n'] == 1:
            return ModelError('invalid_json', text='Требования выделены, но формат я не соблюду.')
        return model._analyze(call)
    app.model.on('promptAnalyze', flaky)
    app.add_sample()
    app.generate()
    ps = app.model.prompts_of('promptAnalyze')
    assert len(ps) == 2 and 'не удалось разобрать как JSON' in ps[1]
    assert app.state('S.run.status') == 'done' and app.state('S.run.requirements.length') > 0


def test_cut_analysis_keeps_what_came(app):
    cut = '{"requirements":[{"title":"Ссылка «Забыли пароль?»","description":"На /login есть ссылка","types":["ui"],"priority":"P3_HIGH","criteria":["Ссылка видна"]},{"title":"Обрыв","descr'
    app.model.on('promptAnalyze', ModelError('invalid_json', text=cut))
    app.add_sample()
    app.generate(wait=False)
    app.page.wait_for_function("() => window.__qa.S.run && window.__qa.S.run.requirements.length > 0", timeout=30000)
    assert app.state('S.run.requirements.map((r) => r.title)') == ['Ссылка «Забыли пароль?»']
    log = ' '.join(app.state("S.run.steps.analyze.log.map((l) => l.text)"))
    assert 'оборвался на лимите длины' in log
    assert len(app.model.prompts_of('promptAnalyze')) == 1   # оборванный ответ не повторяется — дописанное берётся


def test_cut_generation_is_split_not_taken(app):
    """Генерация при обрыве не берёт половину кейсов, а делит пачку и пишет её частями."""
    state = {'n': 0}

    def gen(call):
        state['n'] += 1
        if state['n'] == 1:
            return ModelError('invalid_json', text='{"cases":[{"planItem":"P-01","testCase":{"title":"[FE] Обры')
        return model._generate(call)
    app.model.on('promptGenerate', gen)
    app.add_sample()
    app.generate()
    assert app.state('S.run.status') == 'done' and app.state('S.run.failed.length') == 0
    assert state['n'] >= 3   # оборванная пачка, затем две её половины
    assert not any('Обры' in t for t in app.state('S.run.cases.map((c) => c.testCase.title || "")'))
